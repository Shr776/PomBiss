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
    <widget name="list_header" position="50,140" size="780,40"
            font="Regular;24" transparent="1" foregroundColor="#00ff00"
            halign="center" valign="center" />
    <widget name="line_list_bot" position="50,185" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <!-- 10 خط لیست فیدها -->
    <widget name="feed_1" position="60,200" size="760,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />
    <widget name="feed_2" position="60,260" size="760,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />
    <widget name="feed_3" position="60,320" size="760,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />
    <widget name="feed_4" position="60,380" size="760,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />
    <widget name="feed_5" position="60,440" size="760,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />
    <widget name="feed_6" position="60,500" size="760,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />
    <widget name="feed_7" position="60,560" size="760,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />
    <widget name="feed_8" position="60,620" size="760,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />
    <widget name="feed_9" position="60,680" size="760,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />
    <widget name="feed_10" position="60,740" size="760,55"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="left" valign="center" />

    <!-- شماره صفحه (پایین لیست) -->
    <widget name="line_page_top" position="50,820" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="page_counter" position="50,825" size="780,50"
            font="Regular;28" transparent="1" foregroundColor="#ffff00"
            halign="center" valign="center" />
    <widget name="line_page_bot" position="50,880" size="780,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <!-- ============ کادر جزئیات (راست) ============ -->
    <!-- عنوان/دسته - قرمز -->
    <widget name="line_cat_top" position="860,130" size="1010,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />
    <widget name="label_category" position="860,135" size="1010,90"
            font="Regular;22" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_cat_bot" position="860,230" size="1010,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />

    <!-- ماهواره - سبز -->
    <widget name="line_sat_top" position="960,250" size="810,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="label_satellite" position="960,255" size="810,55"
            font="Regular;28" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_sat_bot" position="960,315" size="810,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <!-- فرکانس - آبی -->
    <widget name="line_freq_top" position="910,335" size="910,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    <widget name="label_frequency" position="910,340" size="910,55"
            font="Regular;26" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_freq_bot" position="910,400" size="910,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <!-- ID - سبز -->
    <widget name="line_id_top" position="910,420" size="910,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="label_id" position="910,425" size="910,55"
            font="Regular;28" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_id_bot" position="910,485" size="910,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <!-- CW - قرمز با متن سبز -->
    <widget name="line_cw_top" position="860,505" size="1010,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />
    <widget name="label_cw" position="860,510" size="1010,60"
            font="Regular;32" transparent="1" foregroundColor="#00ff00"
            halign="center" valign="center" />
    <widget name="line_cw_bot" position="860,575" size="1010,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />

    <!-- تاریخ/ساعت -->
    <widget name="label_datetime" position="860,590" size="1010,40"
            font="Regular;20" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />

    <!-- ============ دکمه‌ها (پایین راست) ============ -->
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

    <!-- راهنمای ناوبری پایین -->
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

        # خطوط
        for line in ["line_title_top", "line_title_bot",
                     "line_list_top", "line_list_bot",
                     "line_page_top", "line_page_bot",
                     "line_cat_top", "line_cat_bot",
                     "line_sat_top", "line_sat_bot",
                     "line_freq_top", "line_freq_bot",
                     "line_id_top", "line_id_bot",
                     "line_cw_top", "line_cw_bot"]:
            self[line] = Label("")

        # عنوان‌ها
        self["title"] = Label("PomBiss")
        self["list_header"] = Label("FEED LIST")
        self["page_counter"] = Label("[1/1]")

        # ۱۰ خط لیست
        for i in range(1, 11):
            self["feed_%d" % i] = Label("")

        # اطلاعات جزئیات
        self["label_category"] = Label("")
        self["label_satellite"] = Label("")
        self["label_frequency"] = Label("")
        self["label_id"] = Label("")
        self["label_cw"] = Label("")
        self["label_datetime"] = Label("")

        # دکمه‌ها
        self["btn_red_bg"] = Label("")
        self["btn_green_bg"] = Label("")
        self["btn_yellow_bg"] = Label("")
        self["key_red"] = Label("FEED")
        self["key_green"] = Label("SCAN")
        self["key_yellow"] = Label("DVB")

        # راهنما
        self["nav_help"] = Label("Up/Down: Select  |  Left/Right: Page  |  OK: Open")

        self.onLayoutFinish.append(self.download_feeds)

    def download_feeds(self):
        try:
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

            # مرتب‌سازی بر اساس تاریخ (جدیدترین اول)
            def get_datetime_key(line):
                parts = line.split("=")
                if len(parts) > 8:
                    return parts[8].strip()
                return ""

            lines.sort(key=get_datetime_key, reverse=True)

            self.allfeeds = lines
            self.current_index = 0
            self.page_start = 0

            self.update_list()
            self.update_details()

        except Exception as exc:
            self["label_category"].setText(_("Error: %s") % str(exc)[:60])

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

                # پارس
                freq_parts = parts[0].strip().split()
                freq = freq_parts[1] if len(freq_parts) > 1 else ""
                pol = freq_parts[2] if len(freq_parts) > 2 else ""

                sat_label = parts[3].strip() if len(parts) > 3 else ""
                feed_id = parts[5].strip() if len(parts) > 5 else ""

                # شماره + ماهواره + فرکانس + ID
                marker = "► " if feed_idx == self.current_index else "   "
                text = "%s[%d] %s  |  %s %s  |  %s" % (
                    marker, feed_idx + 1, sat_label, freq, pol, feed_id
                )

                # رنگ انتخاب‌شده
                if feed_idx == self.current_index:
                    self["feed_%d" % i].setText(text)
                    # رنگ زرد برای انتخاب
                    try:
                        self["feed_%d" % i].instance.setForegroundColor(0xffff00)
                    except:
                        pass
                else:
                    self["feed_%d" % i].setText(text)
                    try:
                        self["feed_%d" % i].instance.setForegroundColor(0xffffff)
                    except:
                        pass
            else:
                self["feed_%d" % i].setText("")

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

        self["label_category"].setText("# " + title)
        self["label_satellite"].setText(sat_label)
        self["label_frequency"].setText("Frequency: %s %s %s" % (freq, pol, sr))
        self["label_id"].setText("ID: %s" % feed_id)
        self["label_cw"].setText("CW: %s" % cw_key)
        self["label_datetime"].setText(feed_datetime)

    def keyUp(self):
        if self.current_index > 0:
            self.current_index -= 1

            # اگه از صفحه خارج شد
            if self.current_index < self.page_start:
                self.page_start -= self.feeds_per_page

            self.update_list()
            self.update_details()

    def keyDown(self):
        if self.current_index < len(self.allfeeds) - 1:
            self.current_index += 1

            # اگه از صفحه خارج شد
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
        

# ============================================================
# MAIN FUNCTION
# ============================================================

def main(session, **kwargs):
    """تابع اجرای پلاگین"""
    session.open(PomBissList)


# ============================================================
# PLUGIN DESCRIPTOR
# ============================================================

def Plugins(**kwargs):
    return PluginDescriptor(
        name="PomBiss",
        description="Sports Feed Viewer",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="FSSLOGO.png",
        fnc=main
    )
