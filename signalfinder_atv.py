# -*- coding: utf-8 -*-
"""
Signalfinder for PomBiss - v49
- FIX: is_id = No_Stream_Id_Filter (not 0)
- FIX: t2mi_plp_id = No_T2MI_PLP_Id (not -1)
- So ServiceScan will not show MIS at all
"""

import sys
import os
import re
import time
import glob
import signal
import binascii
from array import array
from datetime import datetime
from enigma import (
    eDVBFrontendParametersSatellite,
    eTimer,
    eServiceReference,
    iServiceInformation,
    eComponentScan,
)
from Components.NimManager import nimmanager
from Components.config import config, ConfigSubsection
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.ServiceScan import ServiceScan
from Components.Label import Label

try:
    from Tools.Directories import resolveFilename, SCOPE_PLUGINS
    _PLUGIN_DIR = resolveFilename(SCOPE_PLUGINS, "Extensions/PomBiss")
except:
    _PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"


def log_debug(msg):
    try:
        with open("/tmp/PomBiss.log", "a") as f:
            f.write("[Signalfinder] %s\n" % msg)
    except:
        pass


# ============================================================
# Helpers
# ============================================================
def _pol_to_int(pol_str):
    pol_str = str(pol_str).upper().strip()
    if pol_str == "H":
        return eDVBFrontendParametersSatellite.Polarisation_Horizontal
    elif pol_str == "V":
        return eDVBFrontendParametersSatellite.Polarisation_Vertical
    elif pol_str == "L":
        return eDVBFrontendParametersSatellite.Polarisation_CircularLeft
    elif pol_str == "R":
        return eDVBFrontendParametersSatellite.Polarisation_CircularRight
    return eDVBFrontendParametersSatellite.Polarisation_Horizontal


def _position_to_int(position_str):
    try:
        pos = float(position_str)
        if pos.is_integer():
            return int(pos)
        return int(round(pos * 10))
    except:
        return 0


def _get_nim_config_mode(slot):
    mode = None
    try:
        if hasattr(slot, 'config') and hasattr(slot.config, 'dvbs'):
            mode = slot.config.dvbs.configMode.value
    except:
        pass
    if mode is None:
        try:
            mode = slot.config_mode
        except:
            pass
    return mode


def _get_all_dvbs_tuners():
    tuners = []
    for slot in nimmanager.nim_slots:
        try:
            if not slot.isCompatible("DVB-S"):
                continue
        except:
            continue
        mode = _get_nim_config_mode(slot)
        if mode is None:
            mode = "simple"
        if mode in ("loopthrough", "satposdepends", "nothing"):
            continue
        try:
            sat_list = nimmanager.getSatListForNim(slot.slot)
            if not sat_list:
                continue
        except:
            continue
        tuners.append((slot.slot, sat_list))
    return tuners


def _get_tuner_for_position(satpos):
    tuners = _get_all_dvbs_tuners()
    log_debug("Available DVB-S tuners: %s" % str([t[0] for t in tuners]))
    for slot_id, sat_list in tuners:
        for idx, sat in enumerate(sat_list):
            if int(sat[0]) == int(satpos):
                log_debug("Found exact match: tuner=%d sat_idx=%d" % (slot_id, idx))
                return slot_id, idx
    if tuners:
        return tuners[0][0], 0
    return None, None


# ============================================================
# BISS
# ============================================================
def _find_softcam_key():
    paths = [
        "/etc/tuxbox/config/oscam-emu", "/etc/tuxbox/config/oscam-trunk",
        "/etc/tuxbox/config/oscam", "/etc/tuxbox/config/ncam",
        "/etc/tuxbox/config/gcam", "/etc/tuxbox/config",
        "/etc", "/usr/keys", "/var/keys",
    ]
    for version_file, marker in [
        ("/tmp/.oscam/oscam.version", "configdir:"),
        ("/tmp/.ncam/ncam.version", "configdir:"),
        ("/tmp/.gcam/gcam.version", "configdir:"),
    ]:
        if os.path.exists(version_file):
            try:
                with open(version_file, "r") as f:
                    data = f.readlines()
                for line in data:
                    if marker in line.lower():
                        cfgdir = line.split(":")[1].strip()
                        paths.insert(0, cfgdir)
                        break
            except:
                pass
    for path in paths:
        k = os.path.join(path, "SoftCam.Key")
        if os.path.exists(k):
            return k
    return "/usr/keys/SoftCam.Key"


_crc_table = array("L")
for _byte in range(256):
    _crc = 0; _b = _byte
    for _bit in range(8):
        if (_b ^ _crc) & 1:
            _crc = (_crc >> 1) ^ 0xEDB88320
        else:
            _crc >>= 1
        _b >>= 1
    _crc_table.append(_crc)


def _crc32(data):
    value = 0x2600 ^ 0xffffffff
    for ch in data:
        if isinstance(ch, int):
            value = _crc_table[(ch ^ value) & 0xff] ^ (value >> 8)
        else:
            value = _crc_table[(ord(ch) ^ value) & 0xff] ^ (value >> 8)
    return value ^ 0xffffffff


def _get_hash(session):
    ref = session.nav.getCurrentlyPlayingServiceReference()
    sid = ref.getUnsignedData(1); tsid = ref.getUnsignedData(2)
    onid = ref.getUnsignedData(3); ns = ref.getUnsignedData(4) | 0xA0000000
    if ns & 0xFFFF == 0:
        data = "%04X%04X%04X%08X" % (sid, tsid, onid, ns)
    else:
        data = "%04X%08X" % (sid, ns)
    return _crc32(binascii.unhexlify(data))


def _get_orb(session):
    ref = session.nav.getCurrentlyPlayingServiceReference()
    op = ref.getUnsignedData(4) >> 16
    if op == 0xFFFF: return "C"
    elif op == 0xEEEE: return "T"
    else:
        if op > 1800: op = 3600 - op; h = "W"
        else: h = "E"
        return ("%d.%d%s") % (op / 10, op % 10, h)


def _clean_cw(cw):
    cw = re.sub(r'[^0-9A-Fa-f]', '', str(cw or '')).upper()
    if re.match(r'^[0-9A-F]{16}$', cw):
        return cw
    return ""


def _save_biss_key_directly(session, softcam_path, cw):
    from ServiceReference import ServiceReference
    service = session.nav.getCurrentService()
    info = service and service.info()
    orb = _get_orb(session)
    if orb == "21.5E" or orb == "21.6E":
        sid = info.getInfo(iServiceInformation.sSID)
        vpid = info.getInfo(iServiceInformation.sVideoPID)
        keystr = "F %s%s 00 %s" % ("{:04X}".format(sid), "{:04X}".format(vpid), cw)
    else:
        keystr = "F %08X 00 %s" % (_get_hash(session), cw)
    name = ServiceReference(session.nav.getCurrentlyPlayingServiceReference()).getServiceName()
    datastr = "\n%s ; Added by PomBiss on %s for %s at %s ; Edited by PomBiss" % (
        keystr, datetime.now(), name, orb)
    try:
        with open(softcam_path, "a") as f: f.write(datastr)
        log_debug("BISS key written: %s" % keystr)
        return True, keystr
    except Exception as e:
        log_debug("write err: %s" % str(e)); return False, ""


def restart_emulator():
    kws = ["oscam", "ncam", "cccam", "mgcamd", "gbox", "wicardd", "camd", "emu", "cam"]
    pids = []
    for pd in glob.glob("/proc/[0-9]*"):
        try:
            pid = int(os.path.basename(pd))
            cp = os.path.join(pd, "comm")
            if not os.path.exists(cp): continue
            with open(cp) as f: c = f.read().strip().lower()
            if not any(k in c for k in kws): continue
            ep = os.path.join(pd, "exe")
            try: er = os.readlink(ep)
            except: er = ""
            clp = os.path.join(pd, "cmdline"); cl = ""
            try:
                with open(clp, "rb") as f:
                    cl = f.read().replace(b"\x00", b" ").decode("utf-8", "ignore").strip()
            except: pass
            pids.append({"pid": pid, "exe": er, "cmdline": cl})
        except: continue
    if not pids: return False
    for i in pids:
        try: os.kill(i["pid"], signal.SIGKILL)
        except: pass
    time.sleep(2)
    r = False
    for i in pids:
        exe = i["exe"]; cl = i["cmdline"]
        if not exe or not os.path.exists(exe): continue
        if cl:
            cp = cl.split()
            if cp and cp[0] == exe: cp = cp[1:]
            full = "%s %s" % (exe, " ".join(cp)) if cp else exe
        else: full = exe
        try: os.system("nohup %s > /dev/null 2>&1 &" % full); r = True
        except: pass
    if r: time.sleep(3)
    return r


# ============================================================
# CAID check
# ============================================================
CAID_BISS = 0x2600
POLL_MS = 1000
POLL_MAX_TRIES = 30


def _service_has_biss(session):
    try:
        service = session.nav.getCurrentService()
        info = service and service.info()
        caids = info and info.getInfoObject(iServiceInformation.sCAIDs)
        return bool(caids and CAID_BISS in caids)
    except:
        return False


# ============================================================
# Success screen
# ============================================================
class PomBissSuccessScreen(Screen):
    skin = '''
    <screen name="PomBissSuccess" position="center,center" size="750,280"
            title="PomBiss" flags="wfNoBorder" backgroundColor="#0a0a1a">
        <widget name="line_top" position="30,10" size="690,3"
                font="Regular;1" transparent="0" backgroundColor="#00aaff" />
        <widget name="msg" position="0,20" size="750,45"
                font="Regular;30" transparent="1" foregroundColor="#00ff88"
                halign="center" valign="center" />
        <widget name="service_name" position="0,68" size="750,70"
                font="Regular;22" transparent="1" foregroundColor="#ffffff"
                halign="center" valign="center" />
        <widget name="freq_info" position="0,140" size="750,32"
                font="Regular;22" transparent="1" foregroundColor="#ffaa00"
                halign="center" valign="center" />
        <widget name="orbit" position="0,176" size="750,28"
                font="Regular;20" transparent="1" foregroundColor="#00ffff"
                halign="center" valign="center" />
        <widget name="cw_label" position="0,208" size="750,26"
                font="Regular;18" transparent="1" foregroundColor="#8888aa"
                halign="center" valign="center" />
        <widget name="line_bot" position="30,248" size="690,3"
                font="Regular;1" transparent="0" backgroundColor="#00aaff" />
    </screen>'''

    def __init__(self, session, msg="Key saved successfully!",
                 service_name="", freq_info="", orbit="", cw="", timeout=5,
                 on_close=None):
        Screen.__init__(self, session)
        self.on_close_cb = on_close
        self["line_top"] = Label("")
        self["line_bot"] = Label("")
        self["msg"] = Label("")
        self["service_name"] = Label(service_name)
        self["freq_info"] = Label(freq_info)
        self["orbit"] = Label("Satellite: %s" % orbit if orbit else "")
        self["cw_label"] = Label("CW: %s" % cw if cw else "")
        self.base_msg = msg
        self.countdown = timeout
        self["msg"].setText("%s  (%d)" % (self.base_msg, self.countdown))
        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(self._tick)
        except:
            self.timer.callback.append(self._tick)
        self.timer.start(1000, False)

    def _tick(self):
        self.countdown -= 1
        if self.countdown <= 0:
            try: self.timer.stop()
            except: pass
            self._do_close()
        else:
            self["msg"].setText("%s  (%d)" % (self.base_msg, self.countdown))

    def _do_close(self):
        try:
            if self.on_close_cb:
                self.on_close_cb()
        except Exception as e:
            log_debug("on_close cb err: %s" % str(e))
        self.close()


# ============================================================
# KeyPusher
# ============================================================
_pusher = None


class _KeyPusher(object):
    def __init__(self, session, cw, feed=None):
        self.session = session
        self.cw = cw
        self.feed = feed or {}
        self.tries = 0
        self.timer = eTimer()
        try: self.timer_conn = self.timer.timeout.connect(self._tick)
        except: self.timer.callback.append(self._tick)

    def start(self):
        self.timer.start(POLL_MS, True)

    def _tick(self):
        global _pusher
        self.tries += 1
        if _service_has_biss(self.session):
            log_debug("BISS CAID found after %d tries" % self.tries)
            _pusher = None
            self._auto_save_and_restart()
        elif self.tries >= POLL_MAX_TRIES:
            log_debug("BISS CAID not found, giving up")
            _pusher = None
        else:
            self.timer.start(POLL_MS, True)

    def _auto_save_and_restart(self):
        session = self.session
        softcam = _find_softcam_key()
        if not softcam or not os.path.exists(softcam):
            session.open(MessageBox,
                         "Emu misses SoftCam.Key (%s)" % softcam,
                         MessageBox.TYPE_ERROR, timeout=8)
            return
        try:
            ok, keystr = _save_biss_key_directly(session, softcam, self.cw)
            if not ok:
                session.open(MessageBox, "Failed to write SoftCam.Key",
                             MessageBox.TYPE_ERROR, timeout=8)
                return
        except Exception as e:
            import traceback
            log_debug("save key error: %s" % str(e))
            log_debug(traceback.format_exc())
            session.open(MessageBox, "Save error: %s" % str(e),
                         MessageBox.TYPE_ERROR, timeout=8)
            return
        service_name = ""
        orb = "?"
        try:
            from ServiceReference import ServiceReference
            ref = session.nav.getCurrentlyPlayingServiceReference()
            service_name = ServiceReference(ref).getServiceName()
            orb = _get_orb(session)
        except: pass
        freq_info = ""
        try:
            freq_info = "%s %s %s" % (
                self.feed.get("freq", ""),
                self.feed.get("pol", ""),
                self.feed.get("sr", ""))
        except: pass

        def restart_after_close():
            try: restart_emulator()
            except Exception as e:
                log_debug("restart_emulator err: %s" % str(e))
        try:
            session.open(PomBissSuccessScreen,
                         "Key saved successfully!",
                         service_name, freq_info, orb, self.cw,
                         5, restart_after_close)
        except Exception as e:
            log_debug("Success screen err: %s" % str(e))
            restart_after_close()


def push_key_to_keyadder(session, cw, feed=None):
    global _pusher
    cw = _clean_cw(cw)
    if not cw:
        log_debug("feed has no valid 16-hex key, nothing to push")
        return
    log_debug("scheduling auto key push: %s" % cw)
    _pusher = _KeyPusher(session, cw, feed)
    _pusher.start()


# ============================================================
# Entry point
# ============================================================
def open_signal_finder(session, feed):
    try:
        log_debug("=" * 50)
        log_debug("=== START (v49) ===")
        log_debug("feed: " + str(feed))

        satpos = _position_to_int(feed.get('position', '0'))
        log_debug("Calculated satpos = %d" % satpos)

        feid, sat_idx = _get_tuner_for_position(satpos)
        if feid is None:
            session.open(MessageBox,
                "No DVB-S tuner found!",
                MessageBox.TYPE_ERROR)
            return

        log_debug("Selected tuner=%d, sat_idx=%s" % (feid, str(sat_idx)))

        freq = int(feed.get('freq', 0))
        sr = int(feed.get('sr', 0))
        pol_int = _pol_to_int(feed.get('pol', 'H'))

        try:
            from Plugins.SystemPlugins.Signalfinder.plugin import SignalFinder
            log_debug("SignalFinder imported OK")
        except ImportError as e:
            log_debug("SignalFinder import error: %s" % str(e))
            session.open(MessageBox,
                "SignalFinder not found!",
                MessageBox.TYPE_ERROR)
            return

        FEED_FREQ = freq
        FEED_SR = sr
        FEED_POL = pol_int
        FEED_FEID = feid
        FEED_SAT_IDX = sat_idx

        # ⭐ مقادیر درست برای حذف MIS/T2MI
        SP = eDVBFrontendParametersSatellite
        NO_STREAM = getattr(SP, 'No_Stream_Id_Filter', 0xFFFFFFFF)
        NO_T2MI = getattr(SP, 'No_T2MI_PLP_Id', 0xFFFFFFFF)
        T2MI_DEFAULT_PID = getattr(SP, 'T2MI_Default_Pid', 0x1FFF)
        PLS_DEFAULT_GOLD = getattr(SP, 'PLS_Default_Gold_Code', 0)
        PLS_GOLD = getattr(SP, 'PLS_Gold', 0)

        log_debug("constants: NO_STREAM=0x%X NO_T2MI=0x%X T2MI_PID=0x%X" % (
            NO_STREAM, NO_T2MI, T2MI_DEFAULT_PID))

        class PomBissSignalFinder(SignalFinder):
            def __init__(self, session):
                SignalFinder.__init__(self, session)
                self._pombiss_ready = False
                self._pombiss_timer = eTimer()
                try:
                    self._pombiss_timer.timeout.connect(self._pombiss_apply)
                except:
                    self._pombiss_timer.callback.append(self._pombiss_apply)
                self._pombiss_timer.start(300, False)

            def _pombiss_apply(self):
                if self._pombiss_ready:
                    return
                if not hasattr(self, 'frontend') or self.frontend is None:
                    return
                if not hasattr(self, 'tuner') or self.tuner is None:
                    return

                self._pombiss_ready = True
                self._pombiss_timer.stop()
                log_debug("PomBiss applying (frontend ready)")

                try:
                    if hasattr(self, 'scan_nims') and self.scan_nims:
                        try: self.scan_nims.value = str(FEED_FEID)
                        except: pass

                    if FEED_SAT_IDX is not None and hasattr(self, 'scan_satselection'):
                        try:
                            if len(self.scan_satselection) > FEED_FEID:
                                self.scan_satselection[FEED_FEID].value = FEED_SAT_IDX
                        except: pass

                    if hasattr(self, 'scan_type') and self.scan_type:
                        try: self.scan_type.value = "single_transponder"
                        except: pass

                    if hasattr(self, 'scan_sat') and self.scan_sat:
                        ss = self.scan_sat
                        try: ss.frequency.value = FEED_FREQ
                        except: pass
                        try: ss.symbolrate.value = FEED_SR
                        except: pass
                        try: ss.polarization.value = FEED_POL
                        except: pass

                        try:
                            if hasattr(ss, 'system'):
                                ss.system.value = SP.System_DVB_S2
                                log_debug("system = System_DVB_S2")
                        except: pass

                        try:
                            if hasattr(ss, 'modulation'):
                                ss.modulation.value = SP.Modulation_8PSK
                        except: pass
                        try:
                            if hasattr(ss, 'fec'):
                                ss.fec.value = SP.FEC_Auto
                        except: pass
                        try:
                            if hasattr(ss, 'fec_s2'):
                                ss.fec_s2.value = SP.FEC_Auto
                        except: pass
                        try:
                            if hasattr(ss, 'pilot'):
                                if hasattr(SP, 'Pilot_Unknown'):
                                    ss.pilot.value = SP.Pilot_Unknown
                                elif hasattr(SP, 'Pilot_Auto'):
                                    ss.pilot.value = SP.Pilot_Auto
                        except: pass
                        try:
                            if hasattr(ss, 'rolloff'):
                                ss.rolloff.value = SP.RollOff_alpha_0_35
                        except: pass
                        try:
                            if hasattr(ss, 'inversion'):
                                ss.inversion.value = SP.Inversion_Unknown
                        except: pass

                        # ⭐ FIX: مقادیر درست برای حذف MIS/T2MI
                        try:
                            if hasattr(ss, 'is_id_bool'):
                                ss.is_id_bool.value = False
                            if hasattr(ss, 'is_id'):
                                ss.is_id.value = NO_STREAM
                                log_debug("scan_sat.is_id = 0x%X" % NO_STREAM)
                        except: pass
                        try:
                            if hasattr(ss, 'pls_mode'):
                                ss.pls_mode.value = PLS_GOLD
                            if hasattr(ss, 'pls_code'):
                                ss.pls_code.value = PLS_DEFAULT_GOLD
                        except: pass
                        try:
                            if hasattr(ss, 't2mi_plp_id_bool'):
                                ss.t2mi_plp_id_bool.value = False
                            if hasattr(ss, 't2mi_plp_id'):
                                ss.t2mi_plp_id.value = NO_T2MI
                            if hasattr(ss, 't2mi_pid'):
                                ss.t2mi_pid.value = T2MI_DEFAULT_PID
                        except: pass

                    try: self.createSetup()
                    except Exception as e:
                        log_debug("createSetup err: %s" % str(e))
                    try: self.retune()
                    except Exception as e:
                        log_debug("retune err: %s" % str(e))

                    log_debug("PomBiss apply DONE")
                except Exception as e:
                    import traceback
                    log_debug("_pombiss_apply err: %s" % str(e))
                    log_debug(traceback.format_exc())

            def keyGo(self):
                log_debug("=== keyGo OVERRIDE (v49) ===")
                if not self._pombiss_ready:
                    log_debug("not ready yet")
                    return

                try:
                    parm = SP()
                    parm.frequency = FEED_FREQ * 1000
                    parm.symbol_rate = FEED_SR * 1000
                    parm.polarisation = FEED_POL
                    parm.system = SP.System_DVB_S2
                    parm.modulation = SP.Modulation_8PSK
                    parm.fec = SP.FEC_Auto
                    parm.inversion = SP.Inversion_Unknown

                    try:
                        if hasattr(SP, 'RollOff_alpha_0_35'):
                            parm.rolloff = SP.RollOff_alpha_0_35
                    except: pass
                    try:
                        if hasattr(SP, 'Pilot_Unknown'):
                            parm.pilot = SP.Pilot_Unknown
                        elif hasattr(SP, 'Pilot_Auto'):
                            parm.pilot = SP.Pilot_Auto
                    except: pass

                    # ⭐ FIX v49: مقادیر درست
                    for attr, val in [
                        ('is_id', NO_STREAM),
                        ('pls_mode', PLS_GOLD),
                        ('pls_code', PLS_DEFAULT_GOLD),
                        ('t2mi_plp_id', NO_T2MI),
                        ('t2mi_pid', T2MI_DEFAULT_PID),
                    ]:
                        try:
                            if hasattr(parm, attr):
                                setattr(parm, attr, val)
                                log_debug("parm.%s = 0x%X" % (attr, val))
                        except: pass

                    try:
                        sat_list = nimmanager.getSatListForNim(FEED_FEID)
                        if FEED_SAT_IDX is not None and FEED_SAT_IDX < len(sat_list):
                            parm.orbital_position = sat_list[FEED_SAT_IDX][0]
                    except: pass

                    try:
                        log_debug("transponder: freq=%d sr=%d pol=%d sys=%d mod=%d fec=%d is_id=0x%X" % (
                            parm.frequency, parm.symbol_rate, parm.polarisation,
                            parm.system, parm.modulation, parm.fec,
                            getattr(parm, 'is_id', 0)))
                    except: pass

                    tlist = [parm]
                except Exception as e:
                    import traceback
                    log_debug("transponder build err: %s" % str(e))
                    log_debug(traceback.format_exc())
                    return

                flags = 0
                try:
                    if hasattr(self, 'scan_networkScan') and self.scan_networkScan.value:
                        flags |= eComponentScan.scanNetworkSearch
                    if hasattr(self, 'scan_onlyfree') and self.scan_onlyfree.value:
                        flags |= eComponentScan.scanOnlyFree
                    for x in self["config"].list:
                        try: x[1].save()
                        except: pass
                except: pass

                try: self.tuneTimer.stop()
                except: pass
                try: self.deInitFrontend()
                except: pass

                log_debug("opening ServiceScan feid=%d flags=%d" % (FEED_FEID, flags))
                session = self.session
                session.openWithCallback(
                    self.serviceScanFinished,
                    ServiceScan,
                    [{"transponders": tlist, "feid": FEED_FEID, "flags": flags}]
                )

            def serviceScanFinished(self, answer=None):
                log_debug("ServiceScan finished: %s" % str(answer))
                try:
                    if answer is not True:
                        self.session.openWithCallback(
                            self.restartSignalFinder,
                            MessageBox,
                            "Do you want to scan another transponder/satellite?",
                            MessageBox.TYPE_YESNO,
                            timeout=10)
                    elif answer is True:
                        self.restartPrevService(True)
                except Exception as e:
                    log_debug("serviceScanFinished err: %s" % str(e))

        def on_closed(answer=None):
            log_debug("SignalFinder closed")
            cw = feed.get('cw', '')
            if cw:
                push_key_to_keyadder(session, cw, feed)

        session.openWithCallback(on_closed, PomBissSignalFinder)
        log_debug("screen opened")

    except Exception as e:
        import traceback
        log_debug("FATAL: " + str(e))
        log_debug(traceback.format_exc())
        session.open(MessageBox, "Error: " + str(e),
                     MessageBox.TYPE_ERROR, timeout=8)