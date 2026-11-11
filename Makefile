# Makefile para serviuapp (Tesis) - Comandos Docker comunes
# Uso: make <comando>

.PHONY: help up down build logs shell migrate createsuperuser collectstatic test clean

# Variables
COMPOSE = docker-compose
ENV_FILE = .env

# Ayuda
help:
	@echo "Comandos disponibles para serviuapp (Tesis):"
	@echo ""
	@echo "  make up              - Levantar todos los contenedores (build + start)"
	@echo "  make down            - Bajar contenedores"
	@echo "  make build           - Reconstruir imágenes"
	@echo "  make logs            - Ver logs en tiempo real (todos los servicios)"
	@echo "  make logs-web        - Ver logs solo del servicio web"
	@echo "  make logs-worker     - Ver logs solo del celery worker"
	@echo "  make logs-beat       - Ver logs solo del celery beat"
	@echo "  make logs-db         - Ver logs solo de MySQL"
	@echo "  make shell           - Abrir shell en contenedor web"
	@echo "  make dbshell         - Abrir MySQL shell"
	@echo "  make migrate         - Ejecutar migraciones"
	@echo "  make makemigrations  - Crear nuevas migraciones"
	@echo "  make createsuperuser - Crear superusuario Django"
	@echo "  make collectstatic   - Recopilar archivos estáticos"
	@echo "  make test            - Ejecutar tests"
	@echo "  make clean           - Limpiar contenedores, volúmenes e imágenes"
	@echo "  make restart         - Reiniciar servicios"
	@echo "  make status          - Ver estado de contenedores"
	@echo "  make env             - Ver configuración resuelta"
	@echo "  make backup-db       - Backup de base de datos"
	@echo "  make gen-secret      - Generar SECRET_KEY para Django"

# Levantar todo
up:
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "⚠️  No existe .env. Copiando desde .env.example..."; \
		cp .env.example .env; \
		echo "✏️  Edita .env con tus valores antes de continuar."; \
		exit 1; \
	fi
	$(COMPOSE) up -d --build

# Bajar todo
down:
	$(COMPOSE) down

# Reconstruir imágenes
build:
	$(COMPOSE) build --no-cache

# Ver logs
logs:
	$(COMPOSE) logs -f

logs-web:
	$(COMPOSE) logs -f web

logs-worker:
	$(COMPOSE) logs -f celery-worker

logs-beat:
	$(COMPOSE) logs -f celery-beat

logs-db:
	$(COMPOSE) logs -f db

# Shell en contenedor web
shell:
	$(COMPOSE) exec web bash

# Shell en MySQL
dbshell:
	$(COMPOSE) exec db mysql -u root -p

# Django commands
migrate:
	$(COMPOSE) exec web python manage.py migrate

makemigrations:
	$(COMPOSE) exec web python manage.py makemigrations

createsuperuser:
	$(COMPOSE) exec web python manage.py createsuperuser

collectstatic:
	$(COMPOSE) exec web python manage.py collectstatic --noinput

# Tests
test:
	$(COMPOSE) exec web python manage.py test

# Limpieza completa
clean:
	$(COMPOSE) down -v --rmi all --remove-orphans
	docker system prune -f

# Reiniciar
restart:
	$(COMPOSE) restart

# Estado
status:
	$(COMPOSE) ps

# Ver variables de entorno cargadas
env:
	$(COMPOSE) config

# Backup de base de datos
backup-db:
	@mkdir -p backups
	$(COMPOSE) exec -T db mysqldump -u root -p$${MYSQL_ROOT_PASSWORD} serviuapp > backups/serviuapp_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup guardado en backups/"

# Restore de base de datos (uso: make restore-db FILE=backups/archivo.sql)
restore-db:
	@if [ -z "$(FILE)" ]; then \
		echo "Uso: make restore-db FILE=backups/archivo.sql"; \
		exit 1; \
	fi
	$(COMPOSE) exec -T db mysql -u root -p$${MYSQL_ROOT_PASSWORD} serviuapp < $(FILE)

# Generar SECRET_KEY para Django
gen-secret:
	@python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"