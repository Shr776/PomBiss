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
# SCREEN 1 - POMBISS LIST
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

    <widget name="list_header" position="60,138" size="200,40"
            font="Regular;22" transparent="1" foregroundColor="#00ff00"
            halign="left" valign="center" />
    <widget name="feed_count" position="260,138" size="200,40"
            font="Regular;20" transparent="1" foregroundColor="#ffaa00"
            halign="left" valign="center" />
    <widget name="today_date" position="580,138" size="250,40"
            font="Regular;16" transparent="1" foregroundColor="#ffff00"
            halign="right" valign="center" />

    <widget name="line_list_bot" position="50,185" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <!-- ============ پس‌زمینه انتخاب‌شده (10 خط) ============ -->
    <widget name="sel_bg_1" position="55,197" size="775,60"
            font="Regular;1" transparent="0" backgroundColor="#0a0a1a" />
    <widget name="sel_bg_2" position="55,257" size="775,60"
            font="Regular;1" transparent="0" backgroundColor="#0a0a1a" />
    <widget name="sel_bg_3" position="55,317" size="775,60"
            font="Regular;1" transparent="0" backgroundColor="#0a0a1a" />
    <widget name="sel_bg_4" position="55,377" size="775,60"
            font="Regular;1" transparent="0" backgroundColor="#0a0a1a" />
    <widget name="sel_bg_5" position="55,437" size="775,60"
            font="Regular;1" transparent="0" backgroundColor="#0a0a1a" />
    <widget name="sel_bg_6" position="55,497" size="775,60"
            font="Regular;1" transparent="0" backgroundColor="#0a0a1a" />
    <widget name="sel_bg_7" position="55,557" size="775,60"
            font="Regular;1" transparent="0" backgroundColor="#0a0a1a" />
    <widget name="sel_bg_8" position="55,617" size="775,60"
            font="Regular;1" transparent="0" backgroundColor="#0a0a1a" />
    <widget name="sel_bg_9" position="55,677" size="775,60"
            font="Regular;1" transparent="0" backgroundColor="#0a0a1a" />
    <widget name="sel_bg_10" position="55,737" size="775,60"
            font="Regular;1" transparent="0" backgroundColor="#0a0a1a" />

    <!-- ============ خط عمودی انتخاب‌شده ============ -->
    <widget name="sel_bar" position="50,200" size="6,55"
            font="Regular;1" transparent="0" backgroundColor="#00ffff" />

    <!-- ============ 10 خط لیست ============ -->

    <widget name="feed_num_1" position="65,200" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_1" position="190,200" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_1" position="490,200" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_1" position="690,200" size="150,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_2" position="65,260" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_2" position="190,260" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_2" position="490,260" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_2" position="690,260" size="150,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_3" position="65,320" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_3" position="190,320" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_3" position="490,320" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_3" position="690,320" size="150,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_4" position="65,380" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_4" position="190,380" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_4" position="490,380" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_4" position="690,380" size="150,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_5" position="65,440" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_5" position="190,440" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_5" position="490,440" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_5" position="690,440" size="150,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_6" position="65,500" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_6" position="190,500" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_6" position="490,500" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_6" position="690,500" size="150,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_7" position="65,560" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_7" position="190,560" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_7" position="490,560" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_7" position="690,560" size="150,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_8" position="65,620" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_8" position="190,620" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_8" position="490,620" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_8" position="690,620" size="150,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_9" position="65,680" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_9" position="190,680" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_9" position="490,680" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_9" position="690,680" size="150,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <widget name="feed_num_10" position="65,740" size="120,55"
            font="Regular;40" transparent="1" foregroundColor="#ffff00"
            halign="left" valign="center" />
    <widget name="feed_sat_10" position="190,740" size="300,55"
            font="Regular;22" transparent="1" foregroundColor="#00ff88"
            halign="left" valign="center" />
    <widget name="feed_freq_10" position="490,740" size="200,55"
            font="Regular;22" transparent="1" foregroundColor="#00aaff"
            halign="left" valign="center" />
    <widget name="feed_id_10" position="690,740" size="150,55"
            font="Regular;19" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

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

    <!-- ============ @VUSOLO پایین ============ -->
    <widget name="line_brand_top" position="660,960" size="600,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    <widget name="brand_label" position="660,970" size="600,50"
            font="Regular;30" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />
    <widget name="line_brand_bot" position="660,1025" size="600,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <widget name="nav_help" position="50,1040" size="1820,30"
            font="Regular;14" transparent="1" foregroundColor="#666666"
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
                     "line_cw_top", "line_cw_bot",
                     "line_brand_top", "line_brand_bot"]:
            self[line] = Label("")

        # پس‌زمینه انتخاب‌شده
        for i in range(1, 11):
            self["sel_bg_%d" % i] = Label("")

        # خط عمودی انتخاب‌شده
        self["sel_bar"] = Label("")

        self["title"] = Label("PomBiss")
        self["list_header"] = Label("FEED LIST")
        self["feed_count"] = Label("")
        self["today_date"] = Label("")
        self["page_counter"] = Label("[1/1]")

        self["brand_label"] = Label("@VUSOLO")

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

            now = time.strftime("%Y-%m-%d  %H:%M")
            self["today_date"].setText("Updated: %s" % now)

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

    def update_selection_highlight(self):
        """جابجایی پس‌زمینه و خط عمودی به فید انتخاب‌شده"""
        try:
            row = self.current_index - self.page_start

            # ریست همه پس‌زمینه‌ها
            for i in range(1, 11):
                try:
                    self["sel_bg_%d" % i].instance.setBackgroundColor(0x0a0a1a)
                except:
                    pass

            # اگه فید توی این صفحه بود
            if 0 <= row < 10:
                try:
                    self["sel_bg_%d" % (row + 1)].instance.setBackgroundColor(0x001a3a)
                except:
                    pass

        except Exception as e:
            log_debug("highlight error: %s" % str(e))

    def update_list(self):
        """پر کردن ۱۰ خط لیست"""
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
                        self["feed_num_%d" % i].instance.setForegroundColor(0x00ffff)
                        self["feed_sat_%d" % i].instance.setForegroundColor(0x00ffff)
                        self["feed_freq_%d" % i].instance.setForegroundColor(0x00ffff)
                        self["feed_id_%d" % i].instance.setForegroundColor(0x00ffff)
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

        # هایلایت انتخاب‌شده
        self.update_selection_highlight()

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
        """باز کردن Satfinder"""
        if not self.allfeeds:
            return

        try:
            from Plugins.SystemPlugins.Satfinder.plugin import SatfinderExtra
            self.session.open(SatfinderExtra)
            return
        except Exception:
            pass

        try:
            from Plugins.SystemPlugins.Satfinder.plugin import SatfinderMain
            SatfinderMain(self.session)
            return
        except Exception:
            pass

        try:
            from Plugins.SystemPlugins.Satfinder.plugin import Satfinder
            self.session.open(Satfinder)
            return
        except Exception:
            pass

        self.session.open(
            MessageBox,
            _("Satfinder not found"),
            MessageBox.TYPE_ERROR,
            timeout=10
        )

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
