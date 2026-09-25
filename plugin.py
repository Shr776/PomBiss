#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
PomBiss Plugin for Enigma2
Sports Feed Viewer - Anar Theme
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
from Components.Pixmap import Pixmap
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
# MAIN SCREEN - POMBISS
# ============================================================

class PomBiss(Screen):
    """صفحه اصلی پلاگین نمایش فیدها - تم انار"""

    skinL = '''
<screen name="PomBiss" position="center,center" size="1920,1080" title="PomBiss" flags="wfNoBorder" backgroundColor="#000000">

    <!-- انار وسط (700×751) -->
    <ePixmap position="610,165" size="700,751" zPosition="1"
             pixmap="''' + plugin_dir + '''/picon/anar.png" alphatest="on"/>

    <!-- فلش چپ (250×157) -->
    <ePixmap position="250,540" size="250,157" zPosition="2"
             pixmap="''' + plugin_dir + '''/picon/arrow_left.png" alphatest="on"/>

    <!-- فلش راست (250×157) -->
    <ePixmap position="1420,540" size="250,157" zPosition="2"
             pixmap="''' + plugin_dir + '''/picon/arrow_right.png" alphatest="on"/>

    <!-- Prev. بالا چپ -->
    <widget name="prev_text" position="200,180" size="400,80"
            font="Regular;56" transparent="1" foregroundColor="#FF6600"
            halign="center" valign="center" zPosition="3"/>

    <!-- Next بالا راست -->
    <widget name="next_text" position="1320,180" size="400,80"
            font="Regular;56" transparent="1" foregroundColor="#00FF00"
            halign="center" valign="center" zPosition="3"/>

    <!-- اطلاعات فید - داخل انار -->
    <widget name="label_category" position="660,300" size="600,50"
            font="Regular;30" transparent="1" foregroundColor="#FFFFFF"
            halign="center" valign="center" zPosition="3"/>

    <widget name="label_satellite" position="660,400" size="600,50"
            font="Regular;32" transparent="1" foregroundColor="#FFFFFF"
            halign="center" valign="center" zPosition="3"/>

    <widget name="label_frequency" position="660,490" size="600,50"
            font="Regular;30" transparent="1" foregroundColor="#FFFFFF"
            halign="center" valign="center" zPosition="3"/>

    <widget name="label_id" position="660,610" size="600,50"
            font="Regular;32" transparent="1" foregroundColor="#FFFFFF"
            halign="center" valign="center" zPosition="3"/>

    <widget name="label_cw" position="660,710" size="600,60"
            font="Regular;34" transparent="1" foregroundColor="#FFFFFF"
            halign="center" valign="center" zPosition="3"/>

    <!-- دکمه‌های رنگی بیرون انار -->
    <ePixmap position="660,950" size="140,70" zPosition="2"
             pixmap="''' + plugin_dir + '''/picon/bar_red.png" alphatest="on"/>
    <widget name="key_red" position="660,950" size="140,70"
            font="Regular;24" transparent="1" foregroundColor="#FFFFFF"
            halign="center" valign="center" zPosition="3"/>

    <ePixmap position="840,950" size="140,70" zPosition="2"
             pixmap="''' + plugin_dir + '''/picon/bar_green.png" alphatest="on"/>
    <widget name="key_green" position="840,950" size="140,70"
            font="Regular;24" transparent="1" foregroundColor="#FFFFFF"
            halign="center" valign="center" zPosition="3"/>

    <ePixmap position="1020,950" size="140,70" zPosition="2"
             pixmap="''' + plugin_dir + '''/picon/bar_yellow.png" alphatest="on"/>
    <widget name="key_yellow" position="1020,950" size="140,70"
            font="Regular;24" transparent="1" foregroundColor="#FFFFFF"
            halign="center" valign="center" zPosition="3"/>

    <!-- متن‌های پایین -->
    <widget name="text_autokey" position="180,1050" size="350,60"
            font="Regular;40" transparent="1" foregroundColor="#00FF00"
            halign="center" valign="center" zPosition="3"/>

    <widget name="text_scan" position="720,1050" size="480,60"
            font="Regular;40" transparent="1" foregroundColor="#FFFF00"
            halign="center" valign="center" zPosition="3"/>

    <widget name="text_setting" position="1380,1050" size="350,60"
            font="Regular;40" transparent="1" foregroundColor="#00AAFF"
            halign="center" valign="center" zPosition="3"/>

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

        self["prev_text"] = Label("Prev.")
        self["next_text"] = Label("Next")

        self["label_category"] = Label("")
        self["label_satellite"] = Label("")
        self["label_frequency"] = Label("")
        self["label_id"] = Label("")
        self["label_cw"] = Label("")

        self["key_red"] = Label("FEED")
        self["key_green"] = Label("SCAN")
        self["key_yellow"] = Label("DVB-S2")

        self["text_autokey"] = Label("AUTOKEY")
        self["text_scan"] = Label("SCAN(OK)")
        self["text_setting"] = Label("SETTING")

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

        while len(parts) < 8:
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

        self["label_category"].setText("#" + title)
        self["label_satellite"].setText(sat_label if sat_label else sat_pos)
        self["label_frequency"].setText("Frequency: %s %s %s" % (freq, pol, sr))
        self["label_id"].setText("ID: %s" % feed_id)
        self["label_cw"].setText("CW: %s" % cw_key)

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
