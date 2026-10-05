#!/bin/sh
# ============================================================
# PomBiss Plugin Installer v1.2
# Sports Feed Viewer for Enigma2
# GitHub: https://github.com/Shr776/PomBiss
# ============================================================

VERSION="1.2"
PLUGIN_NAME="PomBiss"
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"
REPO_URL="https://github.com/Shr776/PomBiss/archive/refs/heads/main.zip"
TEMP_DIR="/tmp/pombiss_install"
ZIP_FILE="$TEMP_DIR/pombiss.zip"
BACKUP_DIR="/tmp/pombiss_backup"
LOG_FILE="/tmp/pombiss_install.log"
RESTART_FLAG="/tmp/pombiss_need_restart"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================
# log function
# ============================================================
log() {
    echo "$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE" 2>/dev/null
}

# ============================================================
# Progress banner
# ============================================================
progress() {
    echo ""
    echo "============================================================"
    echo "  $1"
    echo "============================================================"
    echo ""
}

# ============================================================
# Start
# ============================================================
echo "" > "$LOG_FILE"
log "============================================================"
log "     PomBiss Plugin Installer v$VERSION"
log "     Sports Feed Viewer for Enigma2"
log "============================================================"
echo ""

# پاک کردن flag قبلی
rm -f "$RESTART_FLAG"

# Check root
if [ "$(id -u)" != "0" ]; then
    log "ERROR: This script must be run as root!"
    echo "ERROR: Not root!"
    exit 1
fi

# Check wget
if ! command -v wget > /dev/null 2>&1; then
    log "ERROR: wget is not installed!"
    echo "ERROR: wget not installed!"
    exit 1
fi

# Check unzip
if ! command -v unzip > /dev/null 2>&1; then
    log "ERROR: unzip is not installed!"
    echo "ERROR: unzip not installed!"
    exit 1
fi

# ============================================================
# Step 1: Download plugin
# ============================================================
progress "[1/6] Downloading new version from GitHub..."
log "Step 1/6: Downloading..."
log "  URL: $REPO_URL"

rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

echo "Downloading... ($REPO_URL)"
if ! wget -q --no-check-certificate "$REPO_URL" -O "$ZIP_FILE"; then
    log "  Download failed!"
    echo ""
    echo "DOWNLOAD FAILED!"
    echo "Check your internet connection."
    echo "Your current plugin is UNTOUCHED."
    rm -rf "$TEMP_DIR"
    exit 1
fi

FILESIZE=$(stat -c%s "$ZIP_FILE" 2>/dev/null || echo "0")
if [ "$FILESIZE" -lt 1000 ]; then
    log "  Downloaded file too small ($FILESIZE bytes)"
    echo "FILE TOO SMALL ($FILESIZE bytes)"
    rm -rf "$TEMP_DIR"
    exit 1
fi

log "  Downloaded ($FILESIZE bytes)"
echo ""
echo "Downloaded: $FILESIZE bytes"
echo "Progress: [##########] 20%"

# ============================================================
# Step 2: Extract
# ============================================================
progress "[2/6] Extracting archive..."
cd "$TEMP_DIR" || exit 1

echo "Extracting..."
if ! unzip -q "$ZIP_FILE"; then
    log "  Extraction failed!"
    echo "EXTRACTION FAILED!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

EXTRACTED_DIR=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "PomBiss-*" | head -1)
if [ -z "$EXTRACTED_DIR" ]; then
    log "  Extracted dir not found!"
    echo "EXTRACT DIR NOT FOUND!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

if [ ! -f "$EXTRACTED_DIR/plugin.py" ]; then
    log "  plugin.py not found!"
    echo "plugin.py NOT FOUND in archive!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

log "  Extracted to: $EXTRACTED_DIR"
echo "Extracted OK"
echo "Progress: [####################] 40%"

# ============================================================
# Step 3: Backup
# ============================================================
progress "[3/6] Backing up current plugin..."
rm -rf "$BACKUP_DIR"
if [ -d "$PLUGIN_PATH" ]; then
    cp -rf "$PLUGIN_PATH" "$BACKUP_DIR"
    log "  Backup created"
    echo "Backup created: $BACKUP_DIR"
else
    log "  No existing plugin"
    echo "No existing plugin to backup"
fi
echo "Progress: [##########################] 55%"

# ============================================================
# Step 4: Install new files
# ============================================================
progress "[4/6] Installing new files..."
if [ -d "$PLUGIN_PATH" ]; then
    rm -rf "$PLUGIN_PATH"
    log "  Old version removed"
    echo "Old version removed"
fi

mkdir -p "$PLUGIN_PATH"

if ! cp -rf "$EXTRACTED_DIR"/* "$PLUGIN_PATH"/ 2>/dev/null; then
    log "  Copy failed! Restoring backup..."
    echo "COPY FAILED! Restoring backup..."
    rm -rf "$PLUGIN_PATH"
    if [ -d "$BACKUP_DIR" ]; then
        cp -rf "$BACKUP_DIR" "$PLUGIN_PATH"
        echo "Restored old version"
    fi
    rm -rf "$TEMP_DIR"
    exit 1
fi

# پاک کردن فایل‌های اضافی
rm -f "$PLUGIN_PATH/installer.sh"
rm -f "$PLUGIN_PATH/README.md"
rm -f "$PLUGIN_PATH/README"
rm -f "$PLUGIN_PATH/.gitignore"
find "$PLUGIN_PATH" -name "*.pyc" -delete 2>/dev/null
find "$PLUGIN_PATH" -name "*.pyo" -delete 2>/dev/null

echo "New files installed"
echo "Progress: [##################################] 75%"

# ============================================================
# Step 5: Write version.txt
# ============================================================
progress "[5/6] Writing version info..."
echo "1.1" > "$PLUGIN_PATH/version.txt"
chmod -R 755 "$PLUGIN_PATH"
log "  version.txt written (1.1)"
log "  Permissions set (755)"
echo "Version 1.1 written"
echo "Permissions set (755)"
echo "Progress: [##########################################] 90%"

# ============================================================
# Step 6: Cleanup
# ============================================================
progress "[6/6] Finalizing..."
rm -rf "$TEMP_DIR"
rm -rf "$BACKUP_DIR"
log "  Cleanup done"
echo "Cleanup done"
echo "Progress: [##############################################] 100%"

# ============================================================
# SUCCESS!
# ============================================================
echo ""
echo "============================================================"
echo "  INSTALLATION COMPLETE!"
echo "============================================================"
echo ""
echo "Installed files:"
ls -la "$PLUGIN_PATH" 2>/dev/null | grep -v "^total"
echo ""
echo "Location: $PLUGIN_PATH"
echo ""

# ساخت flag برای ریستارت توسط پلاگین
touch "$RESTART_FLAG"
log "  Restart flag created: $RESTART_FLAG"

echo "============================================================"
echo "  Enigma2 will restart in a moment..."
echo "============================================================"
echo ""
echo "  Update successful!"
echo "  Returning to plugin for restart..."
echo ""

sleep 3

exit 0
