#!/bin/sh
# ============================================================
# PomBiss Plugin Installer v1.6
# Sports Feed Viewer for Enigma2
# GitHub: https://github.com/Shr776/PomBiss
# ============================================================

VERSION="1.6"
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"
REPO_URL="https://github.com/Shr776/PomBiss/archive/refs/heads/main.zip"
VERSION_URL="https://raw.githubusercontent.com/Shr776/PomBiss/main/version.txt"
TEMP_DIR="/tmp/pombiss_install"
ZIP_FILE="$TEMP_DIR/pombiss.zip"
BACKUP_DIR="/tmp/pombiss_backup"
LOG_FILE="/tmp/pombiss_install.log"
RESTART_FLAG="/tmp/pombiss_need_restart"
FROM_PLUGIN_FLAG="/tmp/pombiss_from_plugin"

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

echo "============================================================"
echo "         PomBiss Plugin Installer v$VERSION"
echo "         Sports Feed Viewer for Enigma2"
echo "============================================================"
echo ""
sleep 1

# پاک کردن flag قبلی
rm -f "$RESTART_FLAG"

# Check root
if [ "$(id -u)" != "0" ]; then
    log "ERROR: Not root!"
    echo "ERROR: This script must be run as root!"
    exit 1
fi
echo "OK: Root check"

# Check wget
if ! command -v wget > /dev/null 2>&1; then
    log "ERROR: wget not installed!"
    echo "ERROR: wget not installed!"
    exit 1
fi
echo "OK: wget check"

# Check unzip
if ! command -v unzip > /dev/null 2>&1; then
    log "ERROR: unzip not installed!"
    echo "ERROR: unzip not installed!"
    exit 1
fi
echo "OK: unzip check"
echo ""

# ============================================================
# Step 0: Get new version from GitHub
# ============================================================
echo "============================================================"
echo "  [0/6] Reading version from GitHub..."
echo "============================================================"

NEW_VERSION=$(wget -q --no-check-certificate -O - "$VERSION_URL" 2>/dev/null | tr -d '[:space:]')

if [ -z "$NEW_VERSION" ]; then
    echo "WARNING: Cannot read version from GitHub, using $VERSION"
    NEW_VERSION="$VERSION"
else
    echo "OK: Latest version from GitHub = $NEW_VERSION"
fi
log "Step 0/6: New version = $NEW_VERSION"
echo ""
sleep 1

# ============================================================
# Step 1: Download
# ============================================================
echo "============================================================"
echo "  [1/6] Downloading from GitHub..."
echo "============================================================"
log "Step 1/6: Downloading..."

rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

echo "URL: $REPO_URL"
echo ""

if ! wget --no-check-certificate --progress=dot:giga -O "$ZIP_FILE" "$REPO_URL"; then
    log "ERROR: Download failed"
    echo ""
    echo "ERROR: DOWNLOAD FAILED!"
    echo "Your current plugin is UNTOUCHED."
    rm -rf "$TEMP_DIR"
    exit 1
fi

FILESIZE=$(stat -c%s "$ZIP_FILE" 2>/dev/null || echo "0")
if [ "$FILESIZE" -lt 1000 ]; then
    log "ERROR: File too small ($FILESIZE bytes)"
    echo "ERROR: FILE TOO SMALL"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo ""
echo "OK: Downloaded $FILESIZE bytes"
echo "Progress: [##########..........] 30%"
echo ""
sleep 1

# ============================================================
# Step 2: Extract
# ============================================================
echo "============================================================"
echo "  [2/6] Extracting archive..."
echo "============================================================"
log "Step 2/6: Extracting..."
cd "$TEMP_DIR" || exit 1

if ! unzip -q "$ZIP_FILE"; then
    log "ERROR: Extraction failed"
    echo "ERROR: EXTRACTION FAILED!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

EXTRACTED_DIR=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "PomBiss-*" | head -1)
if [ -z "$EXTRACTED_DIR" ]; then
    log "ERROR: Extracted dir not found"
    echo "ERROR: EXTRACT DIR NOT FOUND!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

if [ ! -f "$EXTRACTED_DIR/plugin.py" ]; then
    log "ERROR: plugin.py not found"
    echo "ERROR: plugin.py NOT FOUND!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "OK: Extracted to: $EXTRACTED_DIR"
echo "Progress: [################....] 45%"
echo ""
sleep 1

# ============================================================
# Step 3: Backup
# ============================================================
echo "============================================================"
echo "  [3/6] Backing up current plugin..."
echo "============================================================"
log "Step 3/6: Backup..."
rm -rf "$BACKUP_DIR"

if [ -d "$PLUGIN_PATH" ]; then
    cp -rf "$PLUGIN_PATH" "$BACKUP_DIR"
    log "Backup created"
    echo "OK: Backup created"
else
    echo "INFO: No existing plugin to backup"
fi
echo "Progress: [##################..] 55%"
echo ""
sleep 1

# ============================================================
# Step 4: Install
# ============================================================
echo "============================================================"
echo "  [4/6] Installing new files..."
echo "============================================================"
log "Step 4/6: Installing..."

if [ -d "$PLUGIN_PATH" ]; then
    rm -rf "$PLUGIN_PATH"
    echo "OK: Old version removed"
fi

mkdir -p "$PLUGIN_PATH"

if ! cp -rf "$EXTRACTED_DIR"/* "$PLUGIN_PATH"/ 2>/dev/null; then
    log "ERROR: Copy failed - restoring backup"
    echo "ERROR: COPY FAILED! Restoring backup..."
    rm -rf "$PLUGIN_PATH"
    if [ -d "$BACKUP_DIR" ]; then
        cp -rf "$BACKUP_DIR" "$PLUGIN_PATH"
        echo "OK: Restored old version"
    fi
    rm -rf "$TEMP_DIR"
    exit 1
fi

rm -f "$PLUGIN_PATH/installer.sh"
rm -f "$PLUGIN_PATH/README.md"
rm -f "$PLUGIN_PATH/README"
rm -f "$PLUGIN_PATH/.gitignore"
find "$PLUGIN_PATH" -name "*.pyc" -delete 2>/dev/null
find "$PLUGIN_PATH" -name "*.pyo" -delete 2>/dev/null

echo "OK: New files installed"
echo "Progress: [######################] 75%"
echo ""
sleep 1

# ============================================================
# Step 5: Update versions
# ============================================================
echo "============================================================"
echo "  [5/6] Updating version info..."
echo "============================================================"
log "Step 5/6: Update version to $NEW_VERSION"

# 1) نسخه محلی
echo "$NEW_VERSION" > "$PLUGIN_PATH/version.txt"
echo "OK: version.txt = $NEW_VERSION"

# 2) نسخه داخل updater.py
if [ -f "$PLUGIN_PATH/updater.py" ]; then
    sed -i "s/^PLUGIN_VERSION = .*/PLUGIN_VERSION = \"$NEW_VERSION\"/" "$PLUGIN_PATH/updater.py"
    echo "OK: PLUGIN_VERSION = $NEW_VERSION (in updater.py)"
    log "  PLUGIN_VERSION updated to $NEW_VERSION"
else
    echo "WARNING: updater.py not found!"
fi

echo ""
echo "Verifying:"
echo "  Local version.txt:  $(cat $PLUGIN_PATH/version.txt 2>/dev/null)"
echo "  updater.py version: $(grep '^PLUGIN_VERSION' $PLUGIN_PATH/updater.py 2>/dev/null)"
echo ""

chmod -R 755 "$PLUGIN_PATH"
echo "OK: Permissions set (755)"
echo "Progress: [########################] 90%"
echo ""
sleep 1

# ============================================================
# Step 6: Cleanup
# ============================================================
echo "============================================================"
echo "  [6/6] Finalizing..."
echo "============================================================"
log "Step 6/6: Finalize..."

rm -rf "$TEMP_DIR"
rm -rf "$BACKUP_DIR"

echo "OK: Cleanup done"
echo "Progress: [##########################] 100%"
echo ""

# ============================================================
# SUCCESS!
# ============================================================
echo "============================================================"
echo "  INSTALLATION COMPLETE!"
echo "============================================================"
echo ""
echo "Installed files:"
ls -la "$PLUGIN_PATH" 2>/dev/null | grep -v "^total"
echo ""
echo "Location: $PLUGIN_PATH"
echo ""
echo "Version installed: $NEW_VERSION"
echo ""

# ============================================================
# Restart decision: from plugin or from telnet?
# ============================================================
if [ -f "$FROM_PLUGIN_FLAG" ]; then
    # اجرا از داخل پلاگین → فقط flag بساز
    rm -f "$FROM_PLUGIN_FLAG"
    touch "$RESTART_FLAG"
    log "Restart flag created (from plugin)"

    echo "============================================================"
    echo "  Update successful!"
    echo "  Returning to plugin for restart..."
    echo "============================================================"
    echo ""

    sleep 2
    exit 0
else
    # اجرا از تلنت → خودش ریستارت کن
    echo "============================================================"
    echo "  Update successful!"
    echo "  Restarting Enigma2..."
    echo "============================================================"
    echo ""

    sleep 3

    init 4
    sleep 3
    init 3

    exit 0
fi
