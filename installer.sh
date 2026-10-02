#!/bin/sh
# ============================================================
# PomBiss Plugin Installer
# Sports Feed Viewer for Enigma2
# GitHub: https://github.com/Shr776/PomBiss
# ============================================================

VERSION="1.0"
PLUGIN_NAME="PomBiss"
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"
REPO_URL="https://github.com/Shr776/PomBiss/archive/refs/heads/main.zip"
TEMP_DIR="/tmp/pombiss_install"
ZIP_FILE="$TEMP_DIR/pombiss.zip"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "============================================================"
echo "     PomBiss Plugin Installer v$VERSION"
echo "     Sports Feed Viewer for Enigma2"
echo "============================================================"
echo ""

# Check if running as root
if [ "$(id -u)" != "0" ]; then
    echo "❌ This script must be run as root!"
    exit 1
fi

# Check if wget is installed
if ! command -v wget > /dev/null 2>&1; then
    echo "❌ wget is not installed!"
    echo "   Install it with: opkg install wget"
    exit 1
fi

# Check if unzip is installed
if ! command -v unzip > /dev/null 2>&1; then
    echo "❌ unzip is not installed!"
    echo "   Install it with: opkg install unzip"
    exit 1
fi

# ============================================================
# Step 1: Remove old version
# ============================================================
echo "▶ Step 1/5: Removing old version..."
if [ -d "$PLUGIN_PATH" ]; then
    rm -rf "$PLUGIN_PATH"
    echo "  ✓ Old version removed"
else
    echo "  ℹ No old version found"
fi

# ============================================================
# Step 2: Create temp directory
# ============================================================
echo ""
echo "▶ Step 2/5: Preparing temp directory..."
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
echo "  ✓ Temp directory ready"

# ============================================================
# Step 3: Download plugin
# ============================================================
echo ""
echo "▶ Step 3/5: Downloading plugin from GitHub..."
echo "  URL: $REPO_URL"

if ! wget -q --no-check-certificate "$REPO_URL" -O "$ZIP_FILE"; then
    echo "  ❌ Download failed!"
    echo "  Check your internet connection."
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Check file size
FILESIZE=$(stat -c%s "$ZIP_FILE" 2>/dev/null || echo "0")
if [ "$FILESIZE" -lt 1000 ]; then
    echo "  ❌ Downloaded file is too small ($FILESIZE bytes)"
    echo "  Maybe the repo is empty or URL is wrong."
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "  ✓ Downloaded ($FILESIZE bytes)"

# ============================================================
# Step 4: Extract and install
# ============================================================
echo ""
echo "▶ Step 4/5: Extracting and installing..."
cd "$TEMP_DIR" || exit 1

if ! unzip -q "$ZIP_FILE"; then
    echo "  ❌ Extraction failed!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Find the extracted directory (usually PomBiss-main)
EXTRACTED_DIR=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "PomBiss-*" | head -1)

if [ -z "$EXTRACTED_DIR" ]; then
    echo "  ❌ Extracted directory not found!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "  ✓ Extracted to: $EXTRACTED_DIR"

# Create plugin directory
mkdir -p "$PLUGIN_PATH"

# Copy files
cp -rf "$EXTRACTED_DIR"/* "$PLUGIN_PATH"/ 2>/dev/null

# Remove installer.sh and README.md from plugin folder (not needed)
rm -f "$PLUGIN_PATH/installer.sh"
rm -f "$PLUGIN_PATH/README.md"

# Remove any .pyc files (they will be regenerated)
find "$PLUGIN_PATH" -name "*.pyc" -delete 2>/dev/null

# Remove .pyo files
find "$PLUGIN_PATH" -name "*.pyo" -delete 2>/dev/null

echo "  ✓ Files installed to: $PLUGIN_PATH"

# ============================================================
# Step 5: Set permissions
# ============================================================
echo ""
echo "▶ Step 5/5: Setting permissions..."
chmod -R 755 "$PLUGIN_PATH"
echo "  ✓ Permissions set"

# ============================================================
# Cleanup
# ============================================================
rm -rf "$TEMP_DIR"
echo "  ✓ Cleanup done"

# ============================================================
# Show installed files
# ============================================================
echo ""
echo "============================================================"
echo "  ✅ INSTALLATION COMPLETE!"
echo "============================================================"
echo ""
echo "Installed files:"
ls -la "$PLUGIN_PATH" | grep -v "^total"
echo ""
echo "Plugin location: $PLUGIN_PATH"
echo ""

# ============================================================
# Restart Enigma2
# ============================================================
echo "============================================================"
echo "  🔄 Restarting Enigma2 in 3 seconds..."
echo "============================================================"
echo ""
echo "  (Press Ctrl+C to cancel)"
echo ""

sleep 3

echo "Restarting..."
init 4
sleep 2
init 3

echo ""
echo "✅ Enigma2 restarted!"
echo ""
echo "Look for 'PomBiss' in your plugin menu."
echo ""
