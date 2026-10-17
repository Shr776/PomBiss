#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
PomBiss Plugin for Enigma2 v5.6
Sports Feed Viewer - Neon Dual Panel Theme
+ LIVE PIP PREVIEW (800 x 450)
+ M3U Export Manager with timestamped files
+ MENU -> ChoiceBox (Contact + M3U)
+ M3U with group-title for AJ Panel / IPTV Players
+ Compact color buttons (fit inside left panel)
+ Stronger glow effect for preview borders
+ CLEAN VERSION - No emoji (Enigma2 doesn't support them)
+ v5.6:
  - URL-encode ServiceReference for M3U (AJ Panel compatible)
  - Use display_name / feed_id as channel name
  - DELETE ALL now removes PomBiss_services.json too
  - AUTO-CLEANUP: removes JSON + M3U if older than AUTO_CLEAN_HOURS
"""

from __future__ import print_function

try:
    from . import _
except:
    pass

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
from Screens.ChoiceBox import ChoiceBox
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ActionMap import ActionMap
from enigma import getDesktop, eTimer
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

import requests
import time
import os
import glob
import signal
import subprocess
import json
from datetime import datetime

try:
    from urllib import quote
except:
    from urllib.parse import quote

plugin_dir = resolveFilename(SCOPE_PLUGINS, "Extensions/PomBiss")
FEEDS_URL = "https://raw.githubusercontent.com/Shr776/PomBissFeeds/main/feeds.txt"

from . import signalfinder
from . import registration
from . import updater

from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection
from Components.NimManager import nimmanager

config.plugins.PomBiss = ConfigSubsection()
config.plugins.PomBiss.feedfreq = ConfigInteger(default=11020, limits=(0, 13000))
config.plugins.PomBiss.feedsr = ConfigInteger(default=7200, limits=(0, 100000))
config.plugins.PomBiss.feedpol = ConfigInteger(default=1, limits=(0, 1))
config.plugins.PomBiss.feedpos = ConfigInteger(default=130, limits=(0, 3600))

_nimchoices = []
for slot in nimmanager.nim_slots:
    if slot.isCompatible('DVB-S'):
        _nimchoices.append((str(slot.slot), "Tuner %d" % slot.slot))
if not _nimchoices:
    _nimchoices = [("0", "Tuner 0")]

config.plugins.PomBiss.nimnum = ConfigSelection(
    default=_nimchoices[0][0],
    choices=_nimchoices
)

FULLHD = False
if getDesktop(0).size().width() > 1800:
    FULLHD = True


def log_debug(msg):
    try:
        with open("/tmp/PomBissSatfinder.log", "a") as f:
            f.write("[PomBiss] %s\n" % msg)
    except:
        pass


_pombiss_list_instance = None
_restart_timer = None

RESTART_FLAG = "/tmp/pombiss_need_restart"

M3U_DIR = "/media/hdd"
M3U_PREFIX = "PomBiss_M3U"
M3U_PATH = os.path.join(M3U_DIR, "PomBiss_M3U.m3u")
SERVICES_PATH = os.path.join(M3U_DIR, "PomBiss_services.json")
LAST_M3U_FILE = "/tmp/.pombiss_last_m3u"

# ⭐ v5.6: Auto-cleanup config
AUTO_CLEAN_HOURS = 24


# ============================================================
# Auto-cleanup
# ============================================================
def check_and_auto_cleanup():
    """
    v5.6: چک کن اگه از آخرین تغییر JSON بیشتر از AUTO_CLEAN_HOURS ساعت گذشته،
    فایل JSON و همه‌ی M3U ها رو پاک کن.
    
    Returns:
        bool: True اگه پاک شد، False اگه نه
    """
    try:
        if not os.path.exists(SERVICES_PATH):
            return False
        
        # ⭐ آخرین زمان تغییر JSON
        try:
            json_mtime = os.path.getmtime(SERVICES_PATH)
        except Exception as e:
            log_debug("auto-cleanup getmtime error: %s" % str(e))
            return False
        
        now = time.time()
        elapsed_hours = (now - json_mtime) / 3600.0
        
        log_debug("=== AUTO-CLEANUP CHECK ===")
        log_debug("JSON age: %.2f hours (limit: %d hours)" % (elapsed_hours, AUTO_CLEAN_HOURS))
        
        if elapsed_hours < AUTO_CLEAN_HOURS:
            log_debug("JSON is fresh - no cleanup needed")
            return False
        
        # ⭐ بیشتر از AUTO_CLEAN_HOURS گذشته -> پاک کن
        log_debug("!!! JSON is OLDER than %d hours -> AUTO CLEANUP !!!" % AUTO_CLEAN_HOURS)
        
        # شمارش فیدها قبل از پاک کردن (برای لاگ)
        feeds_count = 0
        try:
            with open(SERVICES_PATH, "r") as f:
                feeds_count = len(json.load(f))
        except:
            pass
        
        # پاک کردن JSON
        try:
            os.remove(SERVICES_PATH)
            log_debug("AUTO-CLEANED: removed %s (%d feeds)" % (SERVICES_PATH, feeds_count))
        except Exception as e:
            log_debug("auto-cleanup remove JSON error: %s" % str(e))
            return False
        
        # پاک کردن همه M3U های قدیمی
        try:
            all_files = get_all_m3u_files()
            deleted_m3u = 0
            for f in all_files:
                try:
                    os.remove(f)
                    deleted_m3u += 1
                    log_debug("AUTO-CLEANED: removed %s" % f)
                except:
                    pass
            log_debug("AUTO-CLEANED: %d M3U files removed" % deleted_m3u)
        except:
            pass
        
        # پاک کردن LAST_M3U_FILE
        try:
            if os.path.exists(LAST_M3U_FILE):
                os.remove(LAST_M3U_FILE)
        except:
            pass
        
        # پاک کردن M3U_PATH قدیمی
        try:
            if os.path.exists(M3U_PATH):
                os.remove(M3U_PATH)
        except:
            pass
        
        return True
        
    except Exception as e:
        log_debug("check_and_auto_cleanup error: %s" % str(e))
        return False


# ============================================================
# M3U Helpers
# ============================================================
def get_timestamped_m3u_path():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = "%s_%s.m3u" % (M3U_PREFIX, timestamp)
    return os.path.join(M3U_DIR, filename)


def cleanup_old_m3u_files(keep=3):
    try:
        pattern = os.path.join(M3U_DIR, "%s_*.m3u" % M3U_PREFIX)
        files = glob.glob(pattern)
        
        if len(files) <= keep:
            return len(files)
        
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        for f in files[keep:]:
            try:
                os.remove(f)
                log_debug("Old M3U removed: %s" % f)
            except:
                pass
        
        return len(files)
    except Exception as e:
        log_debug("cleanup_old_m3u_files error: %s" % str(e))
        return 0


def get_last_m3u_path():
    try:
        if os.path.exists(LAST_M3U_FILE):
            with open(LAST_M3U_FILE, "r") as f:
                path = f.read().strip()
            if os.path.exists(path):
                return path
    except:
        pass
    return None


def get_all_m3u_files():
    try:
        pattern = os.path.join(M3U_DIR, "%s*.m3u" % M3U_PREFIX)
        files = glob.glob(pattern)
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return files
    except:
        return []


def count_services():
    """Return number of services in JSON file (0 if not exists)"""
    try:
        if os.path.exists(SERVICES_PATH):
            with open(SERVICES_PATH, "r") as f:
                return len(json.load(f))
    except:
        pass
    return 0


def get_json_age_hours():
    """Return age of JSON file in hours (0 if not exists)"""
    try:
        if os.path.exists(SERVICES_PATH):
            return (time.time() - os.path.getmtime(SERVICES_PATH)) / 3600.0
    except:
        pass
    return 0


# ============================================================
# Clear PomBiss Keys
# ============================================================
def _find_softcam_key_for_clear():
    paths = [
        "/etc/tuxbox/config/oscam-emu",
        "/etc/tuxbox/config/oscam-trunk",
        "/etc/tuxbox/config/oscam",
        "/etc/tuxbox/config/ncam",
        "/etc/tuxbox/config/gcam",
        "/etc/tuxbox/config",
        "/etc",
        "/usr/keys",
        "/var/keys",
    ]

    for version_file, marker in [
        ("/tmp/.oscam/oscam.version", "configdir:"),
        ("/tmp/.ncam/ncam.version", "configdir:"),
        ("/tmp/.gcam/gcam.version", "configdir:"),
    ]:
        if os.path.exists(version_file):
            try:
                with open(version_file, "r") as f:
                    data = f.readlines()
                for line in data:
                    if marker in line.lower():
                        cfgdir = line.split(":")[1].strip()
                        paths.insert(0, cfgdir)
                        break
            except:
                pass

    for path in paths:
        softcamkey = os.path.join(path, "SoftCam.Key")
        if os.path.exists(softcamkey):
            return softcamkey

    return "/etc/tuxbox/config/SoftCam.Key"


def _restart_emulator_after_clear():
    emu_keywords = ["oscam", "ncam", "cccam", "mgcamd", "gbox",
                    "wicardd", "camd", "emu", "cam"]

    found_pids = []
    for proc_dir in glob.glob("/proc/[0-9]*"):
        try:
            pid = int(os.path.basename(proc_dir))
            comm_path = os.path.join(proc_dir, "comm")
            if not os.path.exists(comm_path):
                continue
            with open(comm_path, "r") as f:
                comm = f.read().strip()

            comm_lower = comm.lower()
            is_emu = False
            for kw in emu_keywords:
                if kw in comm_lower:
                    is_emu = True
                    break
            if not is_emu:
                continue

            exe_path = os.path.join(proc_dir, "exe")
            try:
                exe_real = os.readlink(exe_path)
            except:
                exe_real = ""

            cmdline_path = os.path.join(proc_dir, "cmdline")
            cmdline = ""
            try:
                with open(cmdline_path, "rb") as f:
                    raw = f.read()
                cmdline = raw.replace(b"\x00", b" ").decode("utf-8", "ignore").strip()
            except:
                pass

            found_pids.append({
                "pid": pid,
                "comm": comm,
                "exe": exe_real,
                "cmdline": cmdline,
            })
        except Exception:
            continue

    if not found_pids:
        return False

    for info in found_pids:
        try:
            os.kill(info["pid"], signal.SIGTERM)
        except:
            pass

    time.sleep(2)

    for info in found_pids:
        try:
            os.kill(info["pid"], signal.SIGKILL)
        except:
            pass

    time.sleep(1)

    restarted = False
    seen = set()
    for info in found_pids:
        exe = info["exe"]
        cmdline = info["cmdline"]

        if not exe or not os.path.exists(exe):
            continue

        if cmdline:
            cmd_parts = cmdline.split()
            if cmd_parts and cmd_parts[0] == exe:
                cmd_parts = cmd_parts[1:]
            if cmd_parts:
                full_cmd = [exe] + cmd_parts
            else:
                full_cmd = [exe]
        else:
            full_cmd = [exe]

        key = " ".join(full_cmd)
        if key in seen:
            continue
        seen.add(key)

        try:
            subprocess.Popen(
                full_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True
            )
            restarted = True
        except:
            pass

    if restarted:
        time.sleep(2)

    return restarted


def _clear_pombiss_keys():
    softcam_path = _find_softcam_key_for_clear()

    if not os.path.exists(softcam_path):
        return False, 0, "SoftCam.Key not found: %s" % softcam_path

    try:
        with open(softcam_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        removed_count = 0
        for line in lines:
            if "Edited by PomBiss" in line or "added by LIVE FEED" in line:
                removed_count += 1
            else:
                new_lines.append(line)

        if removed_count == 0:
            return True, 0, "No PomBiss or Live Feed keys found"

        backup_path = softcam_path + ".bak.pombiss"
        try:
            with open(backup_path, "w") as bf:
                bf.writelines(lines)
        except Exception as e:
            log_debug("backup error: %s" % str(e))

        with open(softcam_path, "w") as f:
            f.writelines(new_lines)

        log_debug("Cleared %d keys" % removed_count)
        return True, removed_count, "OK"

    except Exception as e:
        log_debug("clear error: %s" % str(e))
        return False, 0, "Error: %s" % str(e)


POSITION_FIX = {
    "31": "Eutelsat 3C ( 3.1E )",
    "216": "Eutelsat 21C ( 21.6E )",
}


# ============================================================
# CONTACT US SCREEN
# ============================================================
class PomBissContactScreen(Screen):
    skin = '''
<screen name="PomBissContact" position="center,center" size="1400,1080"
        title="PomBiss Contact" flags="wfNoBorder" backgroundColor="#0a0a1a">

    <widget name="line_top" position="50,15" size="1300,5"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <widget name="title" position="0,25" size="1400,60"
            font="Regular;36" transparent="1" foregroundColor="#00ff88"
            halign="center" valign="center" />

    <widget name="line_title" position="50,95" size="1300,5"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <widget name="dev_label" position="0,110" size="1400,38"
            font="Regular;24" transparent="1" foregroundColor="#ffff00"
            halign="center" valign="center" />
    <widget name="dev_id" position="0,152" size="1400,34"
            font="Regular;26" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />
    <widget name="dev_url" position="0,190" size="1400,30"
            font="Regular;20" transparent="1" foregroundColor="#00aaff"
            halign="center" valign="center" />

    <widget name="line1" position="250,225" size="900,5"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />

    <widget name="main_label" position="0,235" size="1400,38"
            font="Regular;24" transparent="1" foregroundColor="#ffff00"
            halign="center" valign="center" />
    <widget name="main_id" position="0,277" size="1400,34"
            font="Regular;26" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />
    <widget name="main_url" position="0,315" size="1400,30"
            font="Regular;20" transparent="1" foregroundColor="#00aaff"
            halign="center" valign="center" />

    <widget name="line2" position="250,350" size="900,5"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />

    <widget name="sup_label" position="0,360" size="1400,38"
            font="Regular;24" transparent="1" foregroundColor="#ffff00"
            halign="center" valign="center" />
    <widget name="sup_id" position="0,402" size="1400,34"
            font="Regular;26" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />
    <widget name="sup_url" position="0,440" size="1400,30"
            font="Regular;20" transparent="1" foregroundColor="#00aaff"
            halign="center" valign="center" />

    <widget name="line3" position="250,475" size="900,5"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />

    <widget name="feed_label" position="0,485" size="1400,38"
            font="Regular;24" transparent="1" foregroundColor="#ffff00"
            halign="center" valign="center" />
    <widget name="feed1_id" position="0,527" size="1400,34"
            font="Regular;26" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />
    <widget name="feed1_url" position="0,565" size="1400,30"
            font="Regular;20" transparent="1" foregroundColor="#00aaff"
            halign="center" valign="center" />
    <widget name="feed2_id" position="0,598" size="1400,34"
            font="Regular;26" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />
    <widget name="feed2_url" position="0,636" size="1400,30"
            font="Regular;20" transparent="1" foregroundColor="#00aaff"
            halign="center" valign="center" />

    <widget name="line4" position="250,670" size="900,5"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />

    <widget name="yt_label" position="0,680" size="1400,38"
            font="Regular;24" transparent="1" foregroundColor="#ffff00"
            halign="center" valign="center" />
    <widget name="yt_id" position="0,722" size="1400,34"
            font="Regular;26" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />
    <widget name="yt_url" position="0,760" size="1400,30"
            font="Regular;20" transparent="1" foregroundColor="#00aaff"
            halign="center" valign="center" />

    <widget name="line5" position="250,795" size="900,5"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />

    <widget name="gh_label" position="0,805" size="1400,38"
            font="Regular;24" transparent="1" foregroundColor="#ffff00"
            halign="center" valign="center" />
    <widget name="gh_id" position="0,847" size="1400,34"
            font="Regular;26" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />
    <widget name="gh_url" position="0,885" size="1400,30"
            font="Regular;20" transparent="1" foregroundColor="#00aaff"
            halign="center" valign="center" />

    <widget name="line_bot" position="50,925" size="1300,5"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <widget name="help" position="0,935" size="1400,30"
            font="Regular;18" transparent="1" foregroundColor="#dddddd"
            halign="center" valign="center" />

</screen>'''

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        self.links = [
            "https://t.me/Shr776",
            "https://t.me/VuSolo",
            "https://t.me/PomSat",
            "https://t.me/PomFeed",
            "https://t.me/FeedHunter",
            "https://www.youtube.com/@VUSOLO",
            "https://github.com/Shr776/PomBiss",
        ]
        self.current_index = 0

        self["line_top"] = Label("")
        self["title"] = Label("PomBiss Contact Us")
        self["line_title"] = Label("")

        self["dev_label"] = Label("DEVELOPER")
        self["dev_id"] = Label("@Shr776")
        self["dev_url"] = Label("https://t.me/Shr776")

        self["line1"] = Label("")

        self["main_label"] = Label("MAIN CHANNEL")
        self["main_id"] = Label("@VuSolo")
        self["main_url"] = Label("https://t.me/VuSolo")

        self["line2"] = Label("")

        self["sup_label"] = Label("SUPPORT GROUP")
        self["sup_id"] = Label("@PomSat")
        self["sup_url"] = Label("https://t.me/PomSat")

        self["line3"] = Label("")

        self["feed_label"] = Label("FEEDS CHANNELS")
        self["feed1_id"] = Label("@PomFeed")
        self["feed1_url"] = Label("https://t.me/PomFeed")
        self["feed2_id"] = Label("@FeedHunter")
        self["feed2_url"] = Label("https://t.me/FeedHunter")

        self["line4"] = Label("")

        self["yt_label"] = Label("YOUTUBE")
        self["yt_id"] = Label("@VUSOLO")
        self["yt_url"] = Label("https://www.youtube.com/@VUSOLO")

        self["line5"] = Label("")

        self["gh_label"] = Label("GITHUB")
        self["gh_id"] = Label("@Shr776")
        self["gh_url"] = Label("https://github.com/Shr776/PomBiss")

        self["line_bot"] = Label("")
        self["help"] = Label("Link 1/7  |  GREEN: Copy  |  RED: Close")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"],
            {
                "ok": self.copy_current,
                "green": self.copy_current,
                "cancel": self.close,
                "red": self.close,
                "menu": self.close,
                "up": self.prev_link,
                "down": self.next_link,
            },
            -1
        )

        self._highlight_current()

    def _highlight_current(self):
        reset_titles = [
            ("dev_label",  "DEVELOPER"),
            ("main_label", "MAIN CHANNEL"),
            ("sup_label",  "SUPPORT GROUP"),
            ("feed_label", "FEEDS CHANNELS"),
            ("yt_label",   "YOUTUBE"),
            ("gh_label",   "GITHUB"),
        ]
        for key, text in reset_titles:
            try:
                self[key].setText(text)
            except:
                pass

        current_title_map = {
            0: ("dev_label",  "DEVELOPER"),
            1: ("main_label", "MAIN CHANNEL"),
            2: ("sup_label",  "SUPPORT GROUP"),
            3: ("feed_label", "FEEDS CHANNELS"),
            4: ("feed_label", "FEEDS CHANNELS"),
            5: ("yt_label",   "YOUTUBE"),
            6: ("gh_label",   "GITHUB"),
        }

        try:
            key, text = current_title_map[self.current_index]
            self[key].setText("> " + text + " <")
        except:
            pass

        self["help"].setText("Link %d/7  |  GREEN: Copy  |  RED: Close" % (self.current_index + 1))

    def prev_link(self):
        self.current_index = (self.current_index - 1) % len(self.links)
        self._highlight_current()

    def next_link(self):
        self.current_index = (self.current_index + 1) % len(self.links)
        self._highlight_current()

    def copy_current(self):
        try:
            link = self.links[self.current_index]
            with open("/tmp/.pombiss_clipboard", "w") as f:
                f.write(link)
            self.session.open(
                MessageBox,
                "Link copied!\n\n%s" % link,
                MessageBox.TYPE_INFO,
                timeout=3
            )
        except Exception as e:
            self.session.open(
                MessageBox,
                "Copy error:\n%s" % str(e),
                MessageBox.TYPE_ERROR,
                timeout=4
            )


# ============================================================
# M3U MANAGER SCREEN
# ============================================================
class PomBissM3UManager(Screen):
    skin = '''
<screen name="PomBissM3UManager" position="center,center" size="1000,780"
        title="PomBiss M3U Manager" flags="wfNoBorder" backgroundColor="#0a0a1a">

    <widget name="line_top" position="50,20" size="900,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    
    <widget name="title" position="0,35" size="1000,60"
            font="Regular;36" transparent="1" foregroundColor="#00ff88"
            halign="center" valign="center" />
    
    <widget name="line_title" position="50,105" size="900,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    
    <widget name="status_label" position="100,125" size="280,40"
            font="Regular;22" transparent="1" foregroundColor="#8888aa"
            halign="left" valign="center" />
    <widget name="status_value" position="400,125" size="550,40"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    
    <widget name="feeds_label" position="100,170" size="280,40"
            font="Regular;22" transparent="1" foregroundColor="#8888aa"
            halign="left" valign="center" />
    <widget name="feeds_value" position="400,170" size="550,40"
            font="Regular;22" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    
    <widget name="files_label" position="100,215" size="280,40"
            font="Regular;22" transparent="1" foregroundColor="#8888aa"
            halign="left" valign="center" />
    <widget name="files_value" position="400,215" size="550,40"
            font="Regular;22" transparent="1" foregroundColor="#00ccff"
            halign="left" valign="center" />
    
    <widget name="lastfile_label" position="100,260" size="280,40"
            font="Regular;22" transparent="1" foregroundColor="#8888aa"
            halign="left" valign="center" />
    <widget name="lastfile_value" position="400,260" size="550,40"
            font="Regular;20" transparent="1" foregroundColor="#ffaa00"
            halign="left" valign="center" />

    <widget name="age_label" position="100,300" size="280,40"
            font="Regular;22" transparent="1" foregroundColor="#8888aa"
            halign="left" valign="center" />
    <widget name="age_value" position="400,300" size="550,40"
            font="Regular;20" transparent="1" foregroundColor="#ff8800"
            halign="left" valign="center" />
    
    <widget name="line_info_bot" position="50,350" size="900,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    
    <widget name="desc_title" position="0,365" size="1000,40"
            font="Regular;24" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    
    <widget name="desc_green" position="100,415" size="800,38"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="desc_yellow" position="100,463" size="800,38"
            font="Regular;22" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="desc_blue" position="100,511" size="800,38"
            font="Regular;22" transparent="1" foregroundColor="#00ccff"
            halign="left" valign="center" />
    <widget name="desc_red" position="100,559" size="800,38"
            font="Regular;22" transparent="1" foregroundColor="#ff4444"
            halign="left" valign="center" />
    
    <widget name="line_bot" position="50,610" size="900,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    
    <widget name="btn_green_bg" position="130,630" size="160,55"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="btn_green" position="130,630" size="160,55"
            font="Regular;24" transparent="1" foregroundColor="#000000"
            halign="center" valign="center" />
    
    <widget name="btn_yellow_bg" position="320,630" size="160,55"
            font="Regular;1" transparent="0" backgroundColor="#ffff00" />
    <widget name="btn_yellow" position="320,630" size="160,55"
            font="Regular;24" transparent="1" foregroundColor="#000000"
            halign="center" valign="center" />
    
    <widget name="btn_blue_bg" position="510,630" size="160,55"
            font="Regular;1" transparent="0" backgroundColor="#00ccff" />
    <widget name="btn_blue" position="510,630" size="160,55"
            font="Regular;24" transparent="1" foregroundColor="#000000"
            halign="center" valign="center" />
    
    <widget name="btn_red_bg" position="700,630" size="160,55"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />
    <widget name="btn_red" position="700,630" size="160,55"
            font="Regular;24" transparent="1" foregroundColor="#000000"
            halign="center" valign="center" />
    
    <widget name="files_list" position="100,705" size="800,60"
            font="Regular;18" transparent="1" foregroundColor="#cccccc"
            halign="center" valign="center" />

</screen>'''
    
    def __init__(self, session, parent=None):
        Screen.__init__(self, session)
        self.session = session
        self.parent = parent
        
        # ⭐ v5.6: چک auto-cleanup
        try:
            if check_and_auto_cleanup():
                log_debug("Auto-cleanup done at M3U Manager open")
        except Exception as e:
            log_debug("auto-cleanup error: %s" % str(e))
        
        self["line_top"] = Label("")
        self["title"] = Label("PomBiss M3U Manager")
        self["line_title"] = Label("")
        
        self["status_label"] = Label("Status:")
        self["status_value"] = Label("")
        self["feeds_label"] = Label("Feeds:")
        self["feeds_value"] = Label("")
        self["files_label"] = Label("Files:")
        self["files_value"] = Label("")
        self["lastfile_label"] = Label("Last File:")
        self["lastfile_value"] = Label("")
        self["age_label"] = Label("Age:")
        self["age_value"] = Label("")
        
        self["line_info_bot"] = Label("")
        self["desc_title"] = Label("Select an action:")
        self["desc_green"] = Label("")
        self["desc_yellow"] = Label("")
        self["desc_blue"] = Label("")
        self["desc_red"] = Label("")
        self["line_bot"] = Label("")
        
        self["btn_green_bg"] = Label("")
        self["btn_green"] = Label("")
        self["btn_yellow_bg"] = Label("")
        self["btn_yellow"] = Label("")
        self["btn_blue_bg"] = Label("")
        self["btn_blue"] = Label("")
        self["btn_red_bg"] = Label("")
        self["btn_red"] = Label("")
        
        self["files_list"] = Label("")
        
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "green": self._rebuild_m3u,
                "yellow": self._view_m3u,
                "blue": self._delete_m3u,
                "red": self.close,
                "cancel": self.close,
            },
            -1
        )
        
        self._refresh_status()
    
    def _refresh_status(self):
        try:
            self.has_services = os.path.exists(SERVICES_PATH)
            
            # ⭐ شمارش feeds از JSON
            self.feeds_count = count_services()
            
            all_files = get_all_m3u_files()
            self.files_count = len(all_files)
            self.has_m3u = self.files_count > 0            
            self.file_size = 0
            self.file_mtime = "-"
            self.last_filename = "-"
            
            if self.has_m3u:
                try:
                    last_file = all_files[0]
                    self.file_size = os.path.getsize(last_file)
                    mtime = datetime.fromtimestamp(os.path.getmtime(last_file))
                    self.file_mtime = mtime.strftime("%Y-%m-%d %H:%M:%S")
                    self.last_filename = os.path.basename(last_file)
                except:
                    pass
            
            if self.has_m3u:
                self["status_value"].setText("Files exist")
                try:
                    self["status_value"].instance.setForegroundColor(0x00ff88)
                except:
                    pass
            else:
                self["status_value"].setText("No M3U files")
                try:
                    self["status_value"].instance.setForegroundColor(0xff4444)
                except:
                    pass
            
            self["feeds_value"].setText(str(self.feeds_count))
            self["files_value"].setText(str(self.files_count))
            self["lastfile_value"].setText(self.last_filename)
            
            # ⭐ v5.6: نمایش سن JSON
            if self.has_services:
                age_hours = get_json_age_hours()
                if age_hours < 1:
                    age_str = "%.0f min" % (age_hours * 60)
                else:
                    age_str = "%.1f hours" % age_hours
                self["age_value"].setText("%s (auto-clean at %dh)" % (age_str, AUTO_CLEAN_HOURS))
            else:
                self["age_value"].setText("-")
            
            self["btn_green"].setText("REBUILD")
            self["btn_yellow"].setText("VIEW")
            self["btn_blue"].setText("DELETE ALL")
            self["btn_red"].setText("CLOSE")
            
            self["desc_green"].setText(
                "GREEN:  Create new M3U (timestamped)")
            self["desc_yellow"].setText(
                "YELLOW: View latest M3U content")
            self["desc_blue"].setText(
                "BLUE:   Delete ALL (M3U + services.json)")
            self["desc_red"].setText(
                "RED:    Close (no change)")
            
            if all_files:
                if len(all_files) <= 3:
                    names = [os.path.basename(f) for f in all_files]
                    self["files_list"].setText("Files: " + " | ".join(names))
                else:
                    names = [os.path.basename(f) for f in all_files[:3]]
                    self["files_list"].setText(
                        "Files: " + " | ".join(names) + " ... (+%d more)" % (len(all_files) - 3))
            else:
                self["files_list"].setText("")
            
        except Exception as e:
            log_debug("_refresh_status error: %s" % str(e))
    
    def _rebuild_m3u(self):
        log_debug("=== M3U Rebuild (timestamped) ===")
        
        if not self.has_services:
            self.session.open(
                MessageBox,
                "No searched feeds!\n\n"
                "First search feeds using SCAN button\n"
                "in the main plugin.",
                MessageBox.TYPE_ERROR,
                timeout=5
            )
            return
        
        try:
            with open(SERVICES_PATH, "r") as f:
                services = json.load(f)
            
            if not services:
                self.session.open(MessageBox, "No services found",
                                  MessageBox.TYPE_ERROR, timeout=5)
                return
            
            if not os.path.exists(M3U_DIR):
                os.makedirs(M3U_DIR)
            
            receiver_ip = self._get_receiver_ip()
            log_debug("receiver_ip = %s" % receiver_ip)
            
            new_path = get_timestamped_m3u_path()
            log_debug("New M3U path: %s" % new_path)
            
            count = 0
            with open(new_path, "w") as f:
                f.write("#EXTM3U\n")
                f.write("# PomBiss Plugin\n")
                f.write("# Date: %s\n" % datetime.now())
                f.write("# Telegram: https://t.me/VuSolo\n\n")
                
                for key, data in services.items():
                    service_ref = data.get("service_ref", "")
                    if not service_ref:
                        log_debug("SKIP: no service_ref for %s" % key)
                        continue
                    
                    # ⭐ URL-encode کردن ServiceReference
                    encoded_ref = quote(str(service_ref), safe='')
                    
                    stream_url = "http://%s:8001/%s" % (receiver_ip, encoded_ref)
                    
                    # ⭐ v5.6: اولویت display_name -> feed_id -> name
                    feed_name = (data.get("display_name", "").strip() or 
                                 data.get("feed_id", "").strip() or 
                                 data.get("name", key))
                    feed_name = str(feed_name).strip()
                    
                    f.write('#EXTINF:-1 group-title="PomBiss",%s\n' % feed_name)
                    f.write("#EXTVLCOPT:http-reconnect=true\n")
                    f.write("#EXTVLCOPT:network-caching=1000\n")
                    f.write("%s\n\n" % stream_url)
                    count += 1
                    log_debug("M3U entry %d: %s -> %s" % (count, feed_name, stream_url))
            
            try:
                with open(LAST_M3U_FILE, "w") as f:
                    f.write(new_path)
            except:
                pass
            
            cleanup_old_m3u_files(keep=3)
            
            log_debug("M3U created: %d feeds -> %s" % (count, new_path))
            
            self._refresh_status()
            
            filename = os.path.basename(new_path)
            
            self.session.open(
                MessageBox,
                "M3U Created!\n\n"
                "File:\n%s\n\n"
                "Feeds: %d\n"
                "Folder: %s\n\n"
                "In AJ Panel:\n"
                "1. Delete Cache\n"
                "2. Import the new file\n\n"
                "Old files auto-cleaned (keep 3)" % (
                    filename, count, M3U_DIR
                ),
                MessageBox.TYPE_INFO,
                timeout=15
            )
            
        except Exception as e:
            log_debug("_rebuild_m3u error: %s" % str(e))
            import traceback
            log_debug(traceback.format_exc())
            self.session.open(
                MessageBox,
                "Error: %s" % str(e),
                MessageBox.TYPE_ERROR,
                timeout=8
            )
    
    def _get_receiver_ip(self):
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            try:
                with open("/etc/enigma2/settings", "r") as f:
                    for line in f:
                        if line.startswith("config.network.ip"):
                            return line.split("=")[1].strip()
            except:
                pass
            return "127.0.0.1"
    
    def _view_m3u(self):
        log_debug("=== M3U View ===")
        
        if not self.has_m3u:
            self.session.open(
                MessageBox,
                "No M3U file found!\n\n"
                "Press GREEN to create one first.",
                MessageBox.TYPE_ERROR,
                timeout=5
            )
            return
        
        try:
            last_path = get_last_m3u_path()
            
            if not last_path:
                all_files = get_all_m3u_files()
                if all_files:
                    last_path = all_files[0]
            
            if not last_path or not os.path.exists(last_path):
                self.session.open(
                    MessageBox,
                    "No M3U file found",
                    MessageBox.TYPE_ERROR,
                    timeout=5
                )
                return
            
            with open(last_path, "r") as f:
                content = f.read()
            
            filename = os.path.basename(last_path)
            
            if len(content) > 1500:
                content = content[:1500] + "\n\n... (truncated)"
            
            self.session.open(
                MessageBox,
                "File: %s\n\n%s" % (filename, content),
                MessageBox.TYPE_INFO,
                timeout=25
            )
        except Exception as e:
            log_debug("_view_m3u error: %s" % str(e))
    
    def _delete_m3u(self):
        log_debug("=== M3U Delete All ===")
        
        all_files = get_all_m3u_files()
        count = len(all_files)
        
        has_services = os.path.exists(SERVICES_PATH)
        feeds_count = count_services()
        
        if count == 0 and not has_services:
            self.session.open(
                MessageBox,
                "Nothing to delete!\n\n"
                "No M3U files and no feeds list.",
                MessageBox.TYPE_INFO,
                timeout=5
            )
            return
        
        self.session.openWithCallback(
            self._delete_m3u_confirm,
            MessageBox,
            "Delete ALL M3U files + Feeds list?\n\n"
            "Folder: %s\n\n"
            "M3U files: %d\n"
            "Feeds list: %d entries\n\n"
            "This will reset ALL counters to 0\n"
            "and delete the services.json file.\n\n"
            "This cannot be undone!" % (
                M3U_DIR, count, feeds_count
            ),
            MessageBox.TYPE_YESNO
        )
    
    def _delete_m3u_confirm(self, answer):
        if not answer:
            log_debug("Delete cancelled")
            return
        
        try:
            deleted_m3u = 0
            deleted_other = 0
            
            # ⭐ 1. پاک کردن همه فایل‌های M3U
            all_files = get_all_m3u_files()
            for f in all_files:
                try:
                    os.remove(f)
                    log_debug("M3U deleted: %s" % f)
                    deleted_m3u += 1
                except:
                    pass
            
            # ⭐ 2. پاک کردن LAST_M3U_FILE
            try:
                if os.path.exists(LAST_M3U_FILE):
                    os.remove(LAST_M3U_FILE)
                    deleted_other += 1
            except:
                pass
            
            # ⭐ 3. پاک کردن M3U_PATH قدیمی
            try:
                if os.path.exists(M3U_PATH):
                    os.remove(M3U_PATH)
                    deleted_other += 1
            except:
                pass
            
            # ⭐ 4. پاک کردن فایل JSON (مهم!)
            try:
                if os.path.exists(SERVICES_PATH):
                    os.remove(SERVICES_PATH)
                    log_debug("SERVICES_PATH deleted: %s" % SERVICES_PATH)
                    deleted_other += 1
            except Exception as e:
                log_debug("delete SERVICES_PATH error: %s" % str(e))
            
            total = deleted_m3u + deleted_other
            
            if total > 0:
                self._refresh_status()
                
                self.session.open(
                    MessageBox,
                    "Deleted:\n"
                    "  M3U files: %d\n"
                    "  Other files: %d\n\n"
                    "All counters reset to 0.\n\n"
                    "Now you can search feeds again." % (
                        deleted_m3u, deleted_other
                    ),
                    MessageBox.TYPE_INFO,
                    timeout=6
                )
            else:
                self.session.open(
                    MessageBox,
                    "No files were deleted",
                    MessageBox.TYPE_ERROR,
                    timeout=5
                )
        except Exception as e:
            log_debug("_delete_m3u_confirm error: %s" % str(e))
            self.session.open(
                MessageBox,
                "Error: %s" % str(e),
                MessageBox.TYPE_ERROR,
                timeout=8
            )


# ============================================================
# SCREEN 1 - POMBISS LIST v5.6
# ============================================================
class PomBissList(Screen):
    PLUGIN_VERSION = updater.get_version()

    skinL = '''
<screen name="PomBissList" position="center,center" size="1920,1080" title="PomBiss" flags="wfNoBorder" backgroundColor="#0a0a1a">

    <widget source="global.CurrentTime" render="Label" position="1500,30" size="400,55"
            font="Regular;40" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center">
        <convert type="ClockToText">Format:%H:%M</convert>
    </widget>
    <widget source="global.CurrentTime" render="Label" position="1500,85" size="400,40"
            font="Regular;22" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center">
        <convert type="ClockToText">Format:%A, %d %B %Y</convert>
    </widget>

    <widget name="line_title_top" position="710,30" size="500,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    <ePixmap name="title_logo" position="860,40" size="200,80"
             pixmap="''' + plugin_dir + '''/PomBiss_logo.png"
             alphatest="on" zPosition="1" />
    <widget name="line_title_bot" position="710,125" size="500,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <widget name="version_label" position="50,98" size="780,30"
            font="Regular;18" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />

    <widget name="line_list_top" position="50,130" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <widget name="list_header" position="60,138" size="200,40"
            font="Regular;22" transparent="1" foregroundColor="#00ff00"
            halign="left" valign="center" />
    <widget name="feed_count" position="260,138" size="200,40"
            font="Regular;20" transparent="1" foregroundColor="#ffaa00"
            halign="left" valign="center" />
    <widget name="header_text" position="480,138" size="350,40"
            font="Regular;20" transparent="1" foregroundColor="#00ffff"
            halign="right" valign="center" />

    <widget name="line_list_bot" position="50,185" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <widget name="feed_num_1" position="55,200" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_1" position="180,200" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_1" position="480,200" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_1" position="680,200" size="160,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_2" position="55,260" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_2" position="180,260" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_2" position="480,260" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_2" position="680,260" size="160,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_3" position="55,320" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_3" position="180,320" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_3" position="480,320" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_3" position="680,320" size="160,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_4" position="55,380" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_4" position="180,380" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_4" position="480,380" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_4" position="680,380" size="160,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_5" position="55,440" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_5" position="180,440" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_5" position="480,440" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_5" position="680,440" size="160,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_6" position="55,500" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_6" position="180,500" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_6" position="480,500" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_6" position="680,500" size="160,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_7" position="55,560" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_7" position="180,560" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_7" position="480,560" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_7" position="680,560" size="160,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_8" position="55,620" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_8" position="180,620" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_8" position="480,620" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_8" position="680,620" size="160,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_9" position="55,680" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_9" position="180,680" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_9" position="480,680" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_9" position="680,680" size="160,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_10" position="55,740" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_10" position="180,740" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_10" position="480,740" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_10" position="680,740" size="160,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="line_page_top" position="50,820" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="page_counter" position="50,825" size="780,50"
            font="Regular;28" transparent="1" foregroundColor="#ffff00"
            halign="center" valign="center" />
    <widget name="line_page_bot" position="50,880" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <widget name="btn_red_bg" position="50,895" size="140,60"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />
    <widget name="key_red" position="50,895" size="140,60"
            font="Regular;22" transparent="1" foregroundColor="#000000"
            halign="center" valign="center" />

    <widget name="btn_green_bg" position="200,895" size="140,60"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="key_green" position="200,895" size="140,60"
            font="Regular;22" transparent="1" foregroundColor="#000000"
            halign="center" valign="center" />

    <widget name="btn_yellow_bg" position="350,895" size="140,60"
            font="Regular;1" transparent="0" backgroundColor="#ffff00" />
    <widget name="key_yellow" position="350,895" size="140,60"
            font="Regular;22" transparent="1" foregroundColor="#000000"
            halign="center" valign="center" />

    <widget name="btn_blue_bg" position="500,895" size="140,60"
            font="Regular;1" transparent="0" backgroundColor="#00ccff" />
    <widget name="key_blue" position="500,895" size="140,60"
            font="Regular;22" transparent="1" foregroundColor="#000000"
            halign="center" valign="center" />

    <widget name="btn_m3u_bg" position="650,895" size="140,60"
            font="Regular;1" transparent="0" backgroundColor="#9933ff" />
    <widget name="key_m3u" position="650,895" size="140,60"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />

    <widget name="line_buttons_bot" position="50,975" size="740,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <widget name="preview_glow_top" position="962,130" size="816,18"
            font="Regular;1" transparent="0" backgroundColor="#0088cc"
            zPosition="29" />
    <widget name="preview_glow_bot" position="962,582" size="816,18"
            font="Regular;1" transparent="0" backgroundColor="#0088cc"
            zPosition="29" />
    <widget name="preview_glow_left" position="959,130" size="18,470"
            font="Regular;1" transparent="0" backgroundColor="#0088cc"
            zPosition="29" />
    <widget name="preview_glow_right" position="1763,130" size="18,470"
            font="Regular;1" transparent="0" backgroundColor="#0088cc"
            zPosition="29" />

    <widget source="session.VideoPicture" render="Pig" 
            position="970,140" size="800,450" 
            zPosition="30" backgroundColor="transparent"/>

    <widget name="preview_border_top" position="970,138" size="800,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" zPosition="31" />
    <widget name="preview_border_bot" position="970,590" size="800,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" zPosition="31" />
    <widget name="preview_border_left" position="967,138" size="3,456"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" zPosition="31" />
    <widget name="preview_border_right" position="1767,138" size="3,456"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" zPosition="31" />

    <widget name="line_cat_top" position="860,600" size="1010,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />
    <widget name="label_category" position="860,605" size="1010,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_cat_bot" position="860,660" size="1010,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />

    <widget name="line_sat_top" position="960,670" size="810,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="label_satellite" position="960,675" size="810,45"
            font="Regular;28" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_sat_bot" position="960,720" size="810,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <widget name="line_freq_top" position="910,730" size="910,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    <widget name="label_frequency" position="910,735" size="910,45"
            font="Regular;26" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_freq_bot" position="910,780" size="910,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <widget name="line_id_top" position="910,790" size="910,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="label_id" position="910,795" size="910,45"
            font="Regular;28" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_id_bot" position="910,840" size="910,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <widget name="line_cw_top" position="860,850" size="1010,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />
    <widget name="label_cw" position="860,855" size="1010,55"
            font="Regular;32" transparent="1" foregroundColor="#00ff00"
            halign="center" valign="center" />
    <widget name="line_cw_bot" position="860,910" size="1010,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />

    <widget name="label_datetime" position="860,920" size="1010,30"
            font="Regular;20" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />

    <widget name="line_brand_top" position="960,965" size="810,2"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    <widget name="brand_label" position="960,970" size="810,30"
            font="Regular;24" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />
    <widget name="line_brand_bot" position="960,1002" size="810,2"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <widget name="nav_help" position="50,1030" size="780,40"
            font="Regular;18" transparent="1" foregroundColor="#dddddd"
            halign="center" valign="center" />

</screen>'''

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.skin = self.skinL

        global _pombiss_list_instance
        _pombiss_list_instance = self

        self.allfeeds = []
        self.current_index = 0
        self.page_start = 0
        self.feeds_per_page = 10

        self["myActionsMap"] = ActionMap(
            ["DirectionActions", "ColorActions", "OkCancelActions",
             "MenuActions", "HelpActions"],
            {
                "up": self.keyUp,
                "down": self.keyDown,
                "left": self.keyLeft,
                "right": self.keyRight,
                "ok": self.feedscanall,
                "green": self.feedscanall,
                "blue": self.clear_keys,
                "yellow": self.update_plugin,
                "red": self.cancel,
                "cancel": self.cancel,
                "menu": self.open_menu,
            },
            -1
        )

        for line in ["line_title_top", "line_title_bot",
                     "line_list_top", "line_list_bot",
                     "line_page_top", "line_page_bot",
                     "line_buttons_bot",
                     "preview_glow_top", "preview_glow_bot",
                     "preview_glow_left", "preview_glow_right",
                     "preview_border_top", "preview_border_bot",
                     "preview_border_left", "preview_border_right",
                     "line_cat_top", "line_cat_bot",
                     "line_sat_top", "line_sat_bot",
                     "line_freq_top", "line_freq_bot",
                     "line_id_top", "line_id_bot",
                     "line_cw_top", "line_cw_bot",
                     "line_brand_top", "line_brand_bot"]:
            self[line] = Label("")

        self["title_logo"] = Pixmap()
        self["list_header"] = Label("FEED LIST")
        self["feed_count"] = Label("")
        self["header_text"] = Label("PomBiss Feed Viewer")
        self["page_counter"] = Label("[1/1]")
        self["brand_label"] = Label("@VUSOLO")

        self["version_label"] = Label("PomBiss Plugin v%s" % self.PLUGIN_VERSION)

        for i in range(1, 11):
            self["feed_num_%d" % i] = Label("")
            self["feed_sat_%d" % i] = Label("")
            self["feed_freq_%d" % i] = Label("")
            self["feed_id_%d" % i] = Label("")

        self["label_category"] = Label("")
        self["label_satellite"] = Label("")
        self["label_frequency"] = Label("")
        self["label_id"] = Label("")
        self["label_cw"] = Label("")
        self["label_datetime"] = Label("")

        self["preview_glow_top"] = Label("")
        self["preview_glow_bot"] = Label("")
        self["preview_glow_left"] = Label("")
        self["preview_glow_right"] = Label("")

        self["preview_border_top"] = Label("")
        self["preview_border_bot"] = Label("")
        self["preview_border_left"] = Label("")
        self["preview_border_right"] = Label("")

        self["btn_red_bg"] = Label("")
        self["btn_green_bg"] = Label("")
        self["btn_yellow_bg"] = Label("")
        self["btn_blue_bg"] = Label("")
        self["btn_m3u_bg"] = Label("")

        self["key_red"] = Label("EXIT")
        self["key_green"] = Label("SCAN")
        self["key_yellow"] = Label("Update")
        self["key_blue"] = Label("Clear")
        self["key_m3u"] = Label("M3U")

        self["nav_help"] = Label(
            "Up/Down: Select  |  OK: Scan  |  MENU: Options  |  M3U: Export"
        )

        # ⭐ v5.6: چک auto-cleanup موقع باز شدن پلاگین
        try:
            if check_and_auto_cleanup():
                log_debug("Auto-cleanup done at PomBissList open")
        except Exception as e:
            log_debug("auto-cleanup error: %s" % str(e))

        self.onLayoutFinish.append(self.download_feeds)

    def open_menu(self):
        log_debug("=== open_menu (MENU) ===")
        
        menu_list = [
            ("Contact Us", "contact"),
            ("M3U Manager", "m3u"),
        ]
        
        self.session.openWithCallback(
            self._menu_callback,
            ChoiceBox,
            title="PomBiss Options",
            list=menu_list
        )

    def _menu_callback(self, answer):
        if not answer:
            log_debug("Menu cancelled")
            return
        
        try:
            choice = answer[1]
            log_debug("Menu choice: %s" % choice)
            
            if choice == "contact":
                self.session.open(PomBissContactScreen)
            elif choice == "m3u":
                self.m3u_manager()
        except Exception as e:
            log_debug("_menu_callback error: %s" % str(e))

    def m3u_manager(self):
        log_debug("=== Opening M3U Manager Screen ===")
        self.session.open(PomBissM3UManager, parent=self)

    def download_feeds(self):
        try:
            log_debug("=== download_feeds START ===")
            self["label_category"].setText(_("Downloading..."))

            response = requests.get(FEEDS_URL, timeout=15)
            if response.status_code != 200:
                self["label_category"].setText(_("Error: HTTP %s") % response.status_code)
                return

            content = response.text
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            if not lines:
                self["label_category"].setText(_("No feeds available"))
                return

            def get_datetime_key(line):
                parts = line.split("=")
                if len(parts) > 8:
                    return parts[8].strip()
                return ""

            lines.sort(key=get_datetime_key, reverse=True)
            self.allfeeds = lines
            self.current_index = 0
            self.page_start = 0
            total = len(self.allfeeds)
            self["feed_count"].setText("[%d Feeds]" % total)
            log_debug("Loaded %d feeds" % total)
            self.update_list()
            self.update_details()

        except Exception as exc:
            log_debug("download error: %s" % str(exc))

    def update_list(self):
        if not self.allfeeds:
            return

        total = len(self.allfeeds)
        page_num = (self.page_start // self.feeds_per_page) + 1
        total_pages = (total + self.feeds_per_page - 1) // self.feeds_per_page
        self["page_counter"].setText("[%d/%d]" % (page_num, total_pages))

        for i in range(1, 11):
            feed_idx = self.page_start + i - 1

            if feed_idx < total:
                line = self.allfeeds[feed_idx]
                parts = line.split("=")

                freq_parts = parts[0].strip().split()
                freq = freq_parts[1] if len(freq_parts) > 1 else ""
                pol = freq_parts[2] if len(freq_parts) > 2 else ""
                sr = freq_parts[3] if len(freq_parts) > 3 else ""

                sat_label = parts[3].strip() if len(parts) > 3 else ""
                feed_id = parts[5].strip() if len(parts) > 5 else ""

                if not sat_label or sat_label == "0":
                    sat_pos = freq_parts[0] if len(freq_parts) > 0 else ""
                    sat_label = POSITION_FIX.get(sat_pos, sat_label)

                if feed_idx == self.current_index:
                    self["feed_num_%d" % i].setText(">[%d]" % (feed_idx + 1))
                    self["feed_sat_%d" % i].setText(sat_label)
                    self["feed_freq_%d" % i].setText("%s %s %s" % (freq, pol, sr))
                    self["feed_id_%d" % i].setText(feed_id)
                    try:
                        self["feed_num_%d" % i].instance.setForegroundColor(0xffff00)
                        self["feed_sat_%d" % i].instance.setForegroundColor(0xffff00)
                        self["feed_freq_%d" % i].instance.setForegroundColor(0xffff00)
                        self["feed_id_%d" % i].instance.setForegroundColor(0xffff00)
                    except:
                        pass
                else:
                    self["feed_num_%d" % i].setText(" [%d]" % (feed_idx + 1))
                    self["feed_sat_%d" % i].setText(sat_label)
                    self["feed_freq_%d" % i].setText("%s %s %s" % (freq, pol, sr))
                    self["feed_id_%d" % i].setText(feed_id)
                    try:
                        self["feed_num_%d" % i].instance.setForegroundColor(0xffff00)
                        self["feed_sat_%d" % i].instance.setForegroundColor(0x00ff88)
                        self["feed_freq_%d" % i].instance.setForegroundColor(0x00aaff)
                        self["feed_id_%d" % i].instance.setForegroundColor(0xffffff)
                    except:
                        pass
            else:
                self["feed_num_%d" % i].setText("")
                self["feed_sat_%d" % i].setText("")
                self["feed_freq_%d" % i].setText("")
                self["feed_id_%d" % i].setText("")

    def update_details(self):
        if not self.allfeeds:
            return
        if self.current_index >= len(self.allfeeds):
            return

        line = self.allfeeds[self.current_index]
        parts = [p.strip() for p in line.split("=")]
        while len(parts) < 9:
            parts.append("")

        freq_parts = parts[0].split()
        freq = freq_parts[1] if len(freq_parts) > 1 else ""
        pol = freq_parts[2] if len(freq_parts) > 2 else ""
        sr = freq_parts[3] if len(freq_parts) > 3 else ""

        cw_key = parts[1] if len(parts) > 1 else ""
        title = parts[2] if len(parts) > 2 else ""
        sat_label = parts[3] if len(parts) > 3 else ""
        feed_id = parts[5] if len(parts) > 5 else ""
        feed_datetime = parts[8] if len(parts) > 8 else ""

        if not sat_label or sat_label == "0":
            sat_pos = freq_parts[0] if len(freq_parts) > 0 else ""
            sat_label = POSITION_FIX.get(sat_pos, sat_label)

        self["label_category"].setText("# " + title)
        self["label_satellite"].setText(sat_label)
        self["label_frequency"].setText("Frequency: %s %s %s" % (freq, pol, sr))
        self["label_id"].setText("ID: %s" % feed_id)
        self["label_cw"].setText("CW: %s" % cw_key)
        self["label_datetime"].setText(feed_datetime)

    def keyUp(self):
        if self.current_index > 0:
            self.current_index -= 1
            if self.current_index < self.page_start:
                self.page_start -= self.feeds_per_page
            self.update_list()
            self.update_details()

    def keyDown(self):
        if self.current_index < len(self.allfeeds) - 1:
            self.current_index += 1
            if self.current_index >= self.page_start + self.feeds_per_page:
                self.page_start += self.feeds_per_page
            self.update_list()
            self.update_details()

    def keyLeft(self):
        if self.page_start >= self.feeds_per_page:
            self.page_start -= self.feeds_per_page
            self.current_index = self.page_start
            self.update_list()
            self.update_details()

    def keyRight(self):
        if self.page_start + self.feeds_per_page < len(self.allfeeds):
            self.page_start += self.feeds_per_page
            self.current_index = self.page_start
            self.update_list()
            self.update_details()

    def refresh(self):
        self.download_feeds()

    def feedscanall(self):
        if not self.allfeeds:
            return
        feed = self._parse_current_feed()
        if not feed:
            self.session.open(MessageBox, _("Invalid feed data"),
                              MessageBox.TYPE_ERROR, timeout=5)
            return
        signalfinder.open_signal_finder(self.session, feed)

    def update_plugin(self):
        log_debug("Manual update check triggered")
        updater.check_for_update(self.session, silent_if_no_update=False)

    def clear_keys(self):
        msg = (
            "Delete PomBiss + Live Feed keys from SoftCam.Key?\n\n"
            "Only keys ending with:\n"
            "  \"; Edited by PomBiss\"\n"
            "  \"added by LIVE FEED\"\n"
            "will be removed.\n\n"
            "Other keys (manual, ...) will NOT be touched.\n\n"
            "A backup will be created as SoftCam.Key.bak.pombiss\n\n"
            "Are you sure?"
        )
        self.session.openWithCallback(
            self._clear_keys_confirmed,
            MessageBox,
            msg,
            MessageBox.TYPE_YESNO
        )

    def _clear_keys_confirmed(self, answer):
        if not answer:
            log_debug("Clear keys cancelled by user")
            return

        log_debug("Clear keys confirmed - starting")

        try:
            ok, removed, message = _clear_pombiss_keys()
        except Exception as e:
            log_debug("clear_keys error: %s" % str(e))
            self.session.open(MessageBox, "Error: %s" % str(e),
                              MessageBox.TYPE_ERROR, timeout=8)
            return

        if not ok:
            self.session.open(MessageBox, "Failed: %s" % message,
                              MessageBox.TYPE_ERROR, timeout=8)
            return

        if removed == 0:
            self.session.open(MessageBox,
                              "No PomBiss or Live Feed keys found",
                              MessageBox.TYPE_INFO, timeout=5)
            return

        success_msg = "%d keys removed successfully" % removed
        log_debug(success_msg)

        try:
            result = _restart_emulator_after_clear()
            log_debug("Emulator restart after clear: %s" % result)
            if result:
                success_msg += "\n\nEmulator restarted."
            else:
                success_msg += "\n\nNote: emulator not restarted automatically."
        except Exception as e:
            log_debug("emulator restart error: %s" % str(e))

        self.session.open(MessageBox, success_msg,
                          MessageBox.TYPE_INFO, timeout=8)

    def _parse_current_feed(self):
        try:
            if self.current_index >= len(self.allfeeds):
                return None
            line = self.allfeeds[self.current_index]
            parts = [p.strip() for p in line.split("=")]
            while len(parts) < 9:
                parts.append("")
            freq_parts = parts[0].split()
            if len(freq_parts) < 4:
                return None
            return {
                "position": freq_parts[0],
                "freq": freq_parts[1],
                "pol": freq_parts[2],
                "sr": freq_parts[3],
                "cw": parts[1].replace(" ", "").upper(),
                "name": parts[2] if len(parts) > 2 else "",
                "sat": parts[3] if len(parts) > 3 else "",
                "feed_id": parts[5] if len(parts) > 5 else "",
            }
        except Exception as e:
            log_debug("parse error: %s" % str(e))
            return None

    def cancel(self):
        self.close()


# ============================================================
# Entry point
# ============================================================
def _do_safe_restart(session):
    global _restart_timer

    log_debug("=== SAFE RESTART via TryQuitMainloop ===")

    try:
        if os.path.exists(RESTART_FLAG):
            os.remove(RESTART_FLAG)
    except:
        pass

    session.open(
        MessageBox,
        "Update installed successfully!\n\n"
        "Enigma2 will now restart.",
        MessageBox.TYPE_INFO,
        timeout=3
    )

    def do_restart():
        log_debug("Calling TryQuitMainloop(3)")
        try:
            session.open(TryQuitMainloop, 3)
        except Exception as e:
            log_debug("TryQuitMainloop error: %s" % str(e))

    _restart_timer = eTimer()
    try:
        _restart_timer.timeout.connect(do_restart)
    except:
        _restart_timer.callback.append(do_restart)
    _restart_timer.start(3500, True)


def _open_pombiss_list(session):
    log_debug("=== _open_pombiss_list ===")

    if os.path.exists(RESTART_FLAG):
        log_debug("RESTART FLAG found -> restarting via TryQuitMainloop")
        _do_safe_restart(session)
        return

    def open_plugin():
        session.open(PomBissList)

    updater.check_for_update(
        session,
        silent_if_no_update=True,
        on_no_update=open_plugin
    )


def main(session, **kwargs):
    log_debug("=== main called ===")
    registration.check_registration(
        session,
        on_success=lambda: _open_pombiss_list(session),
        on_cancel=lambda: log_debug("Registration cancelled by user")
    )


def Plugins(**kwargs):
    return PluginDescriptor(
        name="PomBiss",
        description="Sports Feed Viewer",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="PomBiss_logo.png",
        fnc=main
    )