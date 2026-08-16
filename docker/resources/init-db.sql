-- Creates the dev database if it doesn't exist.
-- Postgres init scripts run only on first-time volume initialization.
SELECT 'CREATE DATABASE visdatamap_dev'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'visdatamap_dev')\gexec
