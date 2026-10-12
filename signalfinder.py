# -*- coding: utf-8 -*-
"""
Signalfinder Dispatcher for PomBiss
=====================================
Auto-detects:
  - Python version (2 / 3)
  - Image (OpenATV / OpenBlackHole / OpenPLi / DreamOS)

Loads the correct signalfinder implementation.

Supported:
  - OpenBlackHole 5 / 6
  - OpenATV 7.6 / 8.0
  - OpenPLi 8.3
"""

from __future__ import print_function

import sys
import os


def log_debug(msg):
    try:
        with open("/tmp/PomBiss.log", "a") as f:
            f.write("[Signalfinder-Dispatcher] %s\n" % msg)
    except:
        pass


# ============================================================
# Detection helpers
# ============================================================
def _detect_python():
    """Detect Python major version (2 or 3)"""
    try:
        if sys.version_info[0] == 2:
            return 2
        elif sys.version_info[0] == 3:
            return 3
    except:
        pass
    return 3


def _read_file_safe(path):
    """Read file content safely as lowercase string"""
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().lower()
    except:
        pass
    return ""


def _detect_image():
    """
    Detect image family.
    Returns one of: 'atv', 'obh', 'pli', 'dream', 'unknown'
    """
    issue = _read_file_safe("/etc/issue")
    version = _read_file_safe("/etc/image-version")
    osrel = _read_file_safe("/etc/os-release")
    pli_ver = _read_file_safe("/etc/version")

    combined = " ".join([issue, version, osrel, pli_ver])

    # Priority 1: OpenBlackHole
    if "openbh" in combined or "blackhole" in combined or "openblackhole" in combined:
        return "obh"

    # Priority 2: OpenPLi
    if "openpli" in combined:
        return "pli"

    # Priority 3: OpenATV
    if "openatv" in combined or "atv" in issue:
        return "atv"

    # Priority 4: DreamOS
    if "dreamos" in combined or "dreamelite" in combined or "newenigma" in combined:
        return "dream"

    # Priority 5: check opkg feed files
    if os.path.exists("/etc/opkg/openbh-feed.conf"):
        return "obh"
    if os.path.exists("/etc/opkg/openpli-feed.conf"):
        return "pli"
    if os.path.exists("/etc/opkg/openatv-feed.conf"):
        return "atv"

    return "unknown"


# ============================================================
# Loader
# ============================================================
def _try_import(module_name):
    """Try importing a PomBiss signalfinder module"""
    try:
        full_path = "Plugins.Extensions.PomBiss." + module_name
        mod = __import__(full_path, fromlist=[module_name])
        log_debug("Loaded: %s" % module_name)
        return mod
    except Exception as e:
        log_debug("Failed %s: %s" % (module_name, str(e)))
        return None


def _load_impl():
    """
    Load the right signalfinder implementation.

    v2.1: Removed _py3 dependency.
    All 3 files (obh/atv/pli_py2) work on both Python 2 and 3.
    """
    py = _detect_python()
    image = _detect_image()
    log_debug("Detected: Python %d, Image %s" % (py, image))

    candidates = []

    # v2.1: Same logic for Python 2 and 3
    if image == "obh":
        # OpenBlackHole 5/6 - Python 2 or 3
        candidates = [
            "signalfinder_obh",        # OBH first
            "signalfinder_atv",        # ATV fallback
            "signalfinder_pli_py2",    # PLi fallback
        ]
    elif image == "atv":
        # OpenATV 7.6/8.0 - Python 2 or 3
        candidates = [
            "signalfinder_atv",        # ATV first
            "signalfinder_obh",        # OBH fallback
            "signalfinder_pli_py2",    # PLi fallback
        ]
    elif image == "pli":
        # OpenPLi 8.3 - Python 2
        candidates = [
            "signalfinder_pli_py2",    # PLi first
            "signalfinder_obh",        # OBH fallback
            "signalfinder_atv",        # ATV fallback
        ]
    else:
        # Unknown image - try all
        candidates = [
            "signalfinder_atv",
            "signalfinder_obh",
            "signalfinder_pli_py2",
        ]

    # Try each candidate in order
    for name in candidates:
        mod = _try_import(name)
        if mod is not None:
            log_debug("=== Successfully loaded: %s ===" % name)
            return mod

    log_debug("!!! No signalfinder module could be loaded !!!")
    return None


# Load once at import time
_impl = _load_impl()


# ============================================================
# Public API
# ============================================================
def open_signal_finder(session, feed):
    """Open signal finder with the given feed"""
    if _impl is None:
        try:
            from Screens.MessageBox import MessageBox
            session.open(MessageBox,
                "Signal finder module not found!\n\n"
                "Python: %d\n"
                "Please reinstall PomBiss.",
                MessageBox.TYPE_ERROR, timeout=8)
        except:
            pass
        return

    try:
        _impl.open_signal_finder(session, feed)
    except Exception as e:
        import traceback
        log_debug("open_signal_finder error: %s" % str(e))
        log_debug(traceback.format_exc())
        try:
            from Screens.MessageBox import MessageBox
            session.open(MessageBox, "Error: %s" % str(e),
                         MessageBox.TYPE_ERROR, timeout=8)
        except:
            pass


def push_key_to_keyadder(session, cw, feed=None):
    """Forward to loaded implementation if it has this method"""
    if _impl is None:
        return
    try:
        if hasattr(_impl, 'push_key_to_keyadder'):
            _impl.push_key_to_keyadder(session, cw, feed)
    except Exception as e:
        log_debug("push_key error: %s" % str(e))


# ============================================================
# Info (optional, for debugging)
# ============================================================
def get_info():
    """Return dict with detected info (for debug)"""
    return {
        "python": _detect_python(),
        "image": _detect_image(),
        "loaded_module": _impl.__name__ if _impl else None,
    }
