import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serviu.settings')
django.setup()

from serviuapp.models import Resoluciones, Beneficiarios, Decretos

print('=== VERIFICACIÓN DE DATOS ===')
print(f'Total beneficiarios: {Beneficiarios.objects.count()}')
print(f'Total decretos: {Decretos.objects.count()}')
print(f'Total resoluciones: {Resoluciones.objects.count()}')

if Resoluciones.objects.count() > 0:
    print('\n=== AÑOS ÚNICOS EN RESOLUCIONES ===')
    anos = list(Resoluciones.objects.values_list('ano_imputacion_res_of', flat=True).distinct().order_by('ano_imputacion_res_of'))
    print(f'Años únicos: {anos}')
    
    print('\n=== PRIMERAS 5 RESOLUCIONES ===')
    for r in Resoluciones.objects.all()[:5]:
        print(f'ID: {r.id_resolucion}, Año: {r.ano_imputacion_res_of}, Resolución: {r.resolucion}')
        
    print('\n=== DISTRIBUCIÓN POR AÑO ===')
    for ano in anos:
        count = Resoluciones.objects.filter(ano_imputacion_res_of=ano).count()
        print(f'Año {ano}: {count} resoluciones')
else:
    print('No hay resoluciones en la base de datos')