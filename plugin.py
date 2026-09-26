#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
PomBiss Plugin for Enigma2
Sports Feed Viewer - Neon Dual Panel Theme
"""

from __future__ import print_function

try:
    from . import _
except:
    pass

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.ActionMap import ActionMap
from enigma import getDesktop
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

import requests
import time

plugin_dir = resolveFilename(SCOPE_PLUGINS, "Extensions/PomBiss")
FEEDS_URL = "https://raw.githubusercontent.com/Shr776/PomBissFeeds/main/feeds.txt"

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
    """نوشتن لاگ توی فایل"""
    try:
        with open("/tmp/PomBissSatfinder.log", "a") as f:
            f.write("[PomBiss] %s\n" % msg)
    except:
        pass


# اصلاح موقعیت‌های ناقص
POSITION_FIX = {
    "31": "Eutelsat 3C ( 3.1E )",
    "216": "Eutelsat 21C ( 21.6E )",
}


# ============================================================
# SCREEN 1 - POMBISS LIST (صفحه لیست فیدها)
# ============================================================

class PomBissList(Screen):
    """صفحه لیست فیدها - دو پنل"""

    skinL = '''
<screen name="PomBissList" position="center,center" size="1920,1080" title="PomBiss" flags="wfNoBorder" backgroundColor="#0a0a1a">

    <!-- ============ عنوان بالا ============ -->
    <widget name="line_title_top" position="710,30" size="500,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    <widget name="title" position="710,35" size="500,50"
            font="Regular;38" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />
    <widget name="line_title_bot" position="710,90" size="500,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <!-- ============ کادر لیست (چپ) ============ -->
    <widget name="line_list_top" position="50,130" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="list_header" position="180,138" size="400,40"
            font="Regular;24" transparent="1" foregroundColor="#00ff00"
            halign="center" valign="center" />
    <widget name="today_date" position="600,138" size="230,40"
            font="Regular;18" transparent="1" foregroundColor="#ffff00"
            halign="right" valign="center" />
    <widget name="line_list_bot" position="50,185" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <!-- ============ 10 خط لیست ============ -->

    <!-- خط 1 -->
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

    <!-- خط 2 -->
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

    <!-- خط 3 -->
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

    <!-- خط 4 -->
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

    <!-- خط 5 -->
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

    <!-- خط 6 -->
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

    <!-- خط 7 -->
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

    <!-- خط 8 -->
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

    <!-- خط 9 -->
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

    <!-- خط 10 -->
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

    <!-- ============ شماره صفحه ============ -->
    <widget name="line_page_top" position="50,820" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="page_counter" position="50,825" size="780,50"
            font="Regular;28" transparent="1" foregroundColor="#ffff00"
            halign="center" valign="center" />
    <widget name="line_page_bot" position="50,880" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <!-- ============ کادر جزئیات (راست) ============ -->
    <widget name="line_cat_top" position="860,280" size="1010,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />
    <widget name="label_category" position="860,285" size="1010,90"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_cat_bot" position="860,380" size="1010,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />

    <widget name="line_sat_top" position="960,400" size="810,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="label_satellite" position="960,405" size="810,55"
            font="Regular;28" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_sat_bot" position="960,465" size="810,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <widget name="line_freq_top" position="910,485" size="910,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    <widget name="label_frequency" position="910,490" size="910,55"
            font="Regular;26" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_freq_bot" position="910,550" size="910,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <widget name="line_id_top" position="910,570" size="910,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="label_id" position="910,575" size="910,55"
            font="Regular;28" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_id_bot" position="910,635" size="910,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <widget name="line_cw_top" position="860,655" size="1010,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />
    <widget name="label_cw" position="860,660" size="1010,60"
            font="Regular;32" transparent="1" foregroundColor="#00ff00"
            halign="center" valign="center" />
    <widget name="line_cw_bot" position="860,725" size="1010,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />

    <widget name="label_datetime" position="860,740" size="1010,40"
            font="Regular;20" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />

    <!-- ============ دکمه‌ها ============ -->
    <widget name="btn_red_bg" position="1150,850" size="160,55"
            font="Regular;1" transparent="0" backgroundColor="#cc0000" />
    <widget name="key_red" position="1150,850" size="160,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />

    <widget name="btn_green_bg" position="1330,850" size="160,55"
            font="Regular;1" transparent="0" backgroundColor="#00cc00" />
    <widget name="key_green" position="1330,850" size="160,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />

    <widget name="btn_yellow_bg" position="1510,850" size="160,55"
            font="Regular;1" transparent="0" backgroundColor="#cccc00" />
    <widget name="key_yellow" position="1510,850" size="160,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />

    <widget name="nav_help" position="50,940" size="1820,40"
            font="Regular;18" transparent="1" foregroundColor="#888888"
            halign="center" valign="center" />

</screen>'''

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.skin = self.skinL

        self.allfeeds = []
        self.current_index = 0
        self.page_start = 0
        self.feeds_per_page = 10

        self["myActionsMap"] = ActionMap(
            ["SetupActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.feedscanall,
                "green": self.feedscanall,
                "red": self.refresh,
                "cancel": self.cancel,
                "up": self.keyUp,
                "down": self.keyDown,
                "left": self.keyLeft,
                "right": self.keyRight,
            },
            -1
        )

        for line in ["line_title_top", "line_title_bot",
                     "line_list_top", "line_list_bot",
                     "line_page_top", "line_page_bot",
                     "line_cat_top", "line_cat_bot",
                     "line_sat_top", "line_sat_bot",
                     "line_freq_top", "line_freq_bot",
                     "line_id_top", "line_id_bot",
                     "line_cw_top", "line_cw_bot"]:
            self[line] = Label("")

        self["title"] = Label("PomBiss")
        self["list_header"] = Label("FEED LIST")
        self["today_date"] = Label("")
        self["page_counter"] = Label("[1/1]")

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

        self["btn_red_bg"] = Label("")
        self["btn_green_bg"] = Label("")
        self["btn_yellow_bg"] = Label("")
        self["key_red"] = Label("FEED")
        self["key_green"] = Label("SCAN")
        self["key_yellow"] = Label("DVB")

        self["nav_help"] = Label("Up/Down: Select  |  Left/Right: Page  |  OK: Open")

        self.onLayoutFinish.append(self.download_feeds)
        
    def download_feeds(self):
        try:
            log_debug("=== download_feeds START ===")

            self["label_category"].setText(_("Downloading..."))
            self["today_date"].setText(time.strftime("%Y-%m-%d  %H:%M"))

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

            log_debug("Loaded %d feeds" % len(lines))

            self.update_list()
            self.update_details()

        except Exception as exc:
            log_debug("download error: %s" % str(exc))

    def update_list(self):
        """پر کردن ۱۰ خط لیست با رنگ‌بندی و انتخاب‌شده"""
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
        """نمایش جزئیات فید انتخاب‌شده"""
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
        """باز کردن Satfinder با فرکانس فید"""
        if not self.allfeeds:
            return

        log_debug("=== feedscanall START ===")

        try:
            line = self.allfeeds[self.current_index]
            parts = [p.strip() for p in line.split("=")]
            freq_parts = parts[0].split()

            if len(freq_parts) < 4:
                log_debug("Not enough freq parts")
                return

            self.pending_freq = int(freq_parts[1])
            self.pending_pol = freq_parts[2].upper()
            self.pending_sr = int(freq_parts[3])

            sat_pos = freq_parts[0]
            log_debug("sat_pos raw: '%s'" % sat_pos)
            try:
                clean = sat_pos.replace("E", "").replace("W", "").replace("°", "").strip()
                log_debug("sat_pos clean: '%s'" % clean)

                if clean.isdigit() or (clean.startswith("-") and clean[1:].isdigit()):
                    self.pending_orb = int(clean)
                    log_debug("orb (pure number): %d" % self.pending_orb)
                else:
                    deg = float(clean)
                    if "W" in sat_pos.upper():
                        deg = -deg
                    self.pending_orb = int(deg * 10)
                    log_debug("deg: %f, orb: %d" % (deg, self.pending_orb))
            except Exception as e:
                log_debug("orb parse error: %s" % str(e))
                self.pending_orb = 130

            log_debug("Feed: %d %s %d @ orb %d" % (
                self.pending_freq, self.pending_pol,
                self.pending_sr, self.pending_orb))

        except Exception as e:
            log_debug("parse error: %s" % str(e))
            return

        # باز کردن Satfinder
        try:
            from Plugins.SystemPlugins.Satfinder.plugin import SatfinderExtra
            self.session.open(SatfinderExtra)
            log_debug("SatfinderExtra opened")
            self.start_retune()
            return
        except Exception as e:
            log_debug("SatfinderExtra error: %s" % str(e))

        try:
            from Plugins.SystemPlugins.Satfinder.plugin import SatfinderMain
            SatfinderMain(self.session)
            log_debug("SatfinderMain opened")
            self.start_retune()
            return
        except Exception as e:
            log_debug("SatfinderMain error: %s" % str(e))

        try:
            from Plugins.SystemPlugins.Satfinder.plugin import Satfinder
            self.session.open(Satfinder)
            log_debug("Satfinder opened")
            self.start_retune()
            return
        except Exception as e:
            log_debug("Satfinder error: %s" % str(e))

        self.session.open(
            MessageBox,
            _("Satfinder not found"),
            MessageBox.TYPE_ERROR,
            timeout=10
        )

    def start_retune(self):
        """شروع تایمر برای retune"""
        log_debug("Starting retune timer (2s)")
        from enigma import eTimer
        self.retune_timer = eTimer()
        try:
            self.retune_timer.callback.append(self.do_retune)
        except:
            self.retune_timer.timeout.connect(self.do_retune)
        self.retune_timer.start(2000, True)

    def do_retune(self):
        """تنظیم Tuner"""
        try:
            log_debug("=== do_retune START ===")

            from enigma import eDVBFrontendParametersSatellite
            from enigma import eDVBResourceManager
            from Components.NimManager import nimmanager

            nim_slot = int(config.plugins.PomBiss.nimnum.value)
            frontend = None

            try:
                rm = eDVBResourceManager.getInstance()
                if rm:
                    frontend = rm.getFrontend(nim_slot, 0)
                    log_debug("Got frontend via rm.getFrontend")
            except Exception as e:
                log_debug("rm.getFrontend error: %s" % str(e))

            if frontend is None:
                try:
                    frontend = nimmanager.getFrontend(nim_slot)
                    log_debug("Got frontend via nimmanager.getFrontend")
                except Exception as e:
                    log_debug("nimmanager.getFrontend error: %s" % str(e))

            if frontend is None:
                log_debug("Frontend is None, fallback to retuneSat")
                current = self.session.current_dialog
                if current and hasattr(current, 'retuneSat'):
                    try:
                        current.retuneSat()
                        log_debug("retuneSat() fallback OK")
                    except:
                        pass
                return

            tp = eDVBFrontendParametersSatellite()
            tp.frequency = self.pending_freq * 1000
            tp.symbol_rate = self.pending_sr * 1000
            tp.polarization = (
                eDVBFrontendParametersSatellite.Polarisation_Horizontal
                if self.pending_pol == "H"
                else eDVBFrontendParametersSatellite.Polarisation_Vertical
            )
            tp.fec = eDVBFrontendParametersSatellite.FEC_Auto
            tp.inversion = eDVBFrontendParametersSatellite.Inversion_Unknown
            tp.system = eDVBFrontendParametersSatellite.System_DVB_S2
            tp.modulation = eDVBFrontendParametersSatellite.Modulation_QPSK
            tp.orbital_position = self.pending_orb

            log_debug("Setting frontend: %d %s %d @ orb %d" % (
                self.pending_freq, self.pending_pol,
                self.pending_sr, self.pending_orb))

            try:
                frontend.setFrontend(tp)
                log_debug("setFrontend OK")
            except Exception as e:
                log_debug("setFrontend error: %s" % str(e))
                try:
                    frontend.tune(tp)
                    log_debug("tune OK")
                except Exception as e2:
                    log_debug("tune error: %s" % str(e2))

            current = self.session.current_dialog
            if current and hasattr(current, 'retuneSat'):
                try:
                    current.retuneSat()
                    log_debug("retuneSat() after setFrontend OK")
                except Exception as e:
                    log_debug("retuneSat() error: %s" % str(e))

        except Exception as e:
            log_debug("do_retune error: %s" % str(e))
            import traceback
            log_debug("traceback: %s" % traceback.format_exc())

    def cancel(self):
        self.close()


def main(session, **kwargs):
    session.open(PomBissList)


def Plugins(**kwargs):
    return PluginDescriptor(
        name="PomBiss",
        description="Sports Feed Viewer",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="FSSLOGO.png",
        fnc=main
    )
