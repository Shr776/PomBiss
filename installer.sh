#!/bin/sh
#
# ============================================================
#   PomBiss Plugin Installer v2.4
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
#     ✔ OpenPLi 9.2
#     ✔ Egami 11.2
#
#   🌐 GitHub:
#     https://github.com/Shr776/PomBiss
#
#   💬 Telegram:
#     📢 Main:      https://t.me/VuSolo
#     📡 Feeds:     https://t.me/PomFeed
#     💬 Support:   https://t.me/PomSat
#     👨‍💻 Developer: https://t.me/Shr776
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
PLUGIN_VERSION="2.4"
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
echo "   ✔ OpenPLi 9.2"
echo "   ✔ Egami 11.2"
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
mkdir -p "$TEMP_DIR/files/picon"

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

# --- لیست فایل‌های اصلی ---
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

# --- دانلود فایل‌های اصلی ---
echo "📥 Downloading plugin files..."
FAILED=0

for file in $FILES; do
    if ! download_file "$GITHUB_RAW/$file" "$TEMP_DIR/files/$file"; then
        FAILED=$((FAILED + 1))
    fi
done

# --- دانلود پوشه picon (لوگو) ---
echo "📥 Downloading picon files..."
if ! download_file "$GITHUB_RAW/picon/PomBiss_logo.png" "$TEMP_DIR/files/picon/PomBiss_logo.png"; then
    FAILED=$((FAILED + 1))
fi

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

# کپی فایل‌های اصلی
for file in $(ls "$TEMP_DIR/files/" | grep -v "picon"); do
    cp -f "$TEMP_DIR/files/$file" "$PLUGIN_DIR/$file" 2>/dev/null
done

# ساخت و کپی پوشه پیکون
if [ ! -d "$PLUGIN_DIR/picon" ]; then
    mkdir -p "$PLUGIN_DIR/picon"
fi
cp -f "$TEMP_DIR/files/picon/"* "$PLUGIN_DIR/picon/" 2>/dev/null

# --- پاک کردن .pyo و .pyc قدیمی ---
echo "🗑 Removing old .pyo / .pyc files..."
rm -f "$PLUGIN_DIR"/*.pyo 2>/dev/null
rm -f "$PLUGIN_DIR"/*.pyc 2>/dev/null

# --- permission ---
chmod 644 "$PLUGIN_DIR"/*.py 2>/dev/null
chmod 644 "$PLUGIN_DIR"/*.png 2>/dev/null
chmod 755 "$PLUGIN_DIR/picon" 2>/dev/null
chmod 644 "$PLUGIN_DIR/picon/"* 2>/dev/null

# --- نمایش نسخه ---
NEW_VERSION=$(cat "$TEMP_DIR/files/version.txt" 2>/dev/null | head -n 1)
echo ""
echo "=========================================="
echo "  ✅ PomBiss installed successfully!"
echo "=========================================="
echo "  📌 Version: $NEW_VERSION"
echo "  📁 Path: $PLUGIN_DIR"
echo ""

# --- پیام کانال‌های تلگرام با مکث ۵ ثانیه ---
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                                                      ║"
echo "║              💬  JOIN US ON TELEGRAM                 ║"
echo "║                                                      ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║   📢 Main Channel:      @VUSOLO                      ║"
echo "║                         https://t.me/VuSolo          ║"
echo "║                                                      ║"
echo "║   📡 Feeds Channel:     @PomFeed                     ║"
echo "║                         https://t.me/PomFeed         ║"
echo "║                                                      ║"
echo "║   💬 Support Group:     @PomSat                      ║"
echo "║                         https://t.me/PomSat          ║"
echo "║                                                      ║"
echo "║   👨‍💻 Developer:        @Shr776                      ║"
echo "║                         https://t.me/Shr776          ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "🔄 Restarting Enigma2 in 5 seconds..."
sleep 1
echo "   4..."
sleep 1
echo "   3..."
sleep 1
echo "   2..."
sleep 1
echo "   1..."
sleep 1
echo "   🔄 Restarting now!"
echo ""

# --- ساخت flag برای ریستارت خودکار از پلاگین ---
if [ -f /tmp/pombiss_from_plugin ]; then
    echo "🔁 Restart flag created for plugin update"
    touch /tmp/pombiss_need_restart
fi

# --- ریستارت Enigma2 ---
if [ -f /tmp/pombiss_from_plugin ]; then
    # اگه از داخل پلاگین اجرا شده، فقط flag می‌ذاریم
    # (پلاگین خودش TryQuitMainloop رو صدا می‌زنه)
    :
else
    # اگه از تلنت اجرا شده، خودمون Enigma2 رو ریستارت می‌کنیم
    echo "🚀 Restarting Enigma2..."
    init 4 >/dev/null 2>&1
    sleep 2
    init 3 >/dev/null 2>&1
fi

# --- پاکسازی ---
rm -rf "$TEMP_DIR"

# ============================================================
# ⭐ NEW: Footer / Signature (Centered)
# ============================================================
echo ""
echo ""
echo ""
echo ""
echo -e "\033[1;32m                    🌱 ‌▬▬▬▬▬▬▬▬▬▬▬▬ 🌞\033[0m"
echo -e "\033[1;33m                           ⭐️ㅤ   💬ㅤ     ✉️ㅤ     🌐\033[0m"
echo -e "\033[1;37m                           ˡᶦᵏᵉ    ᶜᵒᵐᵐᵉⁿᵗ    ˢᵃᵛᵉ      ˢʰᵃʳᵉ \033[0m"
echo -e "\033[1;36m                                  📮 @VUSOLO 📮\033[0m"
echo -e "\033[1;37m                          Linux for all - لینوکس برای همه\033[0m"
echo -e "\033[1;36m                    ⛈ ▬▬▬▬▬▬▬▬▬▬▬▬ ❄️\033[0m"
echo ""
echo ""
echo ""

exit 0
