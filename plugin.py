#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
PomBiss Plugin for Enigma2
Sports Feed Viewer - Neon Tri-Color Theme
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
# MAIN SCREEN - POMBISS (NEON TRI-COLOR THEME)
# ============================================================

class PomBiss(Screen):
    """صفحه اصلی پلاگین نمایش فیدها - تم سه‌رنگ نئون"""

    skinL = '''
<screen name="PomBiss" position="center,center" size="1920,1080" title="PomBiss" flags="wfNoBorder" backgroundColor="#0a0a1a">

    <!-- ============ عنوان PomBiss - آبی نئون ============ -->
    <widget name="line_title_top" position="710,50" size="500,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    <widget name="title" position="710,55" size="500,60"
            font="Regular;42" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />
    <widget name="line_title_bot" position="710,120" size="500,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <!-- ============ Prev - آبی نئون ============ -->
    <widget name="line_prev_top" position="200,180" size="500,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    <widget name="prev_text" position="200,185" size="500,60"
            font="Regular;40" transparent="1" foregroundColor="#ff00ff"
            halign="center" valign="center" />
    <widget name="line_prev_bot" position="200,250" size="500,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <!-- ============ شماره فید + تاریخ/ساعت ============ -->
    <widget name="feed_counter" position="760,180" size="400,50"
            font="Regular;36" transparent="1" foregroundColor="#ffff00"
            halign="center" valign="center" />
    <widget name="feed_datetime" position="660,230" size="600,30"
            font="Regular;20" transparent="1" foregroundColor="#00ffff"
            halign="center" valign="center" />

    <!-- ============ Next - آبی نئون ============ -->
    <widget name="line_next_top" position="1220,180" size="500,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    <widget name="next_text" position="1220,185" size="500,60"
            font="Regular;40" transparent="1" foregroundColor="#ff00ff"
            halign="center" valign="center" />
    <widget name="line_next_bot" position="1220,250" size="500,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <!-- ============ کادر ۱: دسته‌بندی - قرمز نئون (بزرگ‌تر) ============ -->
    <widget name="line_cat_top" position="460,300" size="1000,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />
    <widget name="label_category" position="460,305" size="1000,110"
            font="Regular;28" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_cat_bot" position="460,420" size="1000,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />

    <!-- ============ کادر ۲: ماهواره - سبز نئون ============ -->
    <widget name="line_sat_top" position="610,460" size="700,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="label_satellite" position="610,465" size="700,60"
            font="Regular;34" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_sat_bot" position="610,530" size="700,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <!-- ============ کادر ۳: فرکانس - آبی نئون ============ -->
    <widget name="line_freq_top" position="510,590" size="900,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    <widget name="label_frequency" position="510,595" size="900,60"
            font="Regular;30" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_freq_bot" position="510,660" size="900,3"
            font="Regular;1" transparent="0" backgroundColor="#00aaff" />

    <!-- ============ کادر ۴: ID - سبز نئون ============ -->
    <widget name="line_id_top" position="510,720" size="900,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />
    <widget name="label_id" position="510,725" size="900,60"
            font="Regular;34" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />
    <widget name="line_id_bot" position="510,790" size="900,3"
            font="Regular;1" transparent="0" backgroundColor="#00ff00" />

    <!-- ============ کادر ۵: CW - قرمز نئون ============ -->
    <widget name="line_cw_top" position="460,850" size="1000,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />
    <widget name="label_cw" position="460,855" size="1000,65"
            font="Regular;36" transparent="1" foregroundColor="#00ff00"
            halign="center" valign="center" />
    <widget name="line_cw_bot" position="460,925" size="1000,3"
            font="Regular;1" transparent="0" backgroundColor="#ff0000" />

    <!-- ============ دکمه‌ها ============ -->
    <widget name="btn_red_bg" position="760,970" size="130,55"
            font="Regular;1" transparent="0" backgroundColor="#cc0000" />
    <widget name="key_red" position="760,970" size="130,55"
            font="Regular;24" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />

    <widget name="btn_green_bg" position="900,970" size="130,55"
            font="Regular;1" transparent="0" backgroundColor="#00cc00" />
    <widget name="key_green" position="900,970" size="130,55"
            font="Regular;24" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />

    <widget name="btn_yellow_bg" position="1040,970" size="130,55"
            font="Regular;1" transparent="0" backgroundColor="#cccc00" />
    <widget name="key_yellow" position="1040,970" size="130,55"
            font="Regular;24" transparent="1" foregroundColor="#ffffff"
            halign="center" valign="center" />

</screen>'''

    def __init__(self, session):
        self.session = session
        self.skin = self.skinL
        Screen.__init__(self, session)

        self.allfeeds = []
        self.feedindex = 0

        self["myActionsMap"] = ActionMap(
            ["SetupActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.feedscanall,
                "green": self.feedscanall,
                "yellow": self.plconf,
                "blue": self.plconf,
                "red": self.refresh,
                "left": self.kyleft,
                "right": self.kyright,
                "up": self.kyup,
                "down": self.kydown,
                "cancel": self.cancel,
            },
            -1
        )

        # خطوط (Label خالی برای پس‌زمینه)
        self["line_title_top"] = Label("")
        self["line_title_bot"] = Label("")
        self["line_prev_top"] = Label("")
        self["line_prev_bot"] = Label("")
        self["line_next_top"] = Label("")
        self["line_next_bot"] = Label("")
        self["line_cat_top"] = Label("")
        self["line_cat_bot"] = Label("")
        self["line_sat_top"] = Label("")
        self["line_sat_bot"] = Label("")
        self["line_freq_top"] = Label("")
        self["line_freq_bot"] = Label("")
        self["line_id_top"] = Label("")
        self["line_id_bot"] = Label("")
        self["line_cw_top"] = Label("")
        self["line_cw_bot"] = Label("")

        # عنوان بالا
        self["title"] = Label("PomBiss")

        # Prev/Next و شماره فید
        self["prev_text"] = Label("<<  Prev.")
        self["next_text"] = Label("Next  >>")
        self["feed_counter"] = Label("")
        self["feed_datetime"] = Label("")

        # اطلاعات فید
        self["label_category"] = Label("")
        self["label_satellite"] = Label("")
        self["label_frequency"] = Label("")
        self["label_id"] = Label("")
        self["label_cw"] = Label("")

        # دکمه‌ها
        self["btn_red_bg"] = Label("")
        self["btn_green_bg"] = Label("")
        self["btn_yellow_bg"] = Label("")
        self["key_red"] = Label("FEED")
        self["key_green"] = Label("SCAN")
        self["key_yellow"] = Label("DVB")

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

            self.allfeeds = lines
            self.feedindex = 0
            self.show_feed()

        except Exception as exc:
            self["label_category"].setText(_("Error: %s") % str(exc)[:60])

    def show_feed(self):
        if not self.allfeeds:
            return

        line = self.allfeeds[self.feedindex]
        parts = [p.strip() for p in line.split("=")]

        while len(parts) < 9:
            parts.append("")

        freq_parts = parts[0].split()
        sat_pos = freq_parts[0] if len(freq_parts) > 0 else ""
        freq = freq_parts[1] if len(freq_parts) > 1 else ""
        pol = freq_parts[2] if len(freq_parts) > 2 else ""
        sr = freq_parts[3] if len(freq_parts) > 3 else ""

        cw_key = parts[1] if len(parts) > 1 else ""
        title = parts[2] if len(parts) > 2 else ""
        sat_label = parts[3] if len(parts) > 3 else ""
        feed_id = parts[5] if len(parts) > 5 else ""

        # بخش نهم: تاریخ و ساعت
        feed_datetime = parts[8] if len(parts) > 8 else ""

        self["label_category"].setText("# " + title)
        self["label_satellite"].setText(sat_label if sat_label else sat_pos)
        self["label_frequency"].setText("Frequency: %s %s %s" % (freq, pol, sr))
        self["label_id"].setText("ID: %s" % feed_id)
        self["label_cw"].setText("CW: %s" % cw_key)

        # شماره فید و تاریخ
        self["feed_counter"].setText("[%d/%d]" % (self.feedindex + 1, len(self.allfeeds)))
        self["feed_datetime"].setText(feed_datetime)

    def kyleft(self):
        if not self.allfeeds:
            return
        if self.feedindex > 0:
            self.feedindex -= 1
        else:
            self.feedindex = len(self.allfeeds) - 1
        self.show_feed()

    def kyright(self):
        if not self.allfeeds:
            return
        if self.feedindex < len(self.allfeeds) - 1:
            self.feedindex += 1
        else:
            self.feedindex = 0
        self.show_feed()

    def kyup(self):
        if not self.allfeeds:
            return
        self.feedindex = 0
        self.show_feed()

    def kydown(self):
        if not self.allfeeds:
            return
        self.feedindex = len(self.allfeeds) - 1
        self.show_feed()

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

    def plconf(self):
        self.session.open(
            MessageBox,
            _("Settings coming soon..."),
            MessageBox.TYPE_INFO,
            timeout=3
        )

    def cancel(self):
        self.close()


def main(session, **kwargs):
    session.open(PomBiss)


def Plugins(**kwargs):
    return PluginDescriptor(
        name="PomBiss",
        description="Sports Feed Viewer",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="FSSLOGO.png",
        fnc=main
    )
