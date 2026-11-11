"""
Tareas de Celery para ServiuApp.
Procesamiento asíncrono de importaciones Excel y chat.
"""
import os
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=7800,      # 2h 10m límite duro
    soft_time_limit=7200, # 2h límite suave
    acks_late=True,       # Confirmar después de completar (para tareas largas)
    reject_on_worker_lost=True  # Re-encolar si el worker muere
)
def importar_excel_task(self, archivo_path, usuario_id=None):
    """
    Tarea asíncrona para importar archivo Excel.
    Se ejecuta en background sin bloquear la web.

    Args:
        archivo_path: Ruta al archivo Excel subido
        usuario_id: ID del usuario que subió el archivo (opcional)

    Returns:
        dict: Resultado de la importación con estadísticas
    """
    import pandas as pd
    from datetime import datetime, date
    from serviuapp.models import Beneficiarios, Decretos, Resoluciones

    def convert_excel_date(value):
        if pd.isna(value) or value == '' or value == '-':
            return None
        if isinstance(value, (datetime, date)):
            return value.date() if isinstance(value, datetime) else value
        if isinstance(value, (int, float)):
            try:
                if value > 59:
                    excel_date = datetime(1900, 1, 1) + pd.Timedelta(days=value - 2)
                else:
                    excel_date = datetime(1900, 1, 1) + pd.Timedelta(days=value - 1)
                return excel_date.date()
            except:
                return None
        value_str = str(value).strip()
        if not value_str or value_str == '-':
            return None
        for fmt in ['%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue
        return None

    def clean_integer(value):
        if pd.isna(value) or value == '' or value == '-':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def clean_string(value, max_length=None):
        if pd.isna(value) or value == '':
            return ''
        result = str(value).strip()
        if max_length and len(result) > max_length:
            result = result[:max_length]
        return result

    try:
        import time
        self.start_time = time.time()  # Para calcular ETA
        logger.info(f"Iniciando importación Celery: {archivo_path}")

        # Actualizar estado
        self.update_state(state='PROGRESS', meta={'step': 'leyendo', 'progress': 10})

        # Leer archivo
        df = pd.read_excel(archivo_path)
        total_filas = len(df)
        logger.info(f"Archivo leído: {total_filas} filas")

        self.update_state(state='PROGRESS', meta={'step': 'limpiando', 'progress': 20})

        # Limpiar tablas
        Resoluciones.objects.all().delete()
        Decretos.objects.all().delete()
        Beneficiarios.objects.all().delete()

        self.update_state(state='PROGRESS', meta={'step': 'procesando', 'progress': 30})

        batch_size = 1000
        beneficiarios_creados = 0
        decretos_creados = 0
        resoluciones_creadas = 0
        errores = 0

        # Procesar en lotes
        for start_idx in range(0, total_filas, batch_size):
            end_idx = min(start_idx + batch_size, total_filas)
            batch_df = df.iloc[start_idx:end_idx]

            beneficiarios_batch = []
            decretos_data = []
            resoluciones_data = []

            for idx, row in batch_df.iterrows():
                try:
                    # Datos beneficiario
                    id_bene = clean_integer(row.get('id_beneficiario'))
                    if not id_bene:
                        continue

                    bene_data = {
                        'id_beneficiario': id_bene,
                        'rut': clean_string(row.get('rut'), 50),
                        'dv': clean_string(row.get('dv'), 10),
                        'nombres': clean_string(row.get('nombres'), 255),
                        'primer_apellido': clean_string(row.get('primer_apellido'), 100),
                        'segundo_apellido': clean_string(row.get('segundo_apellido'), 100),
                        'comuna': clean_string(row.get('comuna'), 100),
                        'provincia': clean_string(row.get('provincia'), 100),
                        'codigo_proyecto': clean_string(row.get('codigo_proyecto'), 100),
                        'nombre_grupo': clean_string(row.get('nombre_grupo'), 255),
                        'sexo': clean_string(row.get('sexo'), 10)
                    }
                    beneficiarios_batch.append(Beneficiarios(**bene_data))

                    # Preparar decreto
                    decretos_data.append({
                        'id_beneficiario': id_bene,
                        'decreto': clean_string(row.get('decreto'), 10),
                        'tipologia': clean_string(row.get('tipologia'), 50),
                        'tramo': clean_integer(row.get('tramo'))
                    })

                    # Preparar resolución
                    resoluciones_data.append({
                        'id_beneficiario': id_bene,
                        'resolucion': clean_integer(row.get('resolucion')),
                        'fecha_resolucion': convert_excel_date(row.get('fecha_resolucion')),
                        'seleccion': clean_string(row.get('seleccion'), 50),
                        'ano_imputacion_res_of': clean_integer(row.get('ano_imputacion_res_of'))
                    })

                except Exception as e:
                    logger.error(f"Error fila {idx}: {e}")
                    errores += 1

            # Bulk create beneficiarios
            if beneficiarios_batch:
                Beneficiarios.objects.bulk_create(beneficiarios_batch, ignore_conflicts=True)
                beneficiarios_creados += len(beneficiarios_batch)

            # Crear lookup de beneficiarios
            bene_ids = [b.id_beneficiario for b in beneficiarios_batch]
            bene_map = {b.id_beneficiario: b for b in
                        Beneficiarios.objects.filter(id_beneficiario__in=bene_ids)}

            # Bulk create decretos
            decretos_objs = [
                Decretos(
                    decreto_id_beneficiario=bene_map[d['id_beneficiario']],
                    decreto=d['decreto'],
                    tipologia=d['tipologia'],
                    tramo=d['tramo']
                )
                for d in decretos_data if d['id_beneficiario'] in bene_map
            ]
            if decretos_objs:
                Decretos.objects.bulk_create(decretos_objs, ignore_conflicts=True)
                decretos_creados += len(decretos_objs)

            # Bulk create resoluciones
            resoluciones_objs = [
                Resoluciones(
                    resolucion_id_beneficiario=bene_map[r['id_beneficiario']],
                    resolucion=r['resolucion'],
                    fecha_resolucion=r['fecha_resolucion'],
                    seleccion=r['seleccion'],
                    ano_imputacion_res_of=r['ano_imputacion_res_of']
                )
                for r in resoluciones_data if r['id_beneficiario'] in bene_map
            ]
            if resoluciones_objs:
                Resoluciones.objects.bulk_create(resoluciones_objs, ignore_conflicts=True)
                resoluciones_creadas += len(resoluciones_objs)

            # Actualizar progreso con tiempo estimado
            progress = 30 + int((start_idx / total_filas) * 60)

            # Calcular tiempo estimado restante
            import time
            elapsed = time.time() - self.start_time if hasattr(self, 'start_time') else 0
            if progress > 30 and elapsed > 0:
                # Progreso real de procesamiento (0-60%)
                real_progress = (progress - 30) / 60.0
                if real_progress > 0:
                    estimated_total = elapsed / real_progress
                    eta_seconds = int(estimated_total - elapsed)
                else:
                    eta_seconds = 0
            else:
                eta_seconds = 0

            self.update_state(
                state='PROGRESS',
                meta={
                    'step': 'procesando',
                    'progress': progress,
                    'beneficiarios': beneficiarios_creados,
                    'decretos': decretos_creados,
                    'resoluciones': resoluciones_creadas,
                    'eta_seconds': eta_seconds,
                    'rows_processed': start_idx,
                    'total_rows': total_filas
                }
            )

        # Resultado final
        resultado = {
            'status': 'completed',
            'beneficiarios_creados': beneficiarios_creados,
            'decretos_creados': decretos_creados,
            'resoluciones_creadas': resoluciones_creadas,
            'errores': errores,
            'total_filas': total_filas,
            'timestamp': timezone.now().isoformat()
        }

        logger.info(f"Importación completada: {resultado}")
        return resultado

    except Exception as exc:
        logger.error(f"Error en importación: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def procesar_chat_task(self, user_query, rut=None, session_id=None, user_ip=None):
    """
    Tarea asíncrona para procesar consulta del chat con IA.
    Evita bloquear el request HTTP mientras espera respuesta de Ollama.

    Returns:
        dict: Respuesta de la IA con metadatos
    """
    import time
    import uuid
    from serviuapp.serviu_prompt import generate_serviu_response
    from serviuapp.models import ChatInteraction

    try:
        if not session_id:
            session_id = str(uuid.uuid4())

        start_time = time.time()

        # Generar respuesta (usa Ollama con fallback)
        response, session_id, interaction_id = generate_serviu_response(
            user_query=user_query,
            rut=rut,
            session_id=session_id,
            user_ip=user_ip
        )

        response_time = int((time.time() - start_time) * 1000)

        return {
            'status': 'completed',
            'response': response,
            'session_id': session_id,
            'interaction_id': interaction_id,
            'response_time_ms': response_time
        }

    except Exception as exc:
        logger.error(f"Error en chat task: {exc}")
        raise self.retry(exc=exc)


@shared_task
def limpiar_logs_antiguos(dias=30):
    """
    Tarea periódica para limpiar logs e interacciones antiguas.
    Se ejecuta via Celery Beat (configurable en admin).
    """
    from datetime import timedelta
    from django.utils import timezone
    from serviuapp.models import ChatInteraction

    fecha_limite = timezone.now() - timedelta(days=dias)
    eliminados, _ = ChatInteraction.objects.filter(timestamp__lt=fecha_limite).delete()

    logger.info(f"Limpieza logs: {eliminados} interacciones eliminadas (>{dias} días)")
    return {'eliminados': eliminados, 'dias': dias}