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
