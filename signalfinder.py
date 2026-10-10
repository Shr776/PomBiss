# -*- coding: utf-8 -*-
"""
Signalfinder dispatcher for PomBiss
- Auto-detects image (OpenATV vs OpenBlackHole)
- Loads the correct signalfinder module
"""

import os


def log_debug(msg):
    try:
        with open("/tmp/PomBiss.log", "a") as f:
            f.write("[Signalfinder-Dispatcher] %s\n" % msg)
    except:
        pass


def _detect_image():
    """تشخیص خودکار ایمیج"""
    try:
        # روش ۱: /etc/issue
        if os.path.exists("/etc/issue"):
            try:
                with open("/etc/issue", "r") as f:
                    issue = f.read().lower()
                if "openbh" in issue or "blackhole" in issue:
                    return "obh"
                if "openatv" in issue:
                    return "atv"
            except:
                pass

        # روش ۲: /etc/image-version
        if os.path.exists("/etc/image-version"):
            try:
                with open("/etc/image-version", "r") as f:
                    version = f.read().lower()
                if "openbh" in version or "blackhole" in version:
                    return "obh"
                if "openatv" in version:
                    return "atv"
            except:
                pass

        # روش ۳: /etc/os-release
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r") as f:
                    osrel = f.read().lower()
                if "openbh" in osrel or "blackhole" in osrel:
                    return "obh"
                if "openatv" in osrel:
                    return "atv"
            except:
                pass

        # روش ۴: وجود فایل‌های اختصاصی
        if os.path.exists("/etc/opkg/openbh-feed.conf"):
            return "obh"
        if os.path.exists("/etc/opkg/openatv-feed.conf"):
            return "atv"
    except:
        pass

    return "unknown"


def _load_signal_finder_module():
    """لود ماژول درست بر اساس ایمیج"""
    image = _detect_image()
    log_debug("Detected image: %s" % image)

    module = None

    if image == "obh":
        try:
            from . import signalfinder_obh as module
            log_debug("Loaded signalfinder_obh (OpenBlackHole)")
            return module
        except Exception as e:
            log_debug("signalfinder_obh load error: %s" % str(e))

    elif image == "atv":
        try:
            from . import signalfinder_atv as module
            log_debug("Loaded signalfinder_atv (OpenATV)")
            return module
        except Exception as e:
            log_debug("signalfinder_atv load error: %s" % str(e))

    # fallback: اگه ایمیج ناشناخته بود، هر دو رو امتحان کن
    if module is None:
        try:
            from . import signalfinder_atv as module
            log_debug("Fallback: loaded signalfinder_atv")
            return module
        except Exception as e:
            log_debug("atv fallback err: %s" % str(e))

    if module is None:
        try:
            from . import signalfinder_obh as module
            log_debug("Fallback: loaded signalfinder_obh")
            return module
        except Exception as e:
            log_debug("obh fallback err: %s" % str(e))

    return None


# ⭐ لود ماژول درست در لحظه import
_impl = _load_signal_finder_module()


# ⭐ Forward کردن توابع عمومی به ماژول درست
def open_signal_finder(session, feed):
    if _impl is None:
        from Screens.MessageBox import MessageBox
        session.open(MessageBox,
            "Signal finder module not found!\n\n"
            "Please reinstall PomBiss.",
            MessageBox.TYPE_ERROR, timeout=8)
        return

    try:
        _impl.open_signal_finder(session, feed)
    except Exception as e:
        import traceback
        log_debug("open_signal_finder error: %s" % str(e))
        log_debug(traceback.format_exc())
        from Screens.MessageBox import MessageBox
        session.open(MessageBox, "Error: %s" % str(e),
                     MessageBox.TYPE_ERROR, timeout=8)


def push_key_to_keyadder(session, cw, feed=None):
    if _impl is None:
        return
    try:
        if hasattr(_impl, 'push_key_to_keyadder'):
            _impl.push_key_to_keyadder(session, cw, feed)
    except Exception as e:
        log_debug("push_key error: %s" % str(e))