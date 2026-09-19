"""Preparar un clúster PostgreSQL local, sin modificar instalaciones existentes."""
import os
from pathlib import Path
import secrets
import subprocess
import psycopg
from psycopg import sql

root = Path(__file__).resolve().parent.parent
local = root / '.local'
bin_dir = local / 'postgresql' / 'pgsql' / 'bin'
data_dir = local / 'postgres-data'
password_file = local / 'postgres-admin-password'
if not password_file.exists():
    password_file.write_text(secrets.token_urlsafe(36), encoding='utf-8')
admin_password = password_file.read_text(encoding='utf-8').strip()
if not (data_dir / 'PG_VERSION').exists():
    subprocess.run([str(bin_dir / 'initdb.exe'), '-D', str(data_dir), '-U', 'postgres', '--pwfile', str(password_file), '--auth=scram-sha-256', '--encoding=UTF8', '--locale=C'], check=True)
    with (data_dir / 'postgresql.conf').open('a', encoding='utf-8') as config:
        config.write("\nlisten_addresses = '127.0.0.1'\nport = 5432\n")
status = subprocess.run([str(bin_dir / 'pg_ctl.exe'), '-D', str(data_dir), 'status'], capture_output=True)
if status.returncode:
    subprocess.run([str(bin_dir / 'pg_ctl.exe'), '-D', str(data_dir), '-l', str(local / 'postgres.log'), '-w', 'start'], check=True)
env_path = root / '.env'
text = env_path.read_text(encoding='utf-8-sig')
values = dict(line.split('=', 1) for line in text.splitlines() if '=' in line and not line.startswith('#'))
password = values.get('POSTGRES_PASSWORD') or secrets.token_urlsafe(36)
with psycopg.connect(host='127.0.0.1', user='postgres', password=admin_password, dbname='postgres', autocommit=True) as conn:
    if not conn.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', ('sigma',)).fetchone():
        # CREATEDB permite a Django crear su BD de pruebas; rol local no superusuario.
        conn.execute(sql.SQL('CREATE ROLE sigma LOGIN CREATEDB PASSWORD {}').format(sql.Literal(password)))
    if not conn.execute('SELECT 1 FROM pg_database WHERE datname = %s', ('sigma',)).fetchone():
        conn.execute('CREATE DATABASE sigma OWNER sigma')
values.update(POSTGRES_PASSWORD=password, POSTGRES_HOST='127.0.0.1')
lines = []
for line in text.splitlines():
    key = line.split('=', 1)[0]
    lines.append(f'{key}={values[key]}' if key in values else line)
env_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('PostgreSQL local listo. Credenciales guardadas sin mostrarlas.')
