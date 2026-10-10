#!/bin/sh
# PomBiss Installer v1.9
# Supports OpenATV 7.6/8.0 and OpenBlackHole

echo "========================================="
echo "  PomBiss Plugin Installer v1.9"
echo "========================================="

PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"
GITHUB_RAW="https://raw.githubusercontent.com/Shr776/PomBiss/main"

# ⭐ تشخیص ایمیج
IMAGE="unknown"
if [ -f /etc/issue ]; then
    ISSUE=$(cat /etc/issue | head -1 | tr '[:upper:]' '[:lower:]')
    if echo "$ISSUE" | grep -q "openbh\|blackhole"; then
        IMAGE="obh"
    elif echo "$ISSUE" | grep -q "openatv"; then
        IMAGE="atv"
    fi
fi

if [ "$IMAGE" = "unknown" ]; then
    if [ -f /etc/image-version ]; then
        VER=$(cat /etc/image-version | tr '[:upper:]' '[:lower:]')
        if echo "$VER" | grep -q "openbh\|blackhole"; then
            IMAGE="obh"
        elif echo "$VER" | grep -q "openatv"; then
            IMAGE="atv"
        fi
    fi
fi

echo "[*] Detected image: $IMAGE"

# ⭐ ساخت پوشه
mkdir -p "$PLUGIN_DIR"

# ⭐ دانلود فایل‌های اصلی
echo "[*] Downloading plugin files..."

wget -q --no-check-certificate "$GITHUB_RAW/plugin.py" \
     -O "$PLUGIN_DIR/plugin.py" || echo "[!] plugin.py failed"

wget -q --no-check-certificate "$GITHUB_RAW/updater.py" \
     -O "$PLUGIN_DIR/updater.py" || echo "[!] updater.py failed"

wget -q --no-check-certificate "$GITHUB_RAW/registration.py" \
     -O "$PLUGIN_DIR/registration.py" || echo "[!] registration.py failed"

# ⭐ فایل dispatcher
wget -q --no-check-certificate "$GITHUB_RAW/signalfinder.py" \
     -O "$PLUGIN_DIR/signalfinder.py" || echo "[!] signalfinder.py failed"

# ⭐ فایل‌های اختصاصی ایمیج
wget -q --no-check-certificate "$GITHUB_RAW/signalfinder_atv.py" \
     -O "$PLUGIN_DIR/signalfinder_atv.py" || echo "[!] signalfinder_atv.py failed"

wget -q --no-check-certificate "$GITHUB_RAW/signalfinder_obh.py" \
     -O "$PLUGIN_DIR/signalfinder_obh.py" || echo "[!] signalfinder_obh.py failed"

# ⭐ حذف کش قدیمی
echo "[*] Cleaning old cache..."
rm -f "$PLUGIN_DIR"/*.pyo
rm -f "$PLUGIN_DIR"/*.pyc

# ⭐ نمایش فایل‌های نصب‌شده
echo "[*] Installed files:"
ls -la "$PLUGIN_DIR" | grep "\.py$"

# ⭐ علامت restart
touch /tmp/pombiss_need_restart

if [ -f /tmp/pombiss_from_plugin ]; then
    rm -f /tmp/pombiss_from_plugin
    echo "[*] Restart flag set (plugin updater will restart)"
else
    echo ""
    echo "========================================="
    echo "  Installation complete!"
    echo "  Restart Enigma2 with:"
    echo "  # init 4 && sleep 2 && init 3"
    echo "========================================="
fi

exit 0
