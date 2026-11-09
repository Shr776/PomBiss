#!/bin/sh
#
# ============================================================
#   PomBiss Plugin Installer v2.8
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
#
#   This installer reads the file list of the GitHub repository
#   and installs EVERYTHING in it (root files, picon/, fonts/ ...)
#   with the same folder structure. New files added to GitHub
#   later are installed automatically.
# ============================================================

# --- Settings ---
PLUGIN_NAME="PomBiss"
PLUGIN_VERSION="2.8"
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"
GITHUB_USER="Shr776"
GITHUB_REPO="PomBiss"
GITHUB_BRANCH="main"
GITHUB_RAW="https://raw.githubusercontent.com/${GITHUB_USER}/${GITHUB_REPO}/${GITHUB_BRANCH}"
GITHUB_API="https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/git/trees/${GITHUB_BRANCH}?recursive=1"
TEMP_DIR="/tmp/pombiss_install"
LOG_FILE="/tmp/pombiss_install.log"

# Files that must exist, otherwise the installation is aborted
CRITICAL_FILES="__init__.py plugin.py version.txt"

: > "$LOG_FILE"

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
mkdir -p "$TEMP_DIR/files"

# ============================================================
# Build the list of files to install
# ============================================================
echo ">>> Reading file list from GitHub..."

LIST_RAW="$TEMP_DIR/list_raw.txt"
LIST="$TEMP_DIR/list.txt"
: > "$LIST_RAW"

# 1) Ask the GitHub API for the full tree of the repository
if wget -q --no-check-certificate "$GITHUB_API" -O "$TEMP_DIR/tree.json" 2>>"$LOG_FILE" && [ -s "$TEMP_DIR/tree.json" ]; then
    tr ',{}' '\n\n\n' < "$TEMP_DIR/tree.json" | awk '
        /"path"[ ]*:/ { p=$0; sub(/^.*"path"[ ]*:[ ]*"/, "", p); sub(/".*$/, "", p) }
        /"type"[ ]*:/ { if ($0 ~ /"blob"/ && p != "") print p; p="" }
    ' > "$LIST_RAW"
fi

# 2) Fallback: built-in list (used when the API is blocked or rate-limited)
if [ ! -s "$LIST_RAW" ]; then
    echo "    [WARNING] Could not read GitHub file list, using built-in list"
    cat > "$LIST_RAW" <<'FALLBACK_EOF'
__init__.py
plugin.py
webserver.py
signalfinder.py
signalfinder_pli_py2.py
signalfinder_atv.py
signalfinder_obh.py
updater.py
registration.py
version.txt
PomBiss_logo.png
bg_panel.png
picon/PomBiss_logo.png
picon/bar_bg.png
picon/bar_green.png
picon/bar_red.png
picon/bar_yellow.png
picon/bg_panel.png
fonts/ChakraPetch-Bold.ttf
FALLBACK_EOF
fi

# Remove repository-only files (not part of the plugin)
grep -v -E '(^|/)\.|^README\.md$|^installer\.sh$|^LICENSE' "$LIST_RAW" > "$LIST"

TOTAL=$(wc -l < "$LIST" | tr -d ' ')
echo "    Found $TOTAL files to install"
echo ""

# ============================================================
# Download function (3 attempts per file)
# ============================================================
download_file() {
    local rel="$1"
    local dest="$TEMP_DIR/files/$rel"
    local url="$GITHUB_RAW/$(echo "$rel" | sed 's/ /%20/g')"
    local try=1

    mkdir -p "$(dirname "$dest")"
    echo "  -> Downloading: $rel"

    while [ "$try" -le 3 ]; do
        rm -f "$dest"
        if wget -q --no-check-certificate "$url" -O "$dest" 2>>"$LOG_FILE"; then
            # Empty files are only allowed for __init__.py
            if [ -s "$dest" ] || [ "$(basename "$rel")" = "__init__.py" ]; then
                return 0
            fi
        fi
        try=$((try + 1))
        sleep 1
    done

    echo "    [ERROR] Failed to download $rel"
    echo "FAILED: $url" >> "$LOG_FILE"
    rm -f "$dest"
    return 1
}

# --- Download everything ---
echo ">>> Downloading plugin files..."
OK_COUNT=0
FAILED_COUNT=0
FAILED_LIST=""
: > "$TEMP_DIR/ok.txt"

while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    if download_file "$rel"; then
        OK_COUNT=$((OK_COUNT + 1))
        echo "$rel" >> "$TEMP_DIR/ok.txt"
    else
        FAILED_COUNT=$((FAILED_COUNT + 1))
        FAILED_LIST="$FAILED_LIST
      - $rel"
    fi
done < "$LIST"

# --- Abort if a critical file is missing ---
for cf in $CRITICAL_FILES; do
    if [ ! -f "$TEMP_DIR/files/$cf" ]; then
        echo ""
        echo "[ERROR] Critical file missing: $cf"
        echo "        Installation aborted. Existing plugin was not changed."
        echo "        Check your internet connection and try again."
        echo "        Details: $LOG_FILE"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
done

echo ""
echo ">>> Downloaded $OK_COUNT of $TOTAL files"
if [ "$FAILED_COUNT" -gt 0 ]; then
    echo "[WARNING] $FAILED_COUNT file(s) failed to download:$FAILED_LIST"
    echo "Continuing anyway..."
fi

# --- Warn if the plugin needs webserver.py but it is missing ---
if grep -q "webserver" "$TEMP_DIR/files/plugin.py" "$TEMP_DIR/files/__init__.py" 2>/dev/null; then
    if [ ! -f "$TEMP_DIR/files/webserver.py" ]; then
        echo ""
        echo "[WARNING] plugin uses webserver but webserver.py was not downloaded!"
        echo "          The plugin may not appear in the Plugin Browser."
    fi
fi

# ============================================================
# Install (same folder structure as GitHub)
# ============================================================
echo ""
echo ">>> Installing plugin files..."

mkdir -p "$PLUGIN_DIR"
cp -rf "$TEMP_DIR/files/." "$PLUGIN_DIR/" 2>>"$LOG_FILE"

# --- Remove old pyc ---
echo ">>> Removing old .pyo / .pyc files..."
find "$PLUGIN_DIR" -name "*.pyo" -exec rm -f {} \; 2>/dev/null
find "$PLUGIN_DIR" -name "*.pyc" -exec rm -f {} \; 2>/dev/null
rm -rf "$PLUGIN_DIR/__pycache__" 2>/dev/null

# --- Permissions ---
find "$PLUGIN_DIR" -type d -exec chmod 755 {} \; 2>/dev/null
find "$PLUGIN_DIR" -type f -exec chmod 644 {} \; 2>/dev/null

# --- Verify that every downloaded file really landed in the plugin folder ---
MISSING=0
while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    if [ ! -f "$PLUGIN_DIR/$rel" ]; then
        echo "    [ERROR] Not installed: $rel"
        MISSING=$((MISSING + 1))
    fi
done < "$TEMP_DIR/ok.txt"

if [ "$MISSING" -gt 0 ]; then
    echo "[WARNING] $MISSING file(s) were not copied. Check free space: df -h"
else
    echo "    [OK] All downloaded files verified"
fi

# --- Show version ---
NEW_VERSION=$(cat "$PLUGIN_DIR/version.txt" 2>/dev/null | head -n 1)
echo ""
echo "=========================================="
echo "  [OK] PomBiss installed successfully!"
echo "=========================================="
echo "  Version: $NEW_VERSION"
echo "  Path: $PLUGIN_DIR"
echo "  Files: $OK_COUNT"
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

# --- Cleanup temp files BEFORE footer ---
rm -rf "$TEMP_DIR"

# ============================================================
# BIG ASCII TEXT FOOTER (Slim, Centered & Spaced)
# ============================================================
echo ""
echo ""
echo "         _     _                 __              _    _ _ "
echo "        | |   (_)_ __  _   ___  __/ _| ___  _ __ / \\  | | |"
echo "        | |   | | '_ \\| | | \\ \\/ / |_ / _ \\| '__/ _ \\ | | |"
echo "        | |___| | | | | |_| |>  <|  _| (_) | |  / ___ \\| | |"
echo "        |_____|_|_| |_|\\__,_/_/\\_\\_|  \\___/|_| /_/   \\_\\_|_|"
echo ""
echo "                     ======================="
echo ""
echo "              J o i n   u s :   h t t p s : / / t . m e / V u S o l o"
echo ""
echo "                     ======================="
echo ""
echo ""

# --- Horizontal Countdown ---
echo ">>> Restarting Enigma2 in 10 seconds:"
for i in 10 9 8 7 6 5 4 3 2 1; do
    echo -n "$i... "
    sleep 1
done
echo ""
echo ""
echo "   [OK] Restarting now!"

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

exit 0
