#!/usr/bin/env bash
# ==============================================================================
# EXP-2: Shell Scripting for Automation
# Automated Timestamped Backup Script for DisasterWatch India
#
# Concepts Demonstrated:
# - Shell variables & dynamic timestamps
# - Conditionals (if-else) for path & file verification
# - Loops (for) for batch processing of .py source files
# - Archival & exit code error handling
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_BASE="$PROJECT_ROOT/backups"
BACKUP_DIR="$BACKUP_BASE/backup_$TIMESTAMP"
ARCHIVE_NAME="disasterwatch_backup_$TIMESTAMP.tar.gz"

echo "=========================================================="
echo " Starting Automated Backup Routine - DisasterWatch India"
echo " Timestamp: $TIMESTAMP"
echo " Destination: $BACKUP_DIR"
echo "=========================================================="

# 1. Conditionals: Ensure backup root exists
if [ ! -d "$BACKUP_BASE" ]; then
    echo "[INFO] Creating backups directory at $BACKUP_BASE..."
    mkdir -p "$BACKUP_BASE"
else
    echo "[INFO] Backups directory already exists."
fi

mkdir -p "$BACKUP_DIR/backend_scripts"
mkdir -p "$BACKUP_DIR/database"

# 2. Loops: Iterate over all Python scripts and copy them to the backup directory
echo "[INFO] Scanning and backing up Python source files..."
PY_COUNT=0

for py_file in "$PROJECT_ROOT"/backend/*.py "$PROJECT_ROOT"/backend/**/*.py; do
    if [ -f "$py_file" ]; then
        cp "$py_file" "$BACKUP_DIR/backend_scripts/"
        PY_COUNT=$((PY_COUNT + 1))
    fi
done

echo "[SUCCESS] Backed up $PY_COUNT Python source files."

# 3. Conditional: Backup SQLite Database if it exists
DB_FILE="$PROJECT_ROOT/data/disasterwatch.db"
if [ -f "$DB_FILE" ]; then
    echo "[INFO] Found active database: $DB_FILE"
    cp "$DB_FILE" "$BACKUP_DIR/database/disasterwatch_$TIMESTAMP.db"
    echo "[SUCCESS] Database backed up successfully."
else
    echo "[WARNING] Database file $DB_FILE not found. Skipping DB backup."
fi

# 4. Archival: Compress the timestamped folder into a .tar.gz archive
echo "[INFO] Compressing backup into $ARCHIVE_NAME..."
cd "$BACKUP_BASE"
tar -czf "$ARCHIVE_NAME" "backup_$TIMESTAMP"

# Remove uncompressed folder to save disk space
rm -rf "backup_$TIMESTAMP"

# 5. Verification
if [ -f "$BACKUP_BASE/$ARCHIVE_NAME" ]; then
    ARCHIVE_SIZE=$(ls -lh "$BACKUP_BASE/$ARCHIVE_NAME" | awk '{print $5}')
    echo "=========================================================="
    echo " [SUCCESS] Backup completed successfully!"
    echo " Archive: $BACKUP_BASE/$ARCHIVE_NAME ($ARCHIVE_SIZE)"
    echo "=========================================================="
else
    echo "[ERROR] Backup archive creation failed!"
    exit 1
fi
