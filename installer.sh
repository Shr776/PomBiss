#!/bin/sh
#
# ============================================================
#   PomBiss Plugin Installer v2.4
# ============================================================
#
#   Sports Feed Viewer for Enigma2
#
#   Supported Images:
#     - OpenBlackHole 5 / 6
#     - OpenATV 7.6 / 8.0
#     - OpenPLi 8.3 / 9.2
#     - Egami 11.2
#
#   GitHub: https://github.com/Shr776/PomBiss
# ============================================================

# --- Settings ---
PLUGIN_NAME="PomBiss"
PLUGIN_VERSION="2.4"
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"
GITHUB_RAW="https://raw.githubusercontent.com/Shr776/PomBiss/main"
TEMP_DIR="/tmp/pombiss_install"
LOG_FILE="/tmp/pombiss_install.log"

# --- Header ---
echo "=========================================="
echo "  PomBiss Plugin Installer v${PLUGIN_VERSION}"
echo "=========================================="
echo ""
echo " Supported Images:"
echo "   - OpenBlackHole 5"
echo "   - OpenBlackHole 6"
echo "   - OpenATV 7.6"
echo "   - OpenATV 8.0"
echo "   - OpenPLi 8.3"
echo "   - OpenPLi 9.2"
echo "   - Egami 11.2"
echo ""
echo " Installing to: $PLUGIN_DIR"
echo " Log file: $LOG_FILE"
echo ""

# --- Check wget ---
if ! which wget >/dev/null 2>&1; then
    echo "[ERROR] wget not found!"
    echo "Please install wget first:"
    echo "  opkg update && opkg install wget"
    exit 1
fi

# --- Prepare temp dir ---
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
mkdir -p "$TEMP_DIR/files"
mkdir -p "$TEMP_DIR/files/picon"

# --- Download function ---
download_file() {
    local url="$1"
    local dest="$2"
    echo "  -> Downloading: $(basename $dest)"
    wget -q --no-check-certificate "$url" -O "$dest"
    if [ ! -f "$dest" ]; then
        echo "    [ERROR] Failed to download $url"
        return 1
    fi
    return 0
}

# --- Files list ---
FILES="
__init__.py
plugin.py
signalfinder.py
signalfinder_pli_py2.py
signalfinder_atv.py
signalfinder_obh.py
updater.py
registration.py
version.txt
"

# --- Download files ---
echo ">>> Downloading plugin files..."
FAILED=0

for file in $FILES; do
    if ! download_file "$GITHUB_RAW/$file" "$TEMP_DIR/files/$file"; then
        FAILED=$((FAILED + 1))
    fi
done

# --- Download picon ---
echo ">>> Downloading picon files..."
if ! download_file "$GITHUB_RAW/picon/PomBiss_logo.png" "$TEMP_DIR/files/picon/PomBiss_logo.png"; then
    FAILED=$((FAILED + 1))
fi

if [ "$FAILED" -gt 0 ]; then
    echo ""
    echo "[WARNING] $FAILED file(s) failed to download"
    echo "Continuing anyway..."
fi

# --- Install ---
echo ""
echo ">>> Installing plugin files..."

if [ ! -d "$PLUGIN_DIR" ]; then
    mkdir -p "$PLUGIN_DIR"
fi

for file in $(ls "$TEMP_DIR/files/" | grep -v "picon"); do
    cp -f "$TEMP_DIR/files/$file" "$PLUGIN_DIR/$file" 2>/dev/null
done

if [ ! -d "$PLUGIN_DIR/picon" ]; then
    mkdir -p "$PLUGIN_DIR/picon"
fi
cp -f "$TEMP_DIR/files/picon/"* "$PLUGIN_DIR/picon/" 2>/dev/null

# --- Remove old pyc ---
echo ">>> Removing old .pyo / .pyc files..."
rm -f "$PLUGIN_DIR"/*.pyo 2>/dev/null
rm -f "$PLUGIN_DIR"/*.pyc 2>/dev/null

# --- Permissions ---
chmod 644 "$PLUGIN_DIR"/*.py 2>/dev/null
chmod 644 "$PLUGIN_DIR"/*.png 2>/dev/null
chmod 755 "$PLUGIN_DIR/picon" 2>/dev/null
chmod 644 "$PLUGIN_DIR/picon/"* 2>/dev/null

# --- Show version ---
NEW_VERSION=$(cat "$TEMP_DIR/files/version.txt" 2>/dev/null | head -n 1)
echo ""
echo "=========================================="
echo "  [OK] PomBiss installed successfully!"
echo "=========================================="
echo "  Version: $NEW_VERSION"
echo "  Path: $PLUGIN_DIR"
echo ""

# --- Telegram Channels ---
echo ""
echo "======================================================"
echo "                 JOIN US ON TELEGRAM"
echo "======================================================"
echo "  Main Channel:      @VUSOLO"
echo "                     https://t.me/VuSolo"
echo ""
echo "  Feeds Channel:     @PomFeed"
echo "                     https://t.me/PomFeed"
echo ""
echo "  Support Group:     @PomSat"
echo "                     https://t.me/PomSat"
echo ""
echo "  Developer:         @Shr776"
echo "                     https://t.me/Shr776"
echo "======================================================"
echo ""
echo ">>> Restarting Enigma2 in 5 seconds..."
sleep 1
echo "   4..."
sleep 1
echo "   3..."
sleep 1
echo "   2..."
sleep 1
echo "   1..."
sleep 1
echo "   [OK] Restarting now!"
echo ""

# --- Restart Flag ---
if [ -f /tmp/pombiss_from_plugin ]; then
    echo ">>> Restart flag created for plugin update"
    touch /tmp/pombiss_need_restart
fi

# --- Restart Enigma2 ---
if [ -f /tmp/pombiss_from_plugin ]; then
    :
else
    echo ">>> Restarting Enigma2..."
    init 4 >/dev/null 2>&1
    sleep 2
    init 3 >/dev/null 2>&1
fi

# --- Cleanup ---
rm -rf "$TEMP_DIR"

# ============================================================
# BIG ASCII TEXT FOOTER (Centered)
# ============================================================
echo ""
echo ""
echo ""
echo "            _      _                    __                 _ _ "
echo "           | |    (_)_ __  _   ___  __ / _| ___  _ __     / \\ |"
echo "           | |    | | '_ \\| | | \\ \\/ /| |_ / _ \\| '__|   / _ \\|"
echo "           | |___ | | | | | |_| |>  < |  _| (_) | |     / ___ \\|"
echo "           |_____||_|_| |_|\\__,_/_/\\_\\|_|  \\___/|_|    /_/   \\_\\"
echo ""
echo "                           ====================="
echo ""
echo "                 __     __ _   _ ____   ___  _     ___  "
echo "                 \\ \\   / /| | | / ___| / _ \\| |   / _ \\ "
echo "                  \\ \\ / / | | | \\___ \\| | | | |  | | | |"
echo "                   \\ V /  | |_| |___) | |_| | |__| |_| |"
echo "                    \\_/    \\___/|____/ \\___/|_____\\___/ "
echo ""
echo "                           ====================="
echo ""
echo ""
echo ""

exit 0
