# Dockerfile para serviuapp (Django + Celery + MySQL)
# Multi-stage build para imagen más ligera en producción

# ===========================================
# STAGE 1: Base con dependencias del sistema
# ===========================================
FROM python:3.11-slim AS base

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Crear usuario no-root
RUN adduser --disabled-password --gecos '' appuser

# ===========================================
# STAGE 2: Dependencias Python
# ===========================================
FROM base AS python-deps

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ===========================================
# STAGE 3: Imagen final
# ===========================================
FROM python-deps AS final

# Copiar entrypoint script
COPY --chown=appuser:appuser docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Copiar código de la aplicación
COPY --chown=appuser:appuser . .

# Crear directorios necesarios
RUN mkdir -p /app/logs /app/media /app/staticfiles /app/tmp && \
    chown -R appuser:appuser /app

# Cambiar a usuario no-root
USER appuser

# Entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Exponer puertos
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/healthcheck/ || exit 1

# Comando por defecto (sobrescrito en docker-compose)
CMD ["gunicorn", "serviu.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]