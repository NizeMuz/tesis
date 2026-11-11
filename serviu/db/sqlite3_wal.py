"""
SQLite wrapper para Django con WAL mode y optimizaciones de concurrencia.
Permite lecturas concurrentes durante escrituras (importante para Celery + Web).
"""
from django.db.backends.sqlite3 import base as sqlite3_base
from django.db.backends.sqlite3.base import DatabaseWrapper as BaseDatabaseWrapper
import sqlite3


class DatabaseWrapper(BaseDatabaseWrapper):
    def get_connection_params(self):
        params = super().get_connection_params()
        # Solo pasar parámetros soportados por sqlite3.connect()
        # Los PRAGMAs se ejecutan en get_new_connection()
        options = params.get('options', {})
        timeout = options.get('timeout', 30)
        params['timeout'] = timeout
        # Remover options para evitar error de argumentos extra
        params.pop('options', None)
        return params

    def get_new_connection(self, conn_params):
        conn = sqlite3.connect(**conn_params)
        # Aplicar PRAGMAs para optimizar concurrencia
        cursor = conn.cursor()
        try:
            # WAL mode: lectores no bloquean escritores y viceversa
            cursor.execute('PRAGMA journal_mode=WAL')
            # busy_timeout: esperar hasta 30s si la BD está bloqueada
            cursor.execute('PRAGMA busy_timeout=30000')
            # synchronous=NORMAL: más rápido que FULL, seguro con WAL
            cursor.execute('PRAGMA synchronous=NORMAL')
            # cache_size: 32MB de caché (negativo = KB)
            cursor.execute('PRAGMA cache_size=-32768')
            # temp_store: usar memoria para tablas temporales
            cursor.execute('PRAGMA temp_store=MEMORY')
            # mmap_size: 256MB para mapeo de memoria
            cursor.execute('PRAGMA mmap_size=268435456')
            # page_size: 4KB páginas (por defecto, pero explicit)
            cursor.execute('PRAGMA page_size=4096')
            # foreign_keys: activar restricciones FK
            cursor.execute('PRAGMA foreign_keys=ON')
        finally:
            cursor.close()
        return conn


# Para compatibilidad con Django
Database = sqlite3_base.Database