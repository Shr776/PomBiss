#!/bin/sh
# ============================================================
# PomBiss Plugin Installer v1.1
# Sports Feed Viewer for Enigma2
# GitHub: https://github.com/Shr776/PomBiss
# ============================================================

VERSION="1.1"
PLUGIN_NAME="PomBiss"
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"
REPO_URL="https://github.com/Shr776/PomBiss/archive/refs/heads/main.zip"
TEMP_DIR="/tmp/pombiss_install"
ZIP_FILE="$TEMP_DIR/pombiss.zip"
BACKUP_DIR="/tmp/pombiss_backup"
LOG_FILE="/tmp/pombiss_install.log"

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
# Start
# ============================================================
echo "" > "$LOG_FILE"
log "============================================================"
log "     PomBiss Plugin Installer v$VERSION"
log "     Sports Feed Viewer for Enigma2"
log "============================================================"
echo ""

# Check root
if [ "$(id -u)" != "0" ]; then
    log "❌ This script must be run as root!"
    exit 1
fi

# Check wget
if ! command -v wget > /dev/null 2>&1; then
    log "❌ wget is not installed!"
    log "   Install it with: opkg install wget"
    exit 1
fi

# Check unzip
if ! command -v unzip > /dev/null 2>&1; then
    log "❌ unzip is not installed!"
    log "   Install it with: opkg install unzip"
    exit 1
fi

# ============================================================
# Step 1: Download plugin FIRST (before touching anything)
# ============================================================
log "▶ Step 1/6: Downloading new version from GitHub..."
log "  URL: $REPO_URL"

rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

if ! wget -q --no-check-certificate "$REPO_URL" -O "$ZIP_FILE"; then
    log "  ❌ Download failed!"
    log "  Check your internet connection."
    log "  Your current plugin is UNTOUCHED. Nothing changed."
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Check file size
FILESIZE=$(stat -c%s "$ZIP_FILE" 2>/dev/null || echo "0")
if [ "$FILESIZE" -lt 1000 ]; then
    log "  ❌ Downloaded file is too small ($FILESIZE bytes)"
    log "  Maybe the repo is empty or URL is wrong."
    log "  Your current plugin is UNTOUCHED. Nothing changed."
    rm -rf "$TEMP_DIR"
    exit 1
fi

log "  ✓ Downloaded ($FILESIZE bytes)"

# ============================================================
# Step 2: Extract and validate
# ============================================================
log ""
log "▶ Step 2/6: Extracting..."
cd "$TEMP_DIR" || exit 1

if ! unzip -q "$ZIP_FILE"; then
    log "  ❌ Extraction failed!"
    log "  Your current plugin is UNTOUCHED. Nothing changed."
    rm -rf "$TEMP_DIR"
    exit 1
fi

EXTRACTED_DIR=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "PomBiss-*" | head -1)

if [ -z "$EXTRACTED_DIR" ]; then
    log "  ❌ Extracted directory not found!"
    log "  Your current plugin is UNTOUCHED. Nothing changed."
    rm -rf "$TEMP_DIR"
    exit 1
fi

log "  ✓ Extracted to: $EXTRACTED_DIR"

# Validate that essential files exist
if [ ! -f "$EXTRACTED_DIR/plugin.py" ]; then
    log "  ❌ plugin.py not found in downloaded archive!"
    log "  Your current plugin is UNTOUCHED. Nothing changed."
    rm -rf "$TEMP_DIR"
    exit 1
fi

log "  ✓ Validation passed"

# ============================================================
# Step 3: Stop Enigma2 BEFORE replacing files
# ============================================================
log ""
log "▶ Step 3/6: Stopping Enigma2..."
init 4
sleep 2
log "  ✓ Enigma2 stopped"

# ============================================================
# Step 4: Backup current plugin (safety net)
# ============================================================
log ""
log "▶ Step 4/6: Backing up current plugin..."

rm -rf "$BACKUP_DIR"
if [ -d "$PLUGIN_PATH" ]; then
    cp -rf "$PLUGIN_PATH" "$BACKUP_DIR"
    log "  ✓ Backup created: $BACKUP_DIR"
else
    log "  ℹ No existing plugin to backup"
fi

# ============================================================
# Step 5: Install new plugin
# ============================================================
log ""
log "▶ Step 5/6: Installing new version..."

# Remove old version
if [ -d "$PLUGIN_PATH" ]; then
    rm -rf "$PLUGIN_PATH"
    log "  ✓ Old version removed"
fi

# Create fresh plugin directory
mkdir -p "$PLUGIN_PATH"

# Copy new files
if ! cp -rf "$EXTRACTED_DIR"/* "$PLUGIN_PATH"/ 2>/dev/null; then
    log "  ❌ Copy failed! Restoring from backup..."
    rm -rf "$PLUGIN_PATH"
    if [ -d "$BACKUP_DIR" ]; then
        cp -rf "$BACKUP_DIR" "$PLUGIN_PATH"
        log "  ✓ Restored old version from backup"
    fi
    log "  Restarting Enigma2..."
    init 3
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Clean unneeded files
rm -f "$PLUGIN_PATH/installer.sh"
rm -f "$PLUGIN_PATH/README.md"
rm -f "$PLUGIN_PATH/README"
rm -f "$PLUGIN_PATH/.gitignore"

# Remove .pyc and .pyo (they will be regenerated)
find "$PLUGIN_PATH" -name "*.pyc" -delete 2>/dev/null
find "$PLUGIN_PATH" -name "*.pyo" -delete 2>/dev/null

# Write local version.txt
echo "1.1" > "$PLUGIN_PATH/version.txt"
log "  ✓ Local version.txt written (1.1)"

# Set permissions
chmod -R 755 "$PLUGIN_PATH"
log "  ✓ Permissions set (755)"

log "  ✓ Files installed to: $PLUGIN_PATH"

# ============================================================
# Step 6: Cleanup and restart
# ============================================================
log ""
log "▶ Step 6/6: Finalizing..."
rm -rf "$TEMP_DIR"
rm -rf "$BACKUP_DIR"
log "  ✓ Cleanup done"

log ""
log "============================================================"
log "  ✅ INSTALLATION COMPLETE!"
log "============================================================"
log ""
log "Installed files:"
ls -la "$PLUGIN_PATH" | grep -v "^total" | while read line; do log "$line"; done
log ""
log "Plugin location: $PLUGIN_PATH"
log ""

# ============================================================
# Restart Enigma2
# ============================================================
log "============================================================"
log "  🔄 Restarting Enigma2..."
log "============================================================"
echo ""

sleep 2

log "Restarting..."
init 3

log ""
log "✅ Enigma2 restarted!"
log ""
log "Look for 'PomBiss' in your plugin menu."
log ""
exit 0
