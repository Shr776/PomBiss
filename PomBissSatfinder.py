# -*- coding: utf-8 -*-
"""
PomBiss Signal Finder
Custom Signal Finder for PomBiss Plugin
"""

from enigma import eDVBFrontendParametersSatellite, eTimer
from Screens.Screen import Screen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager
from Components.config import config
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

plugin_dir = resolveFilename(SCOPE_PLUGINS, "Extensions/PomBiss")


class PomBissSatfinder(Screen):
    """Signal Finder اختصاصی PomBiss"""

    skin = """
<screen name="PomBissSatfinder" position="center,center" size="1502,950"
        title="Signal Finder" flags="wfNoBorder" backgroundColor="#000000">

    <widget name="title" position="120,60" size="500,60"
            font="Regular;44" transparent="1" foregroundColor="#FFFFFF" />

    <widget name="brand" position="1080,420" size="380,120"
            font="Regular;72" transparent="1" halign="center" valign="center"
            foregroundColor="#FFFFFF" />

    <widget name="snr_label" position="120,200" size="150,40"
            font="Regular;32" transparent="1" foregroundColor="#FFFFFF" />
    <ePixmap name="snr_bar_bg" position="280,205" size="400,30"
             pixmap="''' + plugin_dir + '''/picon/bar_bg.png" alphatest="on" />
    <ePixmap name="snr_bar_red" position="280,205" size="0,30"
             pixmap="''' + plugin_dir + '''/picon/bar_red.png" alphatest="on" />
    <ePixmap name="snr_bar_yellow" position="280,205" size="0,30"
             pixmap="''' + plugin_dir + '''/picon/bar_yellow.png" alphatest="on" />
    <ePixmap name="snr_bar_green" position="280,205" size="0,30"
             pixmap="''' + plugin_dir + '''/picon/bar_green.png" alphatest="on" />
    <widget name="snr_value" position="700,200" size="150,40"
            font="Regular;32" transparent="1" foregroundColor="#FFFFFF" />

    <widget name="agc_label" position="120,270" size="150,40"
            font="Regular;32" transparent="1" foregroundColor="#FFFFFF" />
    <ePixmap name="agc_bar_bg" position="280,275" size="400,30"
             pixmap="''' + plugin_dir + '''/picon/bar_bg.png" alphatest="on" />
    <ePixmap name="agc_bar_red" position="280,275" size="0,30"
             pixmap="''' + plugin_dir + '''/picon/bar_red.png" alphatest="on" />
    <ePixmap name="agc_bar_yellow" position="280,275" size="0,30"
             pixmap="''' + plugin_dir + '''/picon/bar_yellow.png" alphatest="on" />
    <ePixmap name="agc_bar_green" position="280,275" size="0,30"
             pixmap="''' + plugin_dir + '''/picon/bar_green.png" alphatest="on" />
    <widget name="agc_value" position="700,270" size="150,40"
            font="Regular;32" transparent="1" foregroundColor="#FFFFFF" />

    <widget name="ber_label" position="120,340" size="150,40"
            font="Regular;32" transparent="1" foregroundColor="#FFFFFF" />
    <ePixmap name="ber_bar_bg" position="280,345" size="400,30"
             pixmap="''' + plugin_dir + '''/picon/bar_bg.png" alphatest="on" />
    <widget name="ber_value" position="700,340" size="150,40"
            font="Regular;32" transparent="1" foregroundColor="#FFFFFF" />

    <widget name="lock_label" position="120,410" size="150,40"
            font="Regular;32" transparent="1" foregroundColor="#FFFFFF" />
    <widget name="lock_value" position="280,405" size="60,50"
            font="Regular;40" transparent="1" halign="center"
            foregroundColor="#00FF00" />

    <widget name="info_label" position="120,520" size="250,400"
            font="Regular;30" transparent="1" foregroundColor="#FFFFFF"
            valign="top" />
    <widget name="info_value" position="380,520" size="600,400"
            font="Regular;30" transparent="1" foregroundColor="#FFFFFF"
            valign="top" />

    <widget name="key_red" position="120,860" size="250,50"
            font="Regular;28" transparent="1" foregroundColor="#FF0000"
            halign="center" />
    <widget name="key_green" position="500,860" size="250,50"
            font="Regular;28" transparent="1" foregroundColor="#00FF00"
            halign="center" />
</screen>
"""

    def __init__(self, session, feed_params=None):
        Screen.__init__(self, session)
        self.session = session
        self.feed_params = feed_params or {}

        # لیبل‌ها
        self["title"] = Label("Signal Finder")
        self["brand"] = Label("@VUSOLO")

        self["snr_label"] = Label("SNR:")
        self["snr_value"] = Label("0 %")
        self["agc_label"] = Label("AGC:")
        self["agc_value"] = Label("0 %")
        self["ber_label"] = Label("BER:")
        self["ber_value"] = Label("0")
        self["lock_label"] = Label("Lock:")
        self["lock_value"] = Label("")

        self["info_label"] = Label("")
        self["info_value"] = Label("")

        self["key_red"] = Label("Cancel")
        self["key_green"] = Label("Scan")

        # پیکچرها
        self["snr_bar_bg"] = Pixmap()
        self["snr_bar_red"] = Pixmap()
        self["snr_bar_yellow"] = Pixmap()
        self["snr_bar_green"] = Pixmap()

        self["agc_bar_bg"] = Pixmap()
        self["agc_bar_red"] = Pixmap()
        self["agc_bar_yellow"] = Pixmap()
        self["agc_bar_green"] = Pixmap()

        self["ber_bar_bg"] = Pixmap()

        # دکمه‌ها
        self["actions"] = ActionMap(
            ["SetupActions", "ColorActions"],
            {
                "cancel": self.close_screen,
                "red": self.close_screen,
                "green": self.scan,
            },
            -1
        )

        # متغیرها
        self.frontend = None
        self.timer = eTimer()
        try:
            self.timer.callback.append(self.update_signal)
        except AttributeError:
            self.timer_conn = self.timer.timeout.connect(self.update_signal)

        self.onLayoutFinish.append(self.start_tuning)

    def start_tuning(self):
        """تنظیم Tuner روی فرکانس فید"""
        try:
            sat_pos = self.feed_params.get("sat", "13.0E")
            freq = int(self.feed_params.get("freq", 0))
            pol = self.feed_params.get("pol", "H")
            sr = int(self.feed_params.get("sr", 0))

            # اطلاعات فید
            self["info_label"].setText(
                "Satellite:\nSystem:\nFrequency:\nPolarization:\nSymbol rate:\nInversion:\nFEC:"
            )
            self["info_value"].setText(
                "%s\nDVB-S2\n%d\n%s\n%d\nAuto\nAuto" % (
                    sat_pos, freq,
                    "horizontal" if pol.upper() == "H" else "vertical",
                    sr
                )
            )

            # ساخت ترانسپوندر
            tp = eDVBFrontendParametersSatellite()
            tp.frequency = freq * 1000
            tp.symbol_rate = sr * 1000
            tp.polarization = (
                eDVBFrontendParametersSatellite.Polarisation_Horizontal
                if pol.upper() == "H"
                else eDVBFrontendParametersSatellite.Polarisation_Vertical
            )
            tp.fec = eDVBFrontendParametersSatellite.FEC_Auto
            tp.inversion = eDVBFrontendParametersSatellite.Inversion_Unknown
            tp.system = eDVBFrontendParametersSatellite.System_DVB_S2
            tp.modulation = eDVBFrontendParametersSatellite.Modulation_QPSK

            # موقعیت مداری
            try:
                deg = float(sat_pos.replace("E", "").replace("W", "").strip())
                if "W" in sat_pos.upper():
                    deg = -deg
                tp.orbital_position = int(deg * 10)
            except:
                tp.orbital_position = 130

            # گرفتن Tuner و تنظیم
            nim_slot = int(config.plugins.PomBiss.nimnum.value)
            self.frontend = nimmanager.getNim(nim_slot).frontend
            self.frontend.setFrontend(tp)

            # شروع Timer
            self.timer.start(500)

        except Exception as e:
            print("[PomBissSatfinder] start_tuning error:", e)
            self["lock_value"].setText("ERR")

    def update_signal(self):
        """خوندن SNR/AGC/BER/Lock"""
        if self.frontend is None:
            return

        try:
            status = {}
            self.frontend.getFrontendStatus(status)

            snr = status.get("snr", 0)
            self["snr_value"].setText("%d %%" % snr)
            self.set_bar("snr", snr)

            agc = status.get("agc", 0)
            self["agc_value"].setText("%d %%" % agc)
            self.set_bar("agc", agc)

            ber = status.get("ber", 0)
            self["ber_value"].setText(str(ber))

            lock = status.get("lock", False)
            self["lock_value"].setText("✓" if lock else "✗")

        except Exception as e:
            print("[PomBissSatfinder] update_signal error:", e)

    def set_bar(self, name, value):
        """تنظیم عرض نوارهای رنگی"""
        try:
            total_width = 400
            value = max(0, min(100, value))

            red_w = min(value, 33) * total_width // 100
            yellow_w = max(0, min(value - 33, 33)) * total_width // 100
            green_w = max(0, min(value - 66, 34)) * total_width // 100

            self[name + "_bar_red"].instance.setPixmapSize(red_w, 30)
            self[name + "_bar_yellow"].instance.setPixmapSize(yellow_w, 30)
            self[name + "_bar_green"].instance.setPixmapSize(green_w, 30)

        except Exception as e:
            print("[PomBissSatfinder] set_bar error:", e)

    def scan(self):
        """باز کردن Scan رسمی Enigma2"""
        try:
            from Screens.ScanSetup import ScanSetup
            self.session.open(ScanSetup)
        except Exception as e:
            print("[PomBissSatfinder] scan error:", e)

    def close_screen(self):
        """توقف Timer و بستن"""
        try:
            self.timer.stop()
        except:
            pass
        self.close()
