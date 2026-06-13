#!/bin/bash
# Production Database Backup Utility
# Backups database, encrypts via OpenSSL, and uploads to AWS S3 storage target.

set -e

BACKUP_DIR="/tmp/pg_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/ignisai_backup_${TIMESTAMP}.sql"
ENCRYPTED_FILE="${BACKUP_FILE}.enc"

# Encryption key placeholder (Inject secure ENV in production runtime)
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-SecureDevOpsKey123}"
S3_BUCKET="${BACKUP_S3_BUCKET:-ignisai-db-backups}"

echo "Starting database backup snapshot..."
mkdir -p "${BACKUP_DIR}"

# Run pg_dump
PGPASSWORD="${POSTGRES_PASSWORD:-prodsecurepass}" pg_dump -h "${POSTGRES_HOST:-localhost}" -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-ignisai_prod}" -F p -f "${BACKUP_FILE}"

echo "Encrypting backup archive using AES-256..."
openssl enc -aes-256-cbc -salt -in "${BACKUP_FILE}" -out "${ENCRYPTED_FILE}" -k "${ENCRYPTION_KEY}" -pbkdf2

echo "Uploading encrypted snapshot to S3 bucket: s3://${S3_BUCKET}..."
if command -v aws &> /dev/null; then
    aws s3 cp "${ENCRYPTED_FILE}" "s3://${S3_BUCKET}/ignisai_backup_${TIMESTAMP}.sql.enc"
else
    echo "Warning: AWS CLI not found. Saved encrypted snapshot locally in ${ENCRYPTED_FILE}"
fi

# Cleanup local temp raw SQL backups
rm -f "${BACKUP_FILE}"

# Keep local encrypted backups only for 7 days
find "${BACKUP_DIR}" -type f -name "*.enc" -mtime +7 -delete

echo "Database backup snapshot process successfully completed."
