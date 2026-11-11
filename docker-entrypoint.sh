#!/bin/bash
# docker-entrypoint.sh - Script de entrada para el contenedor web
# Maneja migraciones, superusuario, collectstatic, etc.

set -e

echo "🚀 Iniciando serviuapp container..."

# Función para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Esperar a que la base de datos esté lista
log "⏳ Esperando base de datos..."
python manage.py wait_for_db --max-retries=30 --interval=2

# Ejecutar migraciones
log "📦 Ejecutando migraciones..."
python manage.py migrate --noinput

# Crear superusuario si no existe (solo si se definen las variables)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    log "👤 Creando superusuario..."
    python manage.py createsuperuser \
        --username "$DJANGO_SUPERUSER_USERNAME" \
        --email "$DJANGO_SUPERUSER_EMAIL" \
        --noinput || log "⚠️  Superusuario ya existe o error al crear"
fi

# Recopilar archivos estáticos
log "📁 Recopilando archivos estáticos..."
python manage.py collectstatic --noinput --clear

# Verificar configuración
log "🔍 Verificando configuración Django..."
python manage.py check --deploy || log "⚠️  Advertencias en check --deploy (normal en desarrollo)"

log "✅ Inicialización completada. Iniciando servidor..."

# Ejecutar el comando pasado (gunicorn, runserver, etc.)
exec "$@"