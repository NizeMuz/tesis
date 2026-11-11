# 🐳 Docker Setup - serviuapp (Tesis)

Guía rápida para levantar el proyecto con Docker Compose.

## 📋 Requisitos previos

- Docker Desktop / Docker Engine + Docker Compose
- (Opcional) Ollama instalado localmente para chat IA: `ollama pull mistral`

## 🚀 Inicio rápido

```bash
# 1. Clonar/entrar al proyecto
cd tesis

# 2. Copiar variables de entorno y editar
cp .env.example .env
# Edita .env con tus valores (SECRET_KEY, passwords, API keys, etc.)

# 3. Levantar todo
make up
# o directamente: docker-compose up -d --build

# 4. Ver logs
make logs
```

## 🌐 Accesos

| Servicio | URL |
|----------|-----|
| **App Web** | http://localhost:8000 |
| **Admin Django** | http://localhost:8000/admin |
| **Healthcheck** | http://localhost:8000/healthcheck/ |
| **MySQL** | localhost:3306 |
| **Redis** | localhost:6379 |

## 🔧 Comandos útiles (Makefile)

```bash
make help          # Ver todos los comandos
make up            # Levantar contenedores
make down          # Bajar contenedores
make build         # Rebuild imágenes
make logs          # Logs todos los servicios
make logs-web      # Logs solo web
make logs-worker   # Logs celery worker
make logs-beat     # Logs celery beat
make shell         # Shell en contenedor web
make dbshell       # MySQL shell
make migrate       # Ejecutar migraciones
make createsuperuser # Crear admin manualmente
make collectstatic # Recopilar estáticos
make test          # Tests
make backup-db     # Backup BD
make clean         # Limpieza total
make gen-secret    # Generar SECRET_KEY
```

## 📦 Servicios incluidos

| Servicio | Descripción | Puerto |
|----------|-------------|--------|
| **web** | Django + Gunicorn | 8000 |
| **db** | MySQL 8.0 | 3306 |
| **redis** | Redis 7 (Celery broker) | 6379 |
| **celery-worker** | Procesa tareas async (imports, chat) | - |
| **celery-beat** | Scheduler tareas periódicas | - |

## 🗂️ Variables de entorno clave (.env)

```bash
# Django
DEBUG=False
SECRET_KEY=clave_muy_larga_y_segura
ALLOWED_HOSTS=localhost,127.0.0.1,tudominio.com

# MySQL
MYSQL_DATABASE=serviuapp
MYSQL_USER=serviuapp_user
MYSQL_PASSWORD=password_segura
MYSQL_ROOT_PASSWORD=root_password_segura

# IA Chat (opcional)
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
OLLAMA_URL=http://host.docker.internal:11434  # Para acceder a Ollama en el host
OLLAMA_MODEL=mistral

# Superusuario auto-creado (opcional)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=password_admin
```

## 🔄 Flujo de desarrollo

```bash
# Cambios en código Python -> se recargan automáticamente (volumes)
# Cambios en requirements.txt -> make build && make up
# Cambios en modelos -> make makemigrations && make migrate
# Nuevos static files -> make collectstatic
```

## 📊 Cargar datos históricos (opcional)

Los archivos SQL grandes (~35MB) no se incluyen en la imagen.

```bash
# Opción 1: Copiar SQL a init-db/ y descomentar en docker-compose.yml
cp /ruta/a/serviuapp.sql init-db/
# Editar docker-compose.yml: descomentar la línea del volume init-db
# make down && make up

# Opción 2: Restaurar manualmente
make restore-db FILE=backups/serviuapp_20241110.sql
```

## 🛠️ Solución de problemas

**Error: "Can't connect to MySQL"**
```bash
make logs-db
# Verificar que el healthcheck pase (puede tardar 30-60s la primera vez)
```

**Error: "SECRET_KEY not set"**
```bash
make gen-secret
# Copiar la clave generada a .env
```

**Error: "Table doesn't exist"**
```bash
make migrate
```

**Ollama no responde desde Docker**
```bash
# En el host, permitir conexiones externas:
ollama serve  # Debe escuchar en 0.0.0.0:11434
# O configurar OLLAMA_URL=http://host.docker.internal:11434 en .env
```

**Permisos en volumes (Linux)**
```bash
sudo chown -R $USER:$USER .
```

## 🧪 Testing

```bash
make test
# O directamente:
docker-compose exec web python manage.py test
```

## 📝 Estructura de archivos Docker

```
tesis/
├── Dockerfile              # Imagen multi-stage
├── docker-compose.yml      # Orquestación completa
├── docker-entrypoint.sh    # Init: migraciones, superuser, collectstatic
├── .env.example            # Template de variables
├── .dockerignore           # Archivos excluidos del build
├── Makefile                # Comandos shortcuts
├── init-db/
│   └── 01-create-database.sql  # Init MySQL
├── requirements.txt        # Dependencias Python
└── serviu/
    └── settings.py         # Config Django (usa env vars)
```

## 🚀 Producción

Para producción, considera:
- Usar `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up`
- Configurar reverse proxy (nginx/traefik) con SSL
- Usar secrets de Docker Swarm/K8s para passwords
- Desactivar DEBUG y configurar ALLOWED_HOSTS reales
- Configurar backup automático de MySQL
- Monitoreo (Prometheus/Grafana, Sentry, etc.)

---

**¡Listo!** 🎉 Ejecuta `make up` y accede a http://localhost:8000