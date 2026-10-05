#!/bin/sh
# ============================================================
# PomBiss Plugin Installer v1.2
# Sports Feed Viewer for Enigma2
# GitHub: https://github.com/Shr776/PomBiss
# ============================================================

VERSION="1.2"
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"
REPO_URL="https://github.com/Shr776/PomBiss/archive/refs/heads/main.zip"
TEMP_DIR="/tmp/pombiss_install"
ZIP_FILE="$TEMP_DIR/pombiss.zip"
BACKUP_DIR="/tmp/pombiss_backup"
LOG_FILE="/tmp/pombiss_install.log"
RESTART_FLAG="/tmp/pombiss_need_restart"

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
    log "❌ ERROR: Not root!"
    echo "❌ ERROR: This script must be run as root!"
    exit 1
fi
echo "✅ Root check: OK"

# Check wget
if ! command -v wget > /dev/null 2>&1; then
    log "❌ wget not installed!"
    echo "❌ ERROR: wget not installed!"
    exit 1
fi
echo "✅ wget: OK"

# Check unzip
if ! command -v unzip > /dev/null 2>&1; then
    log "❌ unzip not installed!"
    echo "❌ ERROR: unzip not installed!"
    exit 1
fi
echo "✅ unzip: OK"
echo ""

# ============================================================
# Step 1: Download
# ============================================================
echo "============================================================"
echo "  [1/6] Downloading from GitHub..."
echo "============================================================"
log "Step 1/6: Downloading..."
log "  URL: $REPO_URL"

rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

echo "📥 URL: $REPO_URL"
echo ""

# ⭐ progress نمایش داده می‌شه (dot:giga)
if ! wget --no-check-certificate --progress=dot:giga -O "$ZIP_FILE" "$REPO_URL"; then
    log "  ❌ Download failed!"
    echo ""
    echo "❌ DOWNLOAD FAILED!"
    echo "   Your current plugin is UNTOUCHED."
    rm -rf "$TEMP_DIR"
    exit 1
fi

FILESIZE=$(stat -c%s "$ZIP_FILE" 2>/dev/null || echo "0")
if [ "$FILESIZE" -lt 1000 ]; then
    log "  ❌ File too small ($FILESIZE bytes)"
    echo "❌ FILE TOO SMALL"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo ""
echo "✅ Downloaded: $FILESIZE bytes"
echo "📊 Progress: [██████████░░░░░░░░░░] 30%"
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
    log "  ❌ Extraction failed!"
    echo "❌ EXTRACTION FAILED!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

EXTRACTED_DIR=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "PomBiss-*" | head -1)
if [ -z "$EXTRACTED_DIR" ]; then
    log "  ❌ Extracted dir not found!"
    echo "❌ EXTRACT DIR NOT FOUND!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

if [ ! -f "$EXTRACTED_DIR/plugin.py" ]; then
    log "  ❌ plugin.py not found!"
    echo "❌ plugin.py NOT FOUND!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "✅ Extracted to: $EXTRACTED_DIR"
echo "📊 Progress: [████████████████░░░░] 45%"
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
    log "  ✓ Backup created"
    echo "✅ Backup created: $BACKUP_DIR"
else
    echo "ℹ No existing plugin to backup"
fi
echo "📊 Progress: [██████████████████░░] 55%"
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
    echo "✅ Old version removed"
fi

mkdir -p "$PLUGIN_PATH"

if ! cp -rf "$EXTRACTED_DIR"/* "$PLUGIN_PATH"/ 2>/dev/null; then
    log "  ❌ Copy failed! Restoring..."
    echo "❌ COPY FAILED! Restoring backup..."
    rm -rf "$PLUGIN_PATH"
    if [ -d "$BACKUP_DIR" ]; then
        cp -rf "$BACKUP_DIR" "$PLUGIN_PATH"
        echo "✅ Restored old version"
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

echo "✅ New files installed"
echo "📊 Progress: [██████████████████████] 75%"
echo ""
sleep 1

# ============================================================
# Step 5: version + permissions
# ============================================================
echo "============================================================"
echo "  [5/6] Setting up..."
echo "============================================================"
log "Step 5/6: Setup..."

echo "1.1" > "$PLUGIN_PATH/version.txt"
chmod -R 755 "$PLUGIN_PATH"

echo "✅ Version 1.1 written"
echo "✅ Permissions set (755)"
echo "📊 Progress: [████████████████████████] 90%"
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

echo "✅ Cleanup done"
echo "📊 Progress: [██████████████████████████] 100%"
echo ""

# ============================================================
# SUCCESS!
# ============================================================
echo "============================================================"
echo "  ✅ INSTALLATION COMPLETE!"
echo "============================================================"
echo ""
echo "📦 Installed files:"
ls -la "$PLUGIN_PATH" 2>/dev/null | grep -v "^total"
echo ""
echo "📍 Location: $PLUGIN_PATH"
echo ""

# ⭐ ساخت flag برای ریستارت توسط پلاگین
touch "$RESTART_FLAG"
log "Restart flag created: $RESTART_FLAG"

echo "============================================================"
echo "  ✅ Update successful!"
echo "  🔄 Enigma2 will restart automatically..."
echo "============================================================"
echo ""

sleep 3

exit 0
