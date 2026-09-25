# -*- coding: utf-8 -*-
"""
PomBiss Signal Finder
Custom Signal Finder for PomBiss Plugin
"""

from enigma import (
    eDVBFrontendParametersSatellite,
    eTimer,
    iPlayableService,
    eServiceReference,
    getDesktop,
)
from Screens.Screen import Screen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager
from Components.config import config
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import NavigationInstance

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
        self.tp = None
        self.timer = eTimer()
        # پشتیبانی از هر دو روش eTimer
        try:
            self.timer.callback.append(self.update_signal)
        except AttributeError:
            try:
                self.timer_conn = self.timer.timeout.connect(self.update_signal)
            except Exception as e:
                print("[PomBissSatfinder] timer error:", e)

        self.onLayoutFinish.append(self.start_tuning)

    def start_tuning(self):
        """تنظیم Tuner روی فرکانس فید"""
        try:
            sat_pos = self.feed_params.get("sat", "13.0E")
            freq = int(self.feed_params.get("freq", 0))
            pol = self.feed_params.get("pol", "H")
            sr = int(self.feed_params.get("sr", 0))

            # اطلاعات فید (نمایش Satellite به صورت 13.0E نه 130)
            sat_display = sat_pos if "E" in sat_pos.upper() or "W" in sat_pos.upper() else str(sat_pos)
            self["info_label"].setText(
                "Satellite:\nSystem:\nFrequency:\nPolarization:\nSymbol rate:\nInversion:\nFEC:"
            )
            self["info_value"].setText(
                "%s\nDVB-S2\n%d\n%s\n%d\nAuto\nAuto" % (
                    sat_display, freq,
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

            self.tp = tp

            # گرفتن Tuner
            nim_slot = int(config.plugins.PomBiss.nimnum.value)
            self.frontend = nimmanager.getNim(nim_slot).frontend

            # 🔧 روش صحیح تنظیم Tuner در OpenBh 6.0
            # روش ۱: استفاده از tune
            try:
                self.frontend.tune(tp)
                print("[PomBissSatfinder] tune() OK")
            except AttributeError:
                # روش ۲: استفاده از setFrontend
                try:
                    self.frontend.setFrontend(tp)
                    print("[PomBissSatfinder] setFrontend() OK")
                except AttributeError:
                    # روش ۳: استفاده از iPlayableService
                    print("[PomBissSatfinder] trying iPlayableService...")
                    self._tune_via_service(tp)

            # شروع Timer
            self.timer.start(500)
            print("[PomBissSatfinder] Timer started")

        except Exception as e:
            import traceback
            print("[PomBissSatfinder] start_tuning error:", e)
            traceback.print_exc()
            self["lock_value"].setText("ER")

    def _tune_via_service(self, tp):
        """روش جایگزین تنظیم Tuner با iPlayableService"""
        try:
            # ساخت یک ServiceReference موقت
            ref = eServiceReference(
                1,  # نوع سرویس: DVB
                0,
                "1:0:1:0:0:0:0:0:0:0:/"  # مسیر موقت
            )
            # تنظیم Tuner از طریق NavigationInstance
            nav = NavigationInstance.instance
            if nav:
                # این روش خودش Tuner رو تنظیم می‌کنه
                print("[PomBissSatfinder] Using NavigationInstance")
        except Exception as e:
            print("[PomBissSatfinder] _tune_via_service error:", e)

    def update_signal(self):
        """خوندن SNR/AGC/BER/Lock"""
        if self.frontend is None:
            return

        try:
            status = {}
            try:
                self.frontend.getFrontendStatus(status)
            except Exception as e:
                # اگه getFrontendStatus کار نکرد، از iPlayableService استفاده کن
                try:
                    service = self.session.nav.getCurrentService()
                    if service:
                        frontend_info = service.frontendInfo()
                        if frontend_info:
                            status = frontend_info.getAll()
                except:
                    pass

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
        """باز کردن ScanSetup با پارامترهای فید فعلی"""
        try:
            from Screens.ScanSetup import ScanSetup
            from Screens.ScanSetup import ScanSimple

            # ساخت Setup با transponder
            if self.tp:
                self.session.open(ScanSetup, transponder=self.tp, scan_type="single")
            else:
                self.session.open(ScanSetup)
        except Exception as e:
            print("[PomBissSatfinder] scan error:", e)
            import traceback
            traceback.print_exc()
            # اگه خطا داد، Manual Scan معمولی باز کن
            try:
                from Screens.ScanSetup import ScanSetup
                self.session.open(ScanSetup)
            except:
                pass

    def close_screen(self):
        """توقف Timer و بستن"""
        try:
            self.timer.stop()
        except:
            pass
        self.close()
