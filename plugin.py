#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
PomBiss Plugin for Enigma2 v4.3
Sports Feed Viewer - Neon Dual Panel Theme
+ LIVE PIP PREVIEW (800 × 450 - دقیق 16:9)
+ RGB-ordered buttons (EXIT, SCAN, Update, Clear)
+ All elements inside 1080p screen
+ Focus on text content (PIP reduced to 800×450)
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


# ============================================================
# Clear PomBiss Keys - توابع
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
        self["title"] = Label("📞 PomBiss Contact Us")
        self["line_title"] = Label("")

        self["dev_label"] = Label("👤 DEVELOPER")
        self["dev_id"] = Label("@Shr776")
        self["dev_url"] = Label("https://t.me/Shr776")

        self["line1"] = Label("")

        self["main_label"] = Label("📢 MAIN CHANNEL")
        self["main_id"] = Label("@VuSolo")
        self["main_url"] = Label("https://t.me/VuSolo")

        self["line2"] = Label("")

        self["sup_label"] = Label("💬 SUPPORT GROUP")
        self["sup_id"] = Label("@PomSat")
        self["sup_url"] = Label("https://t.me/PomSat")

        self["line3"] = Label("")

        self["feed_label"] = Label("📡 FEEDS CHANNELS")
        self["feed1_id"] = Label("@PomFeed")
        self["feed1_url"] = Label("https://t.me/PomFeed")
        self["feed2_id"] = Label("@FeedHunter")
        self["feed2_url"] = Label("https://t.me/FeedHunter")

        self["line4"] = Label("")

        self["yt_label"] = Label("🎬 YOUTUBE")
        self["yt_id"] = Label("@VUSOLO")
        self["yt_url"] = Label("https://www.youtube.com/@VUSOLO")

        self["line5"] = Label("")

        self["gh_label"] = Label("💻 GITHUB")
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
            ("dev_label",  "👤 DEVELOPER"),
            ("main_label", "📢 MAIN CHANNEL"),
            ("sup_label",  "💬 SUPPORT GROUP"),
            ("feed_label", "📡 FEEDS CHANNELS"),
            ("yt_label",   "🎬 YOUTUBE"),
            ("gh_label",   "💻 GITHUB"),
        ]
        for key, text in reset_titles:
            try:
                self[key].setText(text)
            except:
                pass

        current_title_map = {
            0: ("dev_label",  "👤 DEVELOPER"),
            1: ("main_label", "📢 MAIN CHANNEL"),
            2: ("sup_label",  "💬 SUPPORT GROUP"),
            3: ("feed_label", "📡 FEEDS CHANNELS"),
            4: ("feed_label", "📡 FEEDS CHANNELS"),
            5: ("yt_label",   "🎬 YOUTUBE"),
            6: ("gh_label",   "💻 GITHUB"),
        }

        try:
            key, text = current_title_map[self.current_index]
            self[key].setText("▶ " + text + " ◀")
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
                "✅ Link copied!\n\n%s" % link,
                MessageBox.TYPE_INFO,
                timeout=3
            )
        except Exception as e:
            self.session.open(
                MessageBox,
                "❌ Copy error:\n%s" % str(e),
                MessageBox.TYPE_ERROR,
                timeout=4
            )


# ============================================================
# SCREEN 1 - POMBISS LIST v4.3 (PIP 800×450)
# ============================================================
class PomBissList(Screen):
    """صفحه لیست فیدها - v4.3 با PIP 800×450 (نسبت دقیق 16:9)"""

    PLUGIN_VERSION = updater.get_version()

    skinL = '''
<screen name="PomBissList" position="center,center" size="1920,1080" title="PomBiss" flags="wfNoBorder" backgroundColor="#0a0a1a">

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- HEADER -->
    <!-- ═══════════════════════════════════════════════════════ -->
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

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- LEFT PANEL: FEED LIST -->
    <!-- ═══════════════════════════════════════════════════════ -->
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

    <!-- Page counter -->
    <widget name="line_page_top" position="50,820" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="page_counter" position="50,825" size="780,50"
            font="Regular;28" transparent="1" foregroundColor="#ffff00"
            halign="center" valign="center" />
    <widget name="line_page_bot" position="50,880" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- BUTTONS - RGB Order -->
    <!-- ═══════════════════════════════════════════════════════ -->
    <widget name="btn_red_bg" position="60,895" size="180,60"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />
    <widget name="key_red" position="60,895" size="180,60"
            font="Regular;28" transparent="1" foregroundColor="#000000"
            halign="center" valign="center" />

    <widget name="btn_green_bg" position="260,895" size="180,60"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="key_green" position="260,895" size="180,60"
            font="Regular;28" transparent="1" foregroundColor="#000000"
            halign="center" valign="center" />

    <widget name="btn_yellow_bg" position="460,895" size="180,60"
            font="Regular;1" transparent="0" backgroundColor="#ffff00" />
    <widget name="key_yellow" position="460,895" size="180,60"
            font="Regular;28" transparent="1" foregroundColor="#000000"
            halign="center" valign="center" />

    <widget name="btn_blue_bg" position="660,895" size="180,60"
            font="Regular;1" transparent="0" backgroundColor="#00ccff" />
    <widget name="key_blue" position="660,895" size="180,60"
            font="Regular;28" transparent="1" foregroundColor="#000000"
            halign="center" valign="center" />

    <widget name="line_buttons_bot" position="50,975" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- RIGHT PANEL: LIVE PIP PREVIEW (800 × 450 - 16:9 دقیق) -->
    <!-- ═══════════════════════════════════════════════════════ -->
    <widget source="session.VideoPicture" render="Pig" 
            position="970,140" size="800,450" 
            zPosition="30" backgroundColor="transparent"/>

    <!-- حاشیه‌های کادر Preview -->
    <widget name="preview_border_top" position="970,138" size="800,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" zPosition="31" />
    <widget name="preview_border_bot" position="970,590" size="800,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" zPosition="31" />
    <widget name="preview_border_left" position="967,138" size="3,456"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" zPosition="31" />
    <widget name="preview_border_right" position="1767,138" size="3,456"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" zPosition="31" />

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- RIGHT PANEL: FEED DETAILS -->
    <!-- ═══════════════════════════════════════════════════════ -->
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

    <!-- Footer navigation help -->
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
                "menu": self.show_contact,
                "help": self.show_contact,
                "info": self.show_contact,
            },
            -1
        )

        for line in ["line_title_top", "line_title_bot",
                     "line_list_top", "line_list_bot",
                     "line_page_top", "line_page_bot",
                     "line_buttons_bot",
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

        self["preview_border_top"] = Label("")
        self["preview_border_bot"] = Label("")
        self["preview_border_left"] = Label("")
        self["preview_border_right"] = Label("")

        self["btn_red_bg"] = Label("")
        self["btn_green_bg"] = Label("")
        self["btn_yellow_bg"] = Label("")
        self["btn_blue_bg"] = Label("")

        self["key_red"] = Label("EXIT")
        self["key_green"] = Label("SCAN")
        self["key_yellow"] = Label("Update")
        self["key_blue"] = Label("Clear")

        self["nav_help"] = Label(
            "Up/Down: Select  |  Left/Right: Page  |  OK: Scan  |  MENU: Contact"
        )

        self.onLayoutFinish.append(self.download_feeds)

    def show_contact(self):
        log_debug("Opening contact screen (MENU)")
        self.session.open(PomBissContactScreen)

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
                    self["feed_num_%d" % i].setText("▶[%d]" % (feed_idx + 1))
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
                    self["feed_num_%d" % i].setText("   [%d]" % (feed_idx + 1))
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

        success_msg = "✅ %d keys removed successfully" % removed
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
# نقطه ورود پلاگین
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
        "✅ Update installed successfully!\n\n"
        "🔄 Enigma2 will now restart.",
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
