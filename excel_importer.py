#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Programa externo para importar datos de Excel a la base de datos de ServiuApp
Más rápido que el sistema de importación web integrado

Campos del Excel en orden:
id_beneficiario, rut, dv, nombres, primer_apellido, segundo_apellido, comuna, provincia, 
código_proyecto, nombre_grupo, sexo, fecha_resolucion, decreto, resolucion, seleccion, 
tramo, tipologia, ano_imputacion_res_of, res_n, fecha_res, 
REEMPLAZO/SUSTITUCION/ELIMINACION/RENUNCIA, RUT_NUEVO_BENEFICIARIO, DV2, NOMBRE, APELLIDO1, APELLIDO2
"""

import os
import sys
import django
import pandas as pd
from datetime import datetime, date
import logging
from tqdm import tqdm

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serviu.settings')
django.setup()

from serviuapp.models import Beneficiarios, Decretos, Resoluciones

def setup_logging():
    """Configurar logging para el importador"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('import_log.txt', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def convert_excel_date(value):
    """Convertir fecha de Excel a formato Python date"""
    if pd.isna(value) or value == '' or value == '-':
        return None
    
    if isinstance(value, (datetime, date)):
        return value.date() if isinstance(value, datetime) else value
    
    # Si es un número de serie de Excel
    if isinstance(value, (int, float)):
        try:
            # Excel cuenta desde 1900-01-01
            if value > 59:  # Después del 28 de febrero de 1900
                excel_date = datetime(1900, 1, 1) + pd.Timedelta(days=value - 2)
            else:
                excel_date = datetime(1900, 1, 1) + pd.Timedelta(days=value - 1)
            return excel_date.date()
        except:
            return None
    
    # Intentar convertir string
    value_str = str(value).strip()
    if not value_str or value_str == '-':
        return None
    
    # Formatos de fecha comunes
    date_formats = ['%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']
    for fmt in date_formats:
        try:
            return datetime.strptime(value_str, fmt).date()
        except ValueError:
            continue
    
    return None

def clean_integer(value):
    """Limpiar y convertir valor a entero"""
    if pd.isna(value) or value == '' or value == '-':
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None

def clean_string(value, max_length=None):
    """Limpiar y convertir valor a string"""
    if pd.isna(value) or value == '':
        return ''
    
    result = str(value).strip()
    if max_length and len(result) > max_length:
        result = result[:max_length]
    
    return result

def import_excel_data(excel_file_path, batch_size=1000):
    """Importar datos desde archivo Excel"""
    logger = setup_logging()
    
    logger.info(f"Iniciando importación desde: {excel_file_path}")
    
    try:
        # Leer archivo Excel
        logger.info("Leyendo archivo Excel...")
        df = pd.read_excel(excel_file_path)
        
        logger.info(f"Archivo leído exitosamente. Total de filas: {len(df)}")
        logger.info(f"Columnas encontradas: {list(df.columns)}")
        
        # Mapear columnas del Excel a nombres esperados
        column_mapping = {
            'id_beneficiario': 'id_beneficiario',
            'rut': 'rut',
            'dv': 'dv',
            'nombres': 'nombres',
            'primer_apellido': 'primer_apellido',
            'segundo_apellido': 'segundo_apellido',
            'comuna': 'comuna',
            'provincia': 'provincia',
            'codigo_proyecto': 'codigo_proyecto',
            'nombre_grupo': 'nombre_grupo',
            'sexo': 'sexo',
            'fecha_resolucion': 'fecha_resolucion',
            'decreto': 'decreto',
            'resolucion': 'resolucion',
            'seleccion': 'seleccion',
            'tramo': 'tramo',
            'tipologia': 'tipologia',
            'ano_imputacion_res_of': 'ano_imputacion_res_of',
            'res. n°': 'res_n',
            'fecha_res': 'fecha_res',
            'REEMPLAZO/SUSTITUCION/ELIMINACION/RENUNCIA': 'tipo_cambio',
            'RUT_NUEVO_BENEFICIARIO': 'rut_nuevo',
            'DV2': 'dv2',
            'NOMBRE': 'nombre_nuevo',
            'APELLIDO1': 'apellido1_nuevo',
            'APELLIDO2': 'apellido2_nuevo'
        }
        
        # Renombrar columnas si es necesario
        df_columns_lower = {col: col.lower().strip() for col in df.columns}
        
        # Limpiar datos antes de la importación
        logger.info("Limpiando tablas existentes...")
        Resoluciones.objects.all().delete()
        Decretos.objects.all().delete()
        Beneficiarios.objects.all().delete()
        
        # Contadores
        beneficiarios_creados = 0
        decretos_creados = 0
        resoluciones_creadas = 0
        errores = 0
        
        # Procesar en lotes
        logger.info(f"Procesando datos en lotes de {batch_size}...")
        
        for start_idx in tqdm(range(0, len(df), batch_size), desc="Procesando lotes"):
            end_idx = min(start_idx + batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx]
            
            beneficiarios_batch = []
            decretos_batch = []
            resoluciones_batch = []
            
            for idx, row in batch_df.iterrows():
                try:
                    # Crear beneficiario
                    beneficiario_data = {
                        'id_beneficiario': clean_integer(row.get('id_beneficiario')),
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
                    
                    if beneficiario_data['id_beneficiario']:
                        beneficiario = Beneficiarios(**beneficiario_data)
                        beneficiarios_batch.append(beneficiario)
                        
                        # Preparar decreto
                        decreto_data = {
                            'id_decreto': beneficiario_data['id_beneficiario'],
                            'decreto': clean_string(row.get('decreto'), 10),
                            'tipologia': clean_string(row.get('tipologia'), 50),
                            'tramo': clean_integer(row.get('tramo'))
                        }
                        
                        # Preparar resolución
                        resolucion_data = {
                            'id_resolucion': beneficiario_data['id_beneficiario'],
                            'resolucion': clean_integer(row.get('resolucion')),
                            'fecha_resolucion': convert_excel_date(row.get('fecha_resolucion')),
                            'seleccion': clean_string(row.get('seleccion'), 50),
                            'ano_imputacion_res_of': clean_integer(row.get('ano_imputacion_res_of'))
                        }
                        
                        decretos_batch.append((decreto_data, beneficiario))
                        resoluciones_batch.append((resolucion_data, beneficiario))
                        
                except Exception as e:
                    logger.error(f"Error procesando fila {idx}: {e}")
                    errores += 1
            
            # Insertar lote de beneficiarios
            if beneficiarios_batch:
                try:
                    Beneficiarios.objects.bulk_create(beneficiarios_batch, ignore_conflicts=True)
                    beneficiarios_creados += len(beneficiarios_batch)
                    logger.info(f"Lote {start_idx//batch_size + 1}: {len(beneficiarios_batch)} beneficiarios creados")
                except Exception as e:
                    logger.error(f"Error creando lote de beneficiarios: {e}")
            
            # Insertar decretos
            for decreto_data, beneficiario in decretos_batch:
                try:
                    # Buscar el beneficiario creado
                    beneficiario_obj = Beneficiarios.objects.get(id_beneficiario=beneficiario.id_beneficiario)
                    decreto_data['decreto_id_beneficiario'] = beneficiario_obj
                    
                    Decretos.objects.create(**decreto_data)
                    decretos_creados += 1
                except Exception as e:
                    logger.error(f"Error creando decreto para beneficiario {beneficiario.id_beneficiario}: {e}")
                    errores += 1
            
            # Insertar resoluciones
            for resolucion_data, beneficiario in resoluciones_batch:
                try:
                    # Buscar el beneficiario creado
                    beneficiario_obj = Beneficiarios.objects.get(id_beneficiario=beneficiario.id_beneficiario)
                    resolucion_data['resolucion_id_beneficiario'] = beneficiario_obj
                    
                    Resoluciones.objects.create(**resolucion_data)
                    resoluciones_creadas += 1
                except Exception as e:
                    logger.error(f"Error creando resolución para beneficiario {beneficiario.id_beneficiario}: {e}")
                    errores += 1
        
        # Resumen final
        logger.info("=== RESUMEN DE IMPORTACIÓN ===")
        logger.info(f"Beneficiarios creados: {beneficiarios_creados}")
        logger.info(f"Decretos creados: {decretos_creados}")
        logger.info(f"Resoluciones creadas: {resoluciones_creadas}")
        logger.info(f"Errores: {errores}")
        logger.info("Importación completada exitosamente")
        
        return True
        
    except Exception as e:
        logger.error(f"Error crítico durante la importación: {e}")
        return False

def main():
    """Función principal"""
    if len(sys.argv) != 2:
        print("Uso: python excel_importer.py <ruta_archivo_excel>")
        print("Ejemplo: python excel_importer.py datos.xlsx")
        sys.exit(1)
    
    excel_file = sys.argv[1]
    
    if not os.path.exists(excel_file):
        print(f"Error: El archivo {excel_file} no existe")
        sys.exit(1)
    
    print("=== IMPORTADOR RÁPIDO DE EXCEL - SERVIUAPP ===")
    print(f"Archivo a importar: {excel_file}")
    
    confirm = input("¿Desea continuar? Esto eliminará todos los datos existentes (s/N): ")
    if confirm.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
        print("Importación cancelada")
        sys.exit(0)
    
    success = import_excel_data(excel_file)
    
    if success:
        print("\n✅ Importación completada exitosamente")
        print("Revise el archivo 'import_log.txt' para más detalles")
    else:
        print("\n❌ Error durante la importación")
        print("Revise el archivo 'import_log.txt' para más detalles")
        sys.exit(1)

if __name__ == "__main__":
    main()