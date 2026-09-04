FROM pgvector/pgvector:pg16

COPY init.sql /docker-entrypoint-initdb.d/init.sql
COPY postgresql.conf /etc/postgresql/postgresql.conf
