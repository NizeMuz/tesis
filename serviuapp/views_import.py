"""
Vistas para importación de Excel con progreso en tiempo real usando Celery.
"""
import os
import uuid
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

        # Lanzar tarea Celery
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
        task = importar_excel_task.AsyncResult(task_id)

        if task.state == 'PENDING':
            # La tarea aún no ha sido tomada por un worker
            return JsonResponse({
                'state': 'PENDING',
                'progress': 0,
                'step': 'esperando',
                'message': 'Esperando a que inicie el procesamiento...'
            })

        elif task.state == 'PROGRESS':
            # La tarea está en progreso - devolver meta actualizada
            meta = task.info or {}
            return JsonResponse({
                'state': 'PROGRESS',
                'progress': meta.get('progress', 0),
                'step': meta.get('step', 'procesando'),
                'beneficiarios': meta.get('beneficiarios', 0),
                'decretos': meta.get('decretos', 0),
                'resoluciones': meta.get('resoluciones', 0),
                'message': self._get_step_message(meta.get('step', ''), meta.get('progress', 0))
            })

        elif task.state == 'SUCCESS':
            # Tarea completada exitosamente
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
            # Error en la tarea
            error_info = str(task.info) if task.info else 'Error desconocido'
            return JsonResponse({
                'state': 'FAILURE',
                'progress': 0,
                'step': 'error',
                'error': error_info,
                'message': f'Error durante la importación: {error_info}'
            })

        else:
            # Otros estados (RETRY, REVOKED, etc.)
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
        from celery.result import AsyncResult
        from celery.app.control import Control
        from serviuapp.celery import app as celery_app

        # Revocar la tarea
        celery_app.control.revoke(task_id, terminate=True)

        return JsonResponse({
            'status': 'cancelled',
            'message': 'Importación cancelada'
        })