#!/usr/bin/env bash
# ==============================================================================
# EXP-1: The Shell & CLI Mastery
# Telemetry and Log Analysis Pipeline
#
# Concepts Demonstrated:
# - Linux filesystem navigation & path discovery (find, ls)
# - Text inspection & extraction (cat, grep, awk, sort)
# - Command chaining via Piping (|)
# - Standard output redirection (> for overwrite, >> for append)
# - File permission controls (chmod)
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_FILE="$PROJECT_ROOT/data/telemetry_analysis_report.txt"

echo "=========================================================="
echo " Executing CLI Telemetry Analysis Pipeline (EXP-1)"
echo "=========================================================="

# 1. Redirection (>): Initialize report header with overwrite
echo "==========================================================" > "$REPORT_FILE"
echo "        DISASTERWATCH TELEMETRY & LOG AUDIT REPORT        " >> "$REPORT_FILE"
echo "        Generated on: $(date)                             " >> "$REPORT_FILE"
echo "==========================================================" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 2. Piping (|) & Redirection (>>): Scan Python backend files using find & wc
echo "--- 1. CODEBASE FILE INVENTORY ---" >> "$REPORT_FILE"
echo "Total Python backend modules: $(find "$PROJECT_ROOT/backend" -type f -name "*.py" | wc -l)" >> "$REPORT_FILE"
echo "Monitored Static Assets: $(find "$PROJECT_ROOT/frontend" -type f | wc -l)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 3. Piping (|) & grep: Extract High and Critical thresholds from risk engine rules
echo "--- 2. ACTIVE RISK ENGINE THRESHOLDS ---" >> "$REPORT_FILE"
cat "$PROJECT_ROOT/backend/services/risk_engine.py" \
    | grep -E "Critical|High|threshold" \
    | grep -v "^\s*#" \
    | head -n 15 >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 4. Search and count error occurrences in test outputs or refresh logs
echo "--- 3. RECENT EVENT LOG SUMMARY ---" >> "$REPORT_FILE"
if [ -f "$PROJECT_ROOT/data/disasterwatch.db" ]; then
    echo "Active SQLite database detected at data/disasterwatch.db" >> "$REPORT_FILE"
    echo "Database size: $(ls -lh "$PROJECT_ROOT/data/disasterwatch.db" | awk '{print $5}')" >> "$REPORT_FILE"
else
    echo "No local database found; standard external API mode active." >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

echo "==========================================================" >> "$REPORT_FILE"
echo " [SUCCESS] Analysis complete! Report saved via >> redirection." >> "$REPORT_FILE"
echo " Report file: $REPORT_FILE"
echo "==========================================================" >> "$REPORT_FILE"

# 5. Permissions: Restrict report permissions using chmod (Read & Write for Owner only)
chmod 644 "$REPORT_FILE"

# Display the generated report to stdout using cat
cat "$REPORT_FILE"
