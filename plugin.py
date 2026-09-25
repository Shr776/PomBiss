#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
PomBiss Plugin for Enigma2
Sports Feed Viewer
"""

from __future__ import print_function

# برای ترجمه
try:
    from . import _
except:
    pass

# Enigma2 core
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.AVSwitch import AVSwitch
from enigma import ePicLoad, ePixmap, getDesktop
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

# Python standard
import os
import sys
import requests
# ============================================================
# SETTINGS
# ============================================================

# مسیر پوشه پلاگین روی رسیور
plugin_dir = resolveFilename(SCOPE_PLUGINS, "Extensions/PomBiss")

# آدرس فایل feeds.txt روی GitHub
FEEDS_URL = "https://raw.githubusercontent.com/Shr776/PomBissFeeds/main/feeds.txt"

# ============================================================
# CONFIG
# ============================================================

from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection
from Components.NimManager import nimmanager

# ساخت ConfigSection برای PomBiss
config.plugins.PomBiss = ConfigSubsection()
config.plugins.PomBiss.feedfreq = ConfigInteger(default=11020, limits=(0, 13000))
config.plugins.PomBiss.feedsr = ConfigInteger(default=7200, limits=(0, 100000))
config.plugins.PomBiss.feedpol = ConfigInteger(default=1, limits=(0, 1))
config.plugins.PomBiss.feedpos = ConfigInteger(default=130, limits=(0, 3600))

# Nim choices
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

# چک کردن FULLHD بودن رسیور
FULLHD = False
if getDesktop(0).size().width() > 1800:
    FULLHD = True
    

# ============================================================
# MAIN SCREEN - POMBISS
# ============================================================

class PomBiss(Screen):
    """صفحه اصلی پلاگین نمایش فیدها"""
    
    # اسکین FullHD
    skinL = '''
<screen name="PomBiss" position="center,center" size="1502,950" title="PomBiss Feed Viewer" flags="wfNoBorder" backgroundColor="transparent">
    <ePixmap position="0,0" size="1502,950" zPosition="0" pixmap="''' + plugin_dir + '''/BISSFFS6.png"/>
    
    <widget name="Label11" position="520,135" size="480,40" font="Regular;34" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label22" position="500,195" size="265,40" font="Regular;26" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label33" position="745,195" size="270,40" font="Regular;30" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label44" position="525,260" size="490,40" font="Regular;30" transparent="1" halign="center" zPosition="1"/>
    
    <widget name="Label1" position="520,323" size="350,40" font="Regular;30" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label2" position="893,325" size="100,40" font="Regular;32" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label3" position="515,388" size="485,40" font="Regular;26" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label4" position="500,450" size="250,50" font="Regular;32" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label5" position="740,455" size="270,40" font="Regular;26" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label6" position="510,508" size="500,50" font="Regular;30" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label7" position="687,596" size="145,95" font="Regular;70" transparent="1" halign="center" valign="center" zPosition="3"/>
    
    <ePixmap position="687,598" size="145,95" alphatest="on" zPosition="2" pixmap="''' + plugin_dir + '''/picon/feednofh.png"/>
    <ePixmap position="517,596" size="145,95" alphatest="on" zPosition="2" pixmap="''' + plugin_dir + '''/picon/feedfh.png"/>
    <ePixmap position="857,598" size="145,95" alphatest="on" zPosition="2" pixmap="''' + plugin_dir + '''/picon/satfh.png"/>
</screen>'''
    
    # اسکین HD
    skinS = '''
<screen name="PomBiss" position="center,center" size="1001,600" title="PomBiss Feed Viewer" flags="wfNoBorder" backgroundColor="transparent">
    <ePixmap position="0,0" size="1001,600" zPosition="0" pixmap="''' + plugin_dir + '''/BISSFFS7.png"/>
    
    <widget name="Label11" position="345,89" size="320,27" font="Regular;24" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label22" position="345,131" size="175,27" font="Regular;18" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label33" position="500,131" size="170,27" font="Regular;20" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label44" position="353,173" size="310,27" font="Regular;19" transparent="1" halign="center" zPosition="1"/>
    
    <widget name="Label1" position="342,215" size="250,25" font="Regular;20" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label2" position="593,215" size="80,25" font="Regular;20" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label3" position="345,258" size="325,25" font="Regular;20" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label4" position="347,300" size="150,25" font="Regular;20" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label5" position="510,300" size="150,25" font="Regular;20" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label6" position="347,339" size="300,27" font="Regular;23" transparent="1" halign="center" zPosition="1"/>
    <widget name="Label7" position="458,399" size="100,66" font="Regular;46" transparent="1" halign="center" zPosition="1"/>
    
    <ePixmap position="567,396" size="105,68" alphatest="on" zPosition="2" pixmap="''' + plugin_dir + '''/picon/sat.png"/>
    <ePixmap position="455,396" size="105,68" alphatest="on" zPosition="2" pixmap="''' + plugin_dir + '''/picon/feedno.png"/>
    <ePixmap position="340,396" size="105,68" alphatest="on" zPosition="2" pixmap="''' + plugin_dir + '''/picon/feed.png"/>
</screen>'''
    
    def __init__(self, session):
        self.session = session
        
        # انتخاب اسکین
        if FULLHD:
            self.skin = self.skinL
        else:
            self.skin = self.skinS
        
        Screen.__init__(self, session)
        
        # متغیرها
        self.allfeeds = []
        self.feedindex = 0
        
        # دکمه‌ها
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
        
        # پیام اولیه
        for i in [11, 22, 33, 44, 1, 2, 3, 4, 5, 6, 7]:
            self["Label" + str(i)] = Label("")
        
        self["Label11"] = Label(_("Loading feeds..."))
        
        # دانلود فیدها بعد از بارگذاری صفحه
        self.onLayoutFinish.append(self.download_feeds)
            
    # ============================================================
    # DOWNLOAD FEEDS
    # ============================================================
    
    def download_feeds(self):
        """دانلود فایل feeds.txt از GitHub و نمایش فیدها"""
        try:
            self["Label11"].setText(_("Downloading feeds..."))
            
            # درخواست به GitHub
            response = requests.get(FEEDS_URL, timeout=15)
            
            if response.status_code != 200:
                self["Label11"].setText(_("Error: HTTP %s") % response.status_code)
                return
            
            content = response.text
            
            # تقسیم به خطوط
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            
            if not lines:
                self["Label11"].setText(_("No feeds available"))
                return
            
            self.allfeeds = lines
            self.feedindex = 0
            self.show_feed()
            
        except requests.exceptions.Timeout:
            self["Label11"].setText(_("Error: Timeout"))
        except requests.exceptions.ConnectionError:
            self["Label11"].setText(_("Error: No Internet"))
        except Exception as exc:
            self["Label11"].setText(_("Error: %s") % str(exc)[:60])
    
    # ============================================================
    # SHOW FEED
    # ============================================================
    
    def show_feed(self):
        """نمایش فید فعلی روی صفحه"""
        if not self.allfeeds:
            return
        
        # خط فعلی
        line = self.allfeeds[self.feedindex]
        
        # تقسیم با =
        parts = [p.strip() for p in line.split("=")]
        
        # اطمینان از ۸ بخش
        while len(parts) < 8:
            parts.append("")
        
        # بخش ۱: sat_pos freq pol sr
        freq_parts = parts[0].split()
        sat_pos = freq_parts[0] if len(freq_parts) > 0 else ""
        freq = freq_parts[1] if len(freq_parts) > 1 else ""
        pol = freq_parts[2] if len(freq_parts) > 2 else ""
        sr = freq_parts[3] if len(freq_parts) > 3 else ""
        
        # بخش‌های دیگه
        cw_key = parts[1] if len(parts) > 1 else ""
        title = parts[2] if len(parts) > 2 else ""
        sat_label = parts[3] if len(parts) > 3 else ""
        quality = parts[4] if len(parts) > 4 else ""
        feed_id = parts[5] if len(parts) > 5 else ""
        event = parts[6] if len(parts) > 6 else ""
        teams = parts[7] if len(parts) > 7 else ""
        
        # نمایش اطلاعات
        self["Label11"].setText(title)
        self["Label22"].setText(sat_label)
        self["Label33"].setText("%s %s %s" % (freq, pol, sr))
        self["Label44"].setText(_("BISS Encrypted Feed"))
        
        self["Label1"].setText(quality)
        self["Label2"].setText("")
        self["Label3"].setText(feed_id)
        self["Label4"].setText(event)
        self["Label5"].setText(teams)
        self["Label6"].setText(cw_key)
        self["Label7"].setText(str(self.feedindex + 1))
    
    # ============================================================
    # NAVIGATION
    # ============================================================
    
    def kyleft(self):
        """فید قبلی"""
        if not self.allfeeds:
            return
        if self.feedindex > 0:
            self.feedindex -= 1
        else:
            self.feedindex = len(self.allfeeds) - 1
        self.show_feed()
    
    def kyright(self):
        """فید بعدی"""
        if not self.allfeeds:
            return
        if self.feedindex < len(self.allfeeds) - 1:
            self.feedindex += 1
        else:
            self.feedindex = 0
        self.show_feed()
    
    def kyup(self):
        """برو به اولین فید"""
        if not self.allfeeds:
            return
        self.feedindex = 0
        self.show_feed()
    
    def kydown(self):
        """برو به آخرین فید"""
        if not self.allfeeds:
            return
        self.feedindex = len(self.allfeeds) - 1
        self.show_feed()
    
    # ============================================================
    # REFRESH
    # ============================================================
    
    def refresh(self):
        """دانلود مجدد فیدها"""
        self.download_feeds()
    
    # ============================================================
    # SCAN (Satfinder)
    # ============================================================
    
    def feedscanall(self):
        """Open ScanSetup with current feed parameters"""
        try:
            # استخراج پارامترهای فید فعلی
            line = self.allfeeds[self.feedindex]
            parts = [p.strip() for p in line.split("=")]
            freq_parts = parts[0].split()
            
            sat_pos = freq_parts[0] if len(freq_parts) > 0 else "0"
            freq = int(freq_parts[1]) if len(freq_parts) > 1 else 0
            pol = freq_parts[2] if len(freq_parts) > 2 else "H"
            sr = int(freq_parts[3]) if len(freq_parts) > 3 else 0
            
            pol_num = 0 if pol.upper() == "H" else 1
            sat_pos_int = int(sat_pos) if sat_pos else 0
            
            config.plugins.PomBiss.feedpos.value = sat_pos_int
            config.plugins.PomBiss.feedfreq.value = freq
            config.plugins.PomBiss.feedpol.value = pol_num
            config.plugins.PomBiss.feedsr.value = sr
            config.plugins.PomBiss.save()
            
            from .SatfinderScan import PomBissScanMain
            PomBissScanMain(self.session)
            
        except Exception as e:
            self.session.open(
                MessageBox,
                _("Scan Error: %s") % str(e)[:150],
                MessageBox.TYPE_ERROR,
                timeout=10
            )
    
    # ============================================================
    # SETTINGS
    # ============================================================
    
    def plconf(self):
        """باز کردن تنظیمات"""
        self.session.open(
            MessageBox,
            _("Settings coming soon..."),
            MessageBox.TYPE_INFO,
            timeout=3
        )
    
    # ============================================================
    # CANCEL
    # ============================================================
    
    def cancel(self):
        """خروج از پلاگین"""
        self.close()
        

# ============================================================
# MAIN FUNCTION
# ============================================================

def main(session, **kwargs):
    """تابع اجرای پلاگین"""
    session.open(PomBiss)


# ============================================================
# PLUGIN DESCRIPTOR
# ============================================================

def Plugins(**kwargs):
    """معرفی پلاگین به Enigma2"""
    return PluginDescriptor(
        name="PomBiss",
        description="Sports Feed Viewer",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="FSSLOGO.png",
        fnc=main
    )
