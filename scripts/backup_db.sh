#!/usr/bin/env bash
# Automated PostgreSQL backup to ./backups
set -e
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"
STAMP=$(date +%Y%m%d_%H%M%S)
FILE="$BACKUP_DIR/acuseek_$STAMP.sql"
echo "Backing up database to $FILE..."
docker compose exec -T postgres pg_dump -U acuseek acuseek > "$FILE"
# Keep only last 14 backups
ls -t "$BACKUP_DIR"/acuseek_*.sql 2>/dev/null | tail -n +15 | xargs -r rm --
echo "Backup complete: $FILE"
