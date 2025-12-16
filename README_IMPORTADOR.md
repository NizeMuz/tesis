# Importador Rápido de Excel - ServiuApp

Este programa externo permite importar datos de Excel a la base de datos de ServiuApp de manera más rápida que el sistema web integrado.

## Características

- ✅ Importación en lotes para mayor velocidad
- ✅ Soporte para archivos .xlsx y .xls
- ✅ Manejo robusto de errores
- ✅ Logging detallado de la importación
- ✅ Validación y limpieza automática de datos
- ✅ Soporte para todos los campos del Excel
- ✅ Barra de progreso visual

## Campos del Excel Soportados

El programa espera un archivo Excel con las siguientes columnas en este orden:

1. `id_beneficiario`
2. `rut`
3. `dv`
4. `nombres`
5. `primer_apellido`
6. `segundo_apellido`
7. `comuna`
8. `provincia`
9. `codigo_proyecto`
10. `nombre_grupo`
11. `sexo`
12. `fecha_resolucion`
13. `decreto`
14. `resolucion`
15. `seleccion`
16. `tramo`
17. `tipologia`
18. `ano_imputacion_res_of`
19. `res. n°`
20. `fecha_res`
21. `REEMPLAZO/SUSTITUCION/ELIMINACION/RENUNCIA`
22. `RUT_NUEVO_BENEFICIARIO`
23. `DV2`
24. `NOMBRE`
25. `APELLIDO1`
26. `APELLIDO2`

## Instalación

1. Instalar las dependencias:
```bash
pip install -r requirements_importer.txt
```

## Uso

### Comando básico:
```bash
python excel_importer.py archivo_datos.xlsx
# o también con archivos .xls:
python excel_importer.py archivo_datos.xls
```

### Ejemplos:
```bash
python excel_importer.py beneficiarios_2024.xlsx
python excel_importer.py datos_antiguos.xls
```

## ⚠️ ADVERTENCIAS IMPORTANTES

1. **ELIMINACIÓN DE DATOS**: Este programa elimina TODOS los datos existentes en las tablas antes de importar los nuevos datos.

2. **BACKUP**: Siempre haga un backup de su base de datos antes de ejecutar la importación.

3. **FORMATO DEL EXCEL**: Asegúrese de que su archivo Excel (.xlsx o .xls) tenga exactamente las columnas esperadas.

## Proceso de Importación

1. El programa lee el archivo Excel completo
2. Limpia las tablas existentes (Resoluciones, Decretos, Beneficiarios)
3. Procesa los datos en lotes de 1000 registros
4. Valida y limpia cada campo automáticamente
5. Crea los registros en el orden correcto (Beneficiarios → Decretos → Resoluciones)
6. Genera un log detallado en `import_log.txt`

## Manejo de Errores

- **Fechas**: Convierte automáticamente números de serie de Excel a fechas
- **Campos vacíos**: Maneja valores nulos y vacíos apropiadamente
- **Tipos de datos**: Convierte automáticamente strings a enteros donde sea necesario
- **Longitud de campos**: Trunca automáticamente campos que excedan la longitud máxima

## Logs

El programa genera un archivo `import_log.txt` con:
- Información detallada del proceso
- Errores específicos por fila
- Resumen final de la importación
- Contadores de registros creados

## Rendimiento

- Procesa aproximadamente 1000-5000 registros por minuto (dependiendo del hardware)
- Usa inserción en lotes para optimizar la velocidad
- Muestra barra de progreso en tiempo real

## Solución de Problemas

### Error: "No module named 'pandas'"
```bash
pip install pandas openpyxl tqdm
```

### Error: "No such file or directory"
- Verifique que la ruta del archivo Excel sea correcta
- Use rutas absolutas si es necesario

### Error de conexión a base de datos
- Verifique que Django esté configurado correctamente
- Asegúrese de que la base de datos esté accesible

### Campos faltantes en Excel
- Verifique que todas las columnas esperadas estén presentes
- Los nombres de columnas deben coincidir exactamente

## Ejemplo de Uso Completo

```bash
# 1. Instalar dependencias
pip install -r requirements_importer.txt

# 2. Hacer backup de la base de datos (recomendado)
mysqldump -u usuario -p base_datos > backup_$(date +%Y%m%d).sql

# 3. Ejecutar importación
python excel_importer.py datos_beneficiarios.xlsx

# 4. Revisar logs
cat import_log.txt
```

## Contacto

Para soporte técnico o reportar problemas, contacte al administrador del sistema.