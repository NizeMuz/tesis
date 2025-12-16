import os
import logging
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, DateWidget
from datetime import datetime, date, timedelta
from .models import Beneficiarios, Decretos, Resoluciones

def configure_logger():
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)  # Crear el directorio si no existe

    log_filename = os.path.join(log_dir, 'app.log')
    logger = logging.getLogger('import_logger')
    logger.setLevel(logging.INFO)

    # Crea un manejador de archivo
    handler = logging.FileHandler(log_filename, mode='a')  # 'a' para añadir al archivo
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Evitar añadir múltiples manejadores al logger
    if not logger.hasHandlers():
        logger.addHandler(handler)

    return logger

class CustomDateWidget(DateWidget):
    def clean(self, value, row=None, **kwargs):
        if value is None or value == '':
            return None
        
        # Si ya es un objeto datetime, convertir a date
        if isinstance(value, datetime):
            return value.date()
        
        # Si ya es un objeto date, devolverlo tal como está
        if isinstance(value, date):
            return value
        
        # Convertir a string para procesamiento
        value_str = str(value).strip()
        if not value_str or value_str == '-':
            return None
        
        # Intentar convertir número de serie de Excel a fecha
        try:
            # Si es un número (serie de Excel), convertir a fecha
            if value_str.isdigit() or (value_str.replace('.', '').isdigit()):
                excel_serial = float(value_str)
                # Excel cuenta desde 1900-01-01, pero tiene un bug con 1900 como año bisiesto
                # Por eso restamos 2 días adicionales
                if excel_serial > 59:  # Después del 28 de febrero de 1900
                    excel_date = datetime(1900, 1, 1) + timedelta(days=excel_serial - 2)
                else:
                    excel_date = datetime(1900, 1, 1) + timedelta(days=excel_serial - 1)
                return excel_date.date()
        except (ValueError, OverflowError):
            pass
        
        # Intentar formato DD-MM-YYYY
        try:
            return datetime.strptime(value_str, '%d-%m-%Y').date()
        except ValueError:
            pass
        
        # Intentar formato YYYY-MM-DD
        try:
            return datetime.strptime(value_str, '%Y-%m-%d').date()
        except ValueError:
            pass
        
        # Intentar formato DD/MM/YYYY
        try:
            return datetime.strptime(value_str, '%d/%m/%Y').date()
        except ValueError:
            pass
        
        raise ValueError(f"Formato de fecha inválido en la fila {row}: {value}")

class BeneficiariosResource(resources.ModelResource):
    fecha_resolucion = fields.Field(
        column_name='fecha_resolucion',
        attribute='fecha_resolucion',
        widget=CustomDateWidget()
    )

    class Meta:
        model = Beneficiarios
        exclude = ('id',)
        import_id_fields = ['id_beneficiario']
        skip_unchanged = True
        report_skipped = True

    def before_import(self, dataset, **kwargs):
        self.logger = configure_logger()
        self.logger.info("Iniciando sesión de importación")

        # Limpiar tablas antes de la importación
        Beneficiarios.objects.all().delete()
        Decretos.objects.all().delete()
        Resoluciones.objects.all().delete()
        self.logger.info("Tablas de Beneficiarios, Decretos y Resoluciones han sido limpiadas.")

        dataset.headers = [header.lower() for header in dataset.headers]

    def after_import_row(self, row, row_result, row_number=None, **kwargs):
        try:
            beneficiario = Beneficiarios.objects.get(id_beneficiario=row['id_beneficiario'])

            # Datos para la tabla Decretos
            decreto_id = row.get('id_beneficiario')
            decreto = row.get('decreto')
            tipologia = row.get('tipologia')
            tramo = row.get('tramo')

            # Datos para la tabla Resoluciones
            resolucion_id = row.get('id_beneficiario')
            resolucion = row.get('resolucion')
            fecha_resolucion = row.get('fecha_resolucion')
            seleccion = row.get('seleccion')
            ano_imputacion_res_of = row.get('ano_imputacion_res_of')

            # Convertir fecha_resolucion a formato 'YYYY-MM-DD' si es datetime
            if fecha_resolucion is not None and isinstance(fecha_resolucion, datetime):
                fecha_resolucion = fecha_resolucion.strftime('%Y-%m-%d')

            # Crear o actualizar el decreto
            if decreto_id:
                try:
                    _decreto, created = Decretos.objects.update_or_create(
                        id_decreto=decreto_id,
                        defaults={
                            'decreto': decreto,
                            'tipologia': tipologia,
                            'tramo': tramo,
                            'decreto_id_beneficiario': beneficiario
                        }
                    )
                    self.logger.info(f"Decreto {'creado' if created else 'actualizado'}: {_decreto}")
                except Exception as e:
                    self.logger.error(f"Error al crear o actualizar el decreto: {e}")

            # Crear o actualizar la resolución
            if resolucion_id:
                try:
                    _resolucion, created = Resoluciones.objects.update_or_create(
                        id_resolucion=resolucion_id,
                        defaults={
                            'resolucion': resolucion,
                            'fecha_resolucion': fecha_resolucion,
                            'seleccion': seleccion,
                            'ano_imputacion_res_of': ano_imputacion_res_of,
                            'resolucion_id_beneficiario': beneficiario
                        }
                    )
                    self.logger.info(f"Resolución {'creada' if created else 'actualizada'}: {_resolucion}")
                except Exception as e:
                    self.logger.error(f"Error al crear o actualizar la resolución: {e}")

        except Exception as e:
            self.logger.error(f"Error al procesar la fila {row_number}: {e}")

    def after_import(self, dataset, result, **kwargs):
        self.logger.info("Finalizada sesión de importación.")
        logging.shutdown()  # Asegura que los manejadores del logger se cierren correctamente.
