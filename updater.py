# -*- coding: utf-8 -*-
"""
PomBiss Updater Module
- Checks version.txt on GitHub for new version
- Downloads installer.sh and runs it via nohup
- Installer handles the rest (init 4 && init 3)
"""

import os
import ssl

try:
    import urllib.request
except:
    import urllib2 as urllib

from Screens.MessageBox import MessageBox
from enigma import eTimer


# ============================================================
# تنظیمات - اینجا رو با هر آپدیت دستی عوض کن
# ============================================================
PLUGIN_VERSION = "1.1"

VERSION_URL = "https://raw.githubusercontent.com/Shr776/PomBiss/main/version.txt"
INSTALLER_URL = "https://raw.githubusercontent.com/Shr776/PomBiss/main/installer.sh"

PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"


# ============================================================
# لاگ
# ============================================================
def log_debug(msg):
    try:
        with open("/tmp/PomBiss_Update.log", "a") as f:
            f.write("[Updater] %s\n" % msg)
    except:
        pass


# ============================================================
# دانلود URL
# ============================================================
def _fetch_url(url, timeout=10):
    """دانلود محتوای یک URL با SSL غیر امن (برای Enigma2)"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PomBiss"})
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        try:
            response = urllib.request.urlopen(req, timeout=timeout, context=context)
        except TypeError:
            response = urllib.request.urlopen(req, timeout=timeout)

        return response.read().decode("utf-8", "ignore").strip()
    except Exception as e:
        log_debug("fetch error [%s]: %s" % (url, str(e)))
        return None


# ============================================================
# مقایسه نسخه‌ها
# ============================================================
def _is_newer(latest, current):
    """latest > current ?"""
    try:
        l = [int(x) for x in str(latest).split(".")]
        c = [int(x) for x in str(current).split(".")]
        while len(l) < len(c):
            l.append(0)
        while len(c) < len(l):
            c.append(0)
        return l > c
    except:
        return False


def get_version():
    return PLUGIN_VERSION


# ============================================================
# چک آپدیت
# ============================================================
def check_for_update(session, silent_if_no_update=True, on_no_update=None):
    """
    چک نسخه جدید.
    - نسخه جدید بود → MessageBox میاد
    - نبود → اگه silent=True هیچی، وگرنه پیام "Up to date"
    """
    log_debug("=== checking for update (current=%s) ===" % PLUGIN_VERSION)

    latest = _fetch_url(VERSION_URL)

    if latest is None:
        log_debug("cannot fetch version.txt")
        if not silent_if_no_update:
            session.open(
                MessageBox,
                "❌ Cannot check for updates.\n\n"
                "Please check your internet connection.",
                MessageBox.TYPE_ERROR, timeout=8
            )
        elif on_no_update:
            on_no_update()
        return

    latest = latest.strip().replace("\r", "").replace("\n", "")
    log_debug("latest version: %s" % latest)

    if _is_newer(latest, PLUGIN_VERSION):
        log_debug("NEW VERSION: %s -> %s" % (PLUGIN_VERSION, latest))

        msg = (
            "\U0001F504 New version available!\n\n"
            "Current: %s\n"
            "Latest:  %s\n\n"
            "Do you want to update now?\n\n"
            "\u26A0 Enigma2 will restart after the update."
        ) % (PLUGIN_VERSION, latest)

        def cb(answer):
            if answer:
                _do_update(session)
            else:
                log_debug("User skipped update")
                if on_no_update:
                    on_no_update()

        session.openWithCallback(cb, MessageBox, msg, MessageBox.TYPE_YESNO)

    else:
        log_debug("already up to date")
        if not silent_if_no_update:
            session.open(
                MessageBox,
                "\u2705 You are using the latest version.\n\n"
                "Version: %s" % PLUGIN_VERSION,
                MessageBox.TYPE_INFO, timeout=5
            )
        elif on_no_update:
            on_no_update()


# ============================================================
# اجرای آپدیت
# ============================================================
def _do_update(session):
    """دانلود installer.sh و اجرا با nohup"""
    log_debug("=== UPDATE STARTED ===")

    script_path = "/tmp/pombiss_update.sh"

    # ۱) پیام "در حال آپدیت"
    session.open(
        MessageBox,
        "\u23F3 Downloading update...\n\n"
        "Please wait, Enigma2 will restart automatically.",
        MessageBox.TYPE_INFO, timeout=4
    )

    # ۲) بعد از ۱.۵ ثانیه، اسکریپت دانلود و اجرا بشه
    def launch():
        try:
            script = _fetch_url(INSTALLER_URL, timeout=15)
            if not script:
                session.open(
                    MessageBox,
                    "\u274C Failed to download installer.",
                    MessageBox.TYPE_ERROR, timeout=8
                )
                return

            with open(script_path, "w") as f:
                f.write(script)
            os.chmod(script_path, 0o755)
            log_debug("installer saved: %s" % script_path)

            # اجرا با nohup → از پلاگین جدا می‌شه
            # installer.sh خودش init 4 && init 3 می‌زنه
            os.system(
                "nohup sh %s > /tmp/pombiss_update.log 2>&1 &" % script_path
            )
            log_debug("installer launched")

        except Exception as e:
            log_debug("update launch error: %s" % str(e))
            session.open(
                MessageBox,
                "\u274C Update error: %s" % str(e),
                MessageBox.TYPE_ERROR, timeout=8
            )

    t = eTimer()
    try:
        t.timeout.connect(launch)
    except:
        t.callback.append(launch)
    t.start(1500, True)