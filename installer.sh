#!/bin/sh
#
# ============================================================
#   PomBiss Plugin Installer v2.1
# ============================================================
#
#   🎯 Sports Feed Viewer for Enigma2
#
#   📺 Supported Images:
#     ✔ OpenBlackHole 5
#     ✔ OpenBlackHole 6
#     ✔ OpenATV 7.6
#     ✔ OpenATV 8.0
#     ✔ OpenPLi 8.3
#
#   🌐 GitHub:
#     https://github.com/Shr776/PomBiss
#
#   💬 Telegram:
#     https://t.me/VuSolo
#
#   📥 Installation (Telnet):
#     wget -q --no-check-certificate https://raw.githubusercontent.com/Shr776/PomBiss/main/installer.sh -O - | /bin/sh
#
#   📥 Installation (Plugin):
#     Open PomBiss Plugin → Press YELLOW button (Update)
#
# ============================================================

# --- تنظیمات ---
PLUGIN_NAME="PomBiss"
PLUGIN_VERSION="2.1"
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"
GITHUB_RAW="https://raw.githubusercontent.com/Shr776/PomBiss/main"
TEMP_DIR="/tmp/pombiss_install"
LOG_FILE="/tmp/pombiss_install.log"

# --- نمایش هدر ---
echo "=========================================="
echo "  PomBiss Plugin Installer v${PLUGIN_VERSION}"
echo "=========================================="
echo ""
echo " Supported Images:"
echo "   ✔ OpenBlackHole 5"
echo "   ✔ OpenBlackHole 6"
echo "   ✔ OpenATV 7.6"
echo "   ✔ OpenATV 8.0"
echo "   ✔ OpenPLi 8.3"
echo ""
echo " Installing to: $PLUGIN_DIR"
echo " Log file: $LOG_FILE"
echo ""

# --- چک wget ---
if ! which wget >/dev/null 2>&1; then
    echo "❌ ERROR: wget not found!"
    echo "Please install wget first:"
    echo "  opkg update && opkg install wget"
    exit 1
fi

# --- ساخت پوشه موقت ---
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
mkdir -p "$TEMP_DIR/files"

# --- تابع دانلود ---
download_file() {
    local url="$1"
    local dest="$2"
    echo "  → Downloading: $(basename $dest)"
    wget -q --no-check-certificate "$url" -O "$dest"
    if [ ! -f "$dest" ]; then
        echo "    ❌ ERROR: Failed to download $url"
        return 1
    fi
    return 0
}

# --- لیست فایل‌ها ---
FILES="
__init__.py
plugin.py
signalfinder.py
signalfinder_pli_py2.py
signalfinder_atv.py
signalfinder_obh.py
updater.py
registration.py
PomBiss_logo.png
version.txt
"

# --- دانلود همه فایل‌ها ---
echo "📥 Downloading plugin files..."
FAILED=0

for file in $FILES; do
    if ! download_file "$GITHUB_RAW/$file" "$TEMP_DIR/files/$file"; then
        FAILED=$((FAILED + 1))
    fi
done

if [ "$FAILED" -gt 0 ]; then
    echo ""
    echo "⚠ WARNING: $FAILED file(s) failed to download"
    echo "Continuing anyway..."
fi

# --- نصب ---
echo ""
echo "📦 Installing plugin files..."

# چک اگه پوشه پلاگین نیست، بساز
if [ ! -d "$PLUGIN_DIR" ]; then
    mkdir -p "$PLUGIN_DIR"
fi

# کپی فایل‌ها
for file in $(ls "$TEMP_DIR/files/"); do
    cp -f "$TEMP_DIR/files/$file" "$PLUGIN_DIR/$file" 2>/dev/null
done

# --- پاک کردن .pyo قدیمی ---
echo "🗑 Removing old .pyo files..."
rm -f "$PLUGIN_DIR"/*.pyo 2>/dev/null
rm -f "$PLUGIN_DIR"/*.pyc 2>/dev/null

# --- permission ---
chmod 644 "$PLUGIN_DIR"/*.py 2>/dev/null
chmod 644 "$PLUGIN_DIR"/*.png 2>/dev/null

# --- نمایش نسخه ---
NEW_VERSION=$(cat "$TEMP_DIR/files/version.txt" 2>/dev/null | head -n 1)
echo ""
echo "=========================================="
echo "  ✅ PomBiss installed successfully!"
echo "=========================================="
echo "  📌 Version: $NEW_VERSION"
echo "  📁 Path: $PLUGIN_DIR"
echo ""
echo "🔄 Please restart Enigma2:"
echo "   init 4 && sleep 2 && init 3"
echo ""
echo "💬 Telegram: https://t.me/VuSolo"
echo ""

# --- ساخت flag برای ریستارت خودکار از پلاگین ---
if [ -f /tmp/pombiss_from_plugin ]; then
    echo "🔁 Restart flag created for plugin update"
    touch /tmp/pombiss_need_restart
fi

# --- پاکسازی ---
rm -rf "$TEMP_DIR"

exit 0
