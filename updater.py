# -*- coding: utf-8 -*-
"""
PomBiss Updater Module v1.7
- Uses Console screen to show installation progress live
- Runs installer via wget | sh (like RaedQuickSignal)
- Creates marker file /tmp/pombiss_from_plugin so installer knows source
- After installer finishes, restarts Enigma2 via TryQuitMainloop
"""

import os
import ssl

try:
    import urllib.request
except:
    import urllib2 as urllib

from Screens.MessageBox import MessageBox
from Screens.Console import Console
from Screens.Standby import TryQuitMainloop
from enigma import eTimer


PLUGIN_VERSION = "1.7"

VERSION_URL = "https://raw.githubusercontent.com/Shr776/PomBiss/main/version.txt"
INSTALLER_URL = "https://raw.githubusercontent.com/Shr776/PomBiss/main/installer.sh"

PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"

RESTART_FLAG = "/tmp/pombiss_need_restart"
FROM_PLUGIN_FLAG = "/tmp/pombiss_from_plugin"

_active_timers = []


def log_debug(msg):
    try:
        with open("/tmp/PomBiss_Update.log", "a") as f:
            f.write("[Updater] %s\n" % msg)
    except:
        pass


def _fetch_url(url, timeout=10):
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


def _is_newer(latest, current):
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


def check_for_update(session, silent_if_no_update=True, on_no_update=None):
    log_debug("=== checking for update (current=%s) ===" % PLUGIN_VERSION)

    latest = _fetch_url(VERSION_URL)

    if latest is None:
        log_debug("cannot fetch version.txt")
        if not silent_if_no_update:
            session.open(
                MessageBox,
                "\u274C Cannot check for updates.\n\n"
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


def _do_update(session):
    log_debug("=== UPDATE STARTED ===")

    try:
        if os.path.exists(RESTART_FLAG):
            os.remove(RESTART_FLAG)
    except:
        pass

    try:
        open(FROM_PLUGIN_FLAG, "w").close()
        log_debug("Marker created: %s" % FROM_PLUGIN_FLAG)
    except:
        pass

    cmd = "wget -q --no-check-certificate %s -O - | /bin/sh" % INSTALLER_URL

    log_debug("Executing: %s" % cmd)

    def console_finished(*args):
        log_debug("=== Console finished ===")
        _check_restart_flag(session)

    try:
        session.openWithCallback(
            console_finished,
            Console,
            title="PomBiss Update",
            cmdlist=[cmd],
            finishedCallback=console_finished,
            closeOnSuccess=False
        )
        log_debug("Console opened")
    except Exception as e:
        import traceback
        log_debug("Console open error: %s" % str(e))
        log_debug(traceback.format_exc())
        session.open(
            MessageBox,
            "\u274C Console error: %s" % str(e),
            MessageBox.TYPE_ERROR, timeout=8
        )


def _check_restart_flag(session):
    log_debug("=== checking restart flag ===")

    if os.path.exists(RESTART_FLAG):
        log_debug("RESTART FLAG FOUND -> TryQuitMainloop, 3")

        try:
            os.remove(RESTART_FLAG)
        except:
            pass

        session.open(
            MessageBox,
            "\u2705 Update installed successfully!\n\n"
            "\U0001F504 Enigma2 will now restart.",
            MessageBox.TYPE_INFO,
            timeout=3
        )

        def do_restart():
            log_debug("Calling TryQuitMainloop(3)")
            try:
                session.open(TryQuitMainloop, 3)
            except Exception as e:
                log_debug("TryQuitMainloop error: %s" % str(e))

        t = eTimer()
        try:
            t.timeout.connect(do_restart)
        except:
            t.callback.append(do_restart)
        _active_timers.append(t)
        t.start(3500, True)

    else:
        log_debug("no restart flag -> showing result")
        session.open(
            MessageBox,
            "\u26A0 Update finished but no restart flag found.\n\n"
            "Check /tmp/pombiss_install.log for details.",
            MessageBox.TYPE_WARNING,
            timeout=8
        )
