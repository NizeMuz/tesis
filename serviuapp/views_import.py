"""
Vistas para importación de Excel con progreso en tiempo real usando Celery.
"""
import os
import uuid
import threading
import time
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .tasks import importar_excel_task


# Almacén global para progreso en modo eager (desarrollo sin Redis)
_eager_progress_store = {}
_eager_progress_lock = threading.Lock()


def _store_eager_progress(task_id, meta):
    """Almacena progreso para modo eager (thread-safe)."""
    with _eager_progress_lock:
        _eager_progress_store[task_id] = meta


def _get_eager_progress(task_id):
    """Obtiene progreso para modo eager (thread-safe)."""
    with _eager_progress_lock:
        return _eager_progress_store.get(task_id, {})


def _clear_eager_progress(task_id):
    """Limpia progreso para modo eager (thread-safe)."""
    with _eager_progress_lock:
        _eager_progress_store.pop(task_id, None)


class ImportExcelView(View):
    """Vista principal para la página de importación."""

    def get(self, request):
        return render(request, 'serviutemplate/import.html')


@method_decorator(csrf_exempt, name='dispatch')
class UploadAndImportView(View):
    """
    Vista que recibe el archivo, lo guarda temporalmente y lanza la tarea Celery.
    Retorna el task_id para poder consultar el progreso.
    """

    def post(self, request):
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No se envió ningún archivo'}, status=400)

        uploaded_file = request.FILES['file']

        # Validar extensión
        allowed_extensions = ['.xlsx', '.xls']
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext not in allowed_extensions:
            return JsonResponse({
                'error': f'Formato no permitido. Use .xlsx o .xls'
            }, status=400)

        # Validar tamaño (ej: 100MB max)
        max_size = 100 * 1024 * 1024  # 100MB
        if uploaded_file.size > max_size:
            return JsonResponse({
                'error': f'Archivo muy grande. Máximo {max_size // (1024*1024)}MB'
            }, status=400)

        # Guardar archivo temporalmente
        temp_filename = f"import_{uuid.uuid4().hex}{file_ext}"
        temp_path = os.path.join('temp_imports', temp_filename)

        # Asegurar que el directorio existe
        full_temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_imports')
        os.makedirs(full_temp_dir, exist_ok=True)

        # Guardar archivo
        saved_path = default_storage.save(temp_path, ContentFile(uploaded_file.read()))
        full_file_path = os.path.join(settings.MEDIA_ROOT, saved_path)

        # Verificar si estamos en modo eager
        from django.conf import settings as django_settings
        is_eager = getattr(django_settings, 'CELERY_TASK_ALWAYS_EAGER', False)

        if is_eager:
            # En modo eager, ejecutar la tarea en un hilo separado para permitir polling
            task_id = str(uuid.uuid4())

            # Inicializar progreso
            _store_eager_progress(task_id, {
                'state': 'PROGRESS',
                'step': 'leyendo',
                'progress': 10,
            })

            def run_import():
                try:
                    # Ejecutar la lógica de importación directamente
                    from datetime import datetime, date
                    import pandas as pd
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

                    # Leer archivo
                    df = pd.read_excel(full_file_path)
                    total_filas = len(df)

                    _store_eager_progress(task_id, {
                        'state': 'PROGRESS',
                        'step': 'limpiando',
                        'progress': 20,
                    })

                    # Limpiar tablas
                    Resoluciones.objects.all().delete()
                    Decretos.objects.all().delete()
                    Beneficiarios.objects.all().delete()

                    _store_eager_progress(task_id, {
                        'state': 'PROGRESS',
                        'step': 'procesando',
                        'progress': 30,
                    })

                    batch_size = 1000
                    beneficiarios_creados = 0
                    decretos_creados = 0
                    resoluciones_creadas = 0
                    errores = 0
                    start_time = time.time()

                    for start_idx in range(0, total_filas, batch_size):
                        end_idx = min(start_idx + batch_size, total_filas)
                        batch_df = df.iloc[start_idx:end_idx]

                        beneficiarios_batch = []
                        decretos_data = []
                        resoluciones_data = []

                        for idx, row in batch_df.iterrows():
                            try:
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

                                decretos_data.append({
                                    'id_beneficiario': id_bene,
                                    'decreto': clean_string(row.get('decreto'), 10),
                                    'tipologia': clean_string(row.get('tipologia'), 50),
                                    'tramo': clean_integer(row.get('tramo'))
                                })

                                resoluciones_data.append({
                                    'id_beneficiario': id_bene,
                                    'resolucion': clean_integer(row.get('resolucion')),
                                    'fecha_resolucion': convert_excel_date(row.get('fecha_resolucion')),
                                    'seleccion': clean_string(row.get('seleccion'), 50),
                                    'ano_imputacion_res_of': clean_integer(row.get('ano_imputacion_res_of'))
                                })
                            except Exception as e:
                                errores += 1

                        if beneficiarios_batch:
                            Beneficiarios.objects.bulk_create(beneficiarios_batch, ignore_conflicts=True)
                            beneficiarios_creados += len(beneficiarios_batch)

                        bene_ids = [b.id_beneficiario for b in beneficiarios_batch]
                        bene_map = {b.id_beneficiario: b for b in
                                    Beneficiarios.objects.filter(id_beneficiario__in=bene_ids)}

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

                        progress = 30 + int((start_idx / total_filas) * 60)
                        elapsed = time.time() - start_time
                        if progress > 30 and elapsed > 0:
                            real_progress = (progress - 30) / 60.0
                            if real_progress > 0:
                                estimated_total = elapsed / real_progress
                                eta_seconds = int(estimated_total - elapsed)
                            else:
                                eta_seconds = 0
                        else:
                            eta_seconds = 0

                        _store_eager_progress(
                            task_id,
                            meta={
                                'state': 'PROGRESS',
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
                        'timestamp': datetime.now().isoformat()
                    }

                    _store_eager_progress(task_id, {
                        'state': 'SUCCESS',
                        'result': resultado
                    })

                except Exception as exc:
                    _store_eager_progress(task_id, {
                        'state': 'FAILURE',
                        'error': str(exc)
                    })

            thread = threading.Thread(target=run_import)
            thread.daemon = True
            thread.start()

            return JsonResponse({
                'status': 'started',
                'task_id': task_id,
                'message': 'Importación iniciada. Consultando progreso...'
            })
        else:
            # Modo normal con Celery worker
            task = importar_excel_task.delay(full_file_path)

            return JsonResponse({
                'status': 'started',
                'task_id': task.id,
                'message': 'Importación iniciada. Consultando progreso...'
            })


class ImportProgressView(View):
    """
    Vista para consultar el progreso de la tarea de importación.
    Se llama via AJAX/polling desde el frontend.
    """

    def get(self, request, task_id):
        from django.conf import settings as django_settings
        is_eager = getattr(django_settings, 'CELERY_TASK_ALWAYS_EAGER', False)

        if is_eager:
            # En modo eager, leer del almacén local
            meta = _get_eager_progress(task_id)

            if not meta:
                return JsonResponse({
                    'state': 'PENDING',
                    'progress': 0,
                    'step': 'esperando',
                    'message': 'Esperando a que inicie el procesamiento...'
                })

            state = meta.get('state', 'PROGRESS')

            if state == 'PROGRESS':
                eta_seconds = meta.get('eta_seconds', 0)
                rows_processed = meta.get('rows_processed', 0)
                total_rows = meta.get('total_rows', 0)

                eta_str = ''
                if eta_seconds > 0:
                    if eta_seconds < 60:
                        eta_str = f' ~{eta_seconds}s restantes'
                    elif eta_seconds < 3600:
                        eta_str = f' ~{eta_seconds // 60}m {eta_seconds % 60}s restantes'
                    else:
                        h = eta_seconds // 3600
                        m = (eta_seconds % 3600) // 60
                        eta_str = f' ~{h}h {m}m restantes'

                return JsonResponse({
                    'state': 'PROGRESS',
                    'progress': meta.get('progress', 0),
                    'step': meta.get('step', 'procesando'),
                    'beneficiarios': meta.get('beneficiarios', 0),
                    'decretos': meta.get('decretos', 0),
                    'resoluciones': meta.get('resoluciones', 0),
                    'eta_seconds': eta_seconds,
                    'eta_str': eta_str,
                    'rows_processed': rows_processed,
                    'total_rows': total_rows,
                    'message': self._get_step_message(meta.get('step', ''), meta.get('progress', 0)) + eta_str
                })

            elif state == 'SUCCESS':
                result = meta.get('result', {})
                return JsonResponse({
                    'state': 'SUCCESS',
                    'progress': 100,
                    'step': 'completado',
                    'beneficiarios': result.get('beneficiarios_creados', 0),
                    'decretos': result.get('decretos_creados', 0),
                    'resoluciones': result.get('resoluciones_creadas', 0),
                    'errores': result.get('errores', 0),
                    'total_filas': result.get('total_filas', 0),
                    'message': '¡Importación completada exitosamente!'
                })

            elif state == 'FAILURE':
                error_info = meta.get('error', 'Error desconocido')
                return JsonResponse({
                    'state': 'FAILURE',
                    'progress': 0,
                    'step': 'error',
                    'error': error_info,
                    'message': f'Error durante la importación: {error_info}'
                })

            return JsonResponse({
                'state': state,
                'progress': 0,
                'step': state.lower(),
                'message': f'Estado: {state}'
            })
        else:
            # Modo normal con Celery worker
            task = importar_excel_task.AsyncResult(task_id)

            if task.state == 'PENDING':
                return JsonResponse({
                    'state': 'PENDING',
                    'progress': 0,
                    'step': 'esperando',
                    'message': 'Esperando a que inicie el procesamiento...'
                })

            elif task.state == 'PROGRESS':
                meta = task.info or {}
                eta_seconds = meta.get('eta_seconds', 0)
                rows_processed = meta.get('rows_processed', 0)
                total_rows = meta.get('total_rows', 0)

                eta_str = ''
                if eta_seconds > 0:
                    if eta_seconds < 60:
                        eta_str = f' ~{eta_seconds}s restantes'
                    elif eta_seconds < 3600:
                        eta_str = f' ~{eta_seconds // 60}m {eta_seconds % 60}s restantes'
                    else:
                        h = eta_seconds // 3600
                        m = (eta_seconds % 3600) // 60
                        eta_str = f' ~{h}h {m}m restantes'

                return JsonResponse({
                    'state': 'PROGRESS',
                    'progress': meta.get('progress', 0),
                    'step': meta.get('step', 'procesando'),
                    'beneficiarios': meta.get('beneficiarios', 0),
                    'decretos': meta.get('decretos', 0),
                    'resoluciones': meta.get('resoluciones', 0),
                    'eta_seconds': eta_seconds,
                    'eta_str': eta_str,
                    'rows_processed': rows_processed,
                    'total_rows': total_rows,
                    'message': self._get_step_message(meta.get('step', ''), meta.get('progress', 0)) + eta_str
                })

            elif task.state == 'SUCCESS':
                result = task.result or {}
                return JsonResponse({
                    'state': 'SUCCESS',
                    'progress': 100,
                    'step': 'completado',
                    'beneficiarios': result.get('beneficiarios_creados', 0),
                    'decretos': result.get('decretos_creados', 0),
                    'resoluciones': result.get('resoluciones_creadas', 0),
                    'errores': result.get('errores', 0),
                    'total_filas': result.get('total_filas', 0),
                    'message': '¡Importación completada exitosamente!'
                })

            elif task.state == 'FAILURE':
                error_info = str(task.info) if task.info else 'Error desconocido'
                return JsonResponse({
                    'state': 'FAILURE',
                    'progress': 0,
                    'step': 'error',
                    'error': error_info,
                    'message': f'Error durante la importación: {error_info}'
                })

            else:
                return JsonResponse({
                    'state': task.state,
                    'progress': 0,
                    'step': task.state.lower(),
                    'message': f'Estado: {task.state}'
                })

    def _get_step_message(self, step, progress):
        """Genera mensaje descriptivo según el paso."""
        messages = {
            'leyendo': f'Leyendo archivo Excel... {progress}%',
            'limpiando': f'Limpiando tablas anteriores... {progress}%',
            'procesando': f'Procesando datos... {progress}%',
            'completado': 'Importación finalizada'
        }
        return messages.get(step, f'{step}... {progress}%')


class CancelImportView(View):
    """Vista para cancelar una importación en curso."""

    def post(self, request, task_id):
        from django.conf import settings as django_settings
        is_eager = getattr(django_settings, 'CELERY_TASK_ALWAYS_EAGER', False)

        if is_eager:
            _clear_eager_progress(task_id)
            return JsonResponse({
                'status': 'cancelled',
                'message': 'Importación cancelada'
            })
        else:
            from celery.result import AsyncResult
            from celery.app.control import Control
            from serviuapp.celery import app as celery_app

            celery_app.control.revoke(task_id, terminate=True)

            return JsonResponse({
                'status': 'cancelled',
                'message': 'Importación cancelada'
            })