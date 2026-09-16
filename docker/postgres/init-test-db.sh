#!/bin/sh
# Runs once, on first container start, via docker-entrypoint-initdb.d.
# Gives the test suite its own database so it can never touch dev data.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
    CREATE DATABASE portfolio_test OWNER "$POSTGRES_USER";
SQL
