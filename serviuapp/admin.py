from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from django.urls import path
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import uuid

from .models import Beneficiarios, Decretos, Resoluciones
from .resources import BeneficiariosResource
from .tasks import importar_excel_task


class BeneficiariosAdmin(ImportExportModelAdmin):
    skip_import_confirm = True
    resource_class = BeneficiariosResource
    list_display = ["id_beneficiario", "rut"]
    # Override import_export's template to use our custom one
    # Only set import_export_change_list_template, let the mixin handle change_list_template
    import_export_change_list_template = "admin/serviuapp/beneficiarios/change_list.html"
    # Don't set change_list_template directly - it causes recursion with import_export's template chain
    change_list_template = None

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('importar-progreso/', self.admin_site.admin_view(self.importar_progreso_view), name='serviuapp_beneficiarios_importar_progreso'),
            path('importar-progreso/upload/', self.admin_site.admin_view(self.importar_progreso_upload), name='serviuapp_beneficiarios_importar_progreso_upload'),
            path('importar-progreso/progress/<str:task_id>/', self.admin_site.admin_view(self.importar_progreso_progress), name='serviuapp_beneficiarios_importar_progreso_progress'),
        ]
        return custom_urls + urls

    def importar_progreso_view(self, request):
        """Vista para la página de importación con barra de progreso"""
        context = self.admin_site.each_context(request)
        context.update({
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        })
        return render(request, 'admin/serviuapp/beneficiarios/import_progress.html', context)

    @method_decorator(csrf_exempt)
    def importar_progreso_upload(self, request):
        """Recibe el archivo y lanza la tarea Celery"""
        if request.method != 'POST':
            return JsonResponse({'error': 'Método no permitido'}, status=405)

        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No se envió ningún archivo'}, status=400)

        uploaded_file = request.FILES['file']

        # Validar extensión
        allowed_extensions = ['.xlsx', '.xls']
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext not in allowed_extensions:
            return JsonResponse({'error': f'Formato no permitido. Use .xlsx o .xls'}, status=400)

        # Validar tamaño (100MB max)
        max_size = 100 * 1024 * 1024
        if uploaded_file.size > max_size:
            return JsonResponse({'error': f'Archivo muy grande. Máximo {max_size // (1024*1024)}MB'}, status=400)

        # Guardar archivo temporalmente
        temp_filename = f"import_{uuid.uuid4().hex}{file_ext}"
        temp_path = os.path.join('temp_imports', temp_filename)
        full_temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_imports')
        os.makedirs(full_temp_dir, exist_ok=True)
        saved_path = default_storage.save(temp_path, ContentFile(uploaded_file.read()))
        full_file_path = os.path.join(settings.MEDIA_ROOT, saved_path)

        # Lanzar tarea Celery
        task = importar_excel_task.delay(full_file_path)

        return JsonResponse({
            'status': 'started',
            'task_id': task.id,
            'message': 'Importación iniciada. Consultando progreso...'
        })

    def importar_progreso_progress(self, request, task_id):
        """Consulta el progreso de la tarea o cancela si se envía POST con action=cancel"""
        if request.method == 'POST':
            import json
            try:
                data = json.loads(request.body)
                if data.get('action') == 'cancel':
                    from celery.app.control import Control
                    from serviuapp.celery import app as celery_app
                    celery_app.control.revoke(task_id, terminate=True)
                    return JsonResponse({'status': 'cancelled', 'message': 'Importación cancelada'})
            except:
                pass
            return JsonResponse({'error': 'Acción no válida'}, status=400)

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
        messages = {
            'leyendo': f'Leyendo archivo Excel... {progress}%',
            'limpiando': f'Limpiando tablas anteriores... {progress}%',
            'procesando': f'Procesando datos... {progress}%',
            'completado': 'Importación finalizada'
        }
        return messages.get(step, f'{step}... {progress}%')


admin.site.register(Beneficiarios, BeneficiariosAdmin)
admin.site.site_header = 'ServiuApp Admin'
admin.site.site_title = 'ServiuApp'
