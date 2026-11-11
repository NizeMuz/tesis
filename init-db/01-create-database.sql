-- Script de inicialización de base de datos para serviuapp
-- Se ejecuta automáticamente al iniciar el contenedor MySQL por primera vez

-- Crear base de datos con charset correcto si no existe
CREATE DATABASE IF NOT EXISTS `serviuapp`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Crear usuario de la app si no existe (para conexión desde Docker)
CREATE USER IF NOT EXISTS 'serviuapp_user'@'%' IDENTIFIED BY 'serviuapp_pass_segura';

-- Dar permisos al usuario de la app
GRANT ALL PRIVILEGES ON `serviuapp`.* TO 'serviuapp_user'@'%';

-- Aplicar cambios
FLUSH PRIVILEGES;

-- Seleccionar la base de datos
USE `serviuapp`;

-- Las tablas serán creadas por Django migrations al iniciar la app
-- Este script solo prepara la BD y el usuario