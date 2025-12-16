# management/commands/import_data.py
import pandas as pd
from django.core.management.base import BaseCommand
from serviuapp.resources import BeneficiariosResource, DecretosResource
from serviuapp.models import Beneficiarios, Decretos

class Command(BaseCommand):
    help = 'Importa datos desde un archivo Excel y distribuye en Beneficiarios y Decretos'

    def add_arguments(self, parser):
        parser.add_argument('archivo', type=str)

    def handle(self, *args, **kwargs):
        archivo = kwargs['archivo']
        
        # Lee el archivo Excel
        df = pd.read_excel(archivo)

        # Separa los datos para Beneficiarios y Decretos
        beneficiarios_data = df[['id_beneficiario', 'rut', 'dv', 'primer_y_segundo_nombre', 'primer_apellido', 'segundo_apellido', 'comuna', 'provincia', 'codigo_proyecto', 'nombre_grupo', 'sexo']]
        decretos_data = df[['id_decreto', 'programa', 'tipologian', 'tramo', 'decreto_id_beneficiario']]

        # Importar Beneficiarios
        beneficiarios_resource = BeneficiariosResource()
        beneficiarios_resource.import_data(beneficiarios_data, dry_run=False)

        # Asegúrate de que Beneficiarios están guardados antes de importar Decretos
        # Esto es crucial para las relaciones de clave foránea
        for index, row in decretos_data.iterrows():
            beneficiario_id = row['id_beneficiario']
            try:
                beneficiario = Beneficiarios.objects.get(id_beneficiario=beneficiario_id)
            except Beneficiarios.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Beneficiario con id_beneficiario {beneficiario_id} no encontrado'))
                continue

            # Crear o actualizar el decreto
            Decretos.objects.update_or_create(
                id_decreto=row['id_decreto'],
                defaults={
                    'programa': row['programa'],
                    'tipologia': row['tipologia'],
                    'tramo': row['tramo'],
                    'decreto_id_beneficiario': beneficiario
                }
            )

        self.stdout.write(self.style.SUCCESS('Importación completada con éxito'))


#python manage.py import_data ruta/al/archivo.xlsx
