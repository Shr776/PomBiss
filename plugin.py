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
