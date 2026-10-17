# -*- coding: utf-8 -*-
"""
Signalfinder for PomBiss - OpenBlackHole - v59.1 FINAL
- FIX: restart_emulator with subprocess.Popen (no os.system crash)
- FIX: SIGTERM then SIGKILL (no duplicate OSCam)
- FIX: deduplication of emu processes
- FIX: _find_sat_index with more position formats
- FIX: fallback sat_idx by name
- FIX: _do_close with GLOBAL timer (callback runs reliably)
- FIX: restart_after_close ALWAYS runs
- FIX: auto retune service AFTER emulator restart
- FIX: OOM prevention
- NEW: save_service_reference for M3U export
- v59.1: display_name field for cleaner M3U channel names
- v59.1: better feed_key sanitization
"""

import sys
import os
import re
import time
import glob
import signal
import binascii
import subprocess
import json
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
from Components.config import config
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.ServiceScan import ServiceScan
from Components.Label import Label
from Components.Pixmap import Pixmap

try:
    from Tools.Directories import resolveFilename, SCOPE_PLUGINS
    _PLUGIN_DIR = resolveFilename(SCOPE_PLUGINS, "Extensions/PomBiss")
except:
    _PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"


def log_debug(msg):
    try:
        with open("/tmp/PomBiss.log", "a") as f:
            f.write("[Signalfinder-OBH] %s\n" % msg)
    except:
        pass


def _safe_text(value):
    try:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            if isinstance(value, unicode):
                return value.encode("utf-8", "ignore")
        except NameError:
            pass
        if isinstance(value, bytes):
            return value
        try:
            return str(value)
        except:
            return ""
    except:
        return ""


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
    """
    v59: 160 -> 160 (not 1600)
    """
    try:
        s = str(position_str).strip()
        if not s:
            return 0
        pos = float(s)
        if '.' in s:
            return int(round(pos * 10))
        return int(pos)
    except:
        return 0


def _get_tuner():
    for slot in nimmanager.nim_slots:
        if slot.isCompatible("DVB-S"):
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
            if mode not in ("loopthrough", "satposdepends", "nothing"):
                return slot.slot
    return None


def _normalize_name(s):
    return str(s).upper().replace(" ", "").replace("(", "").replace(")", "").replace("-", "").replace(".", "").replace("°", "")


def _find_sat_index(feid, satpos, sat_name=""):
    """
    v59: پیدا کردن sat_idx با فرمت‌های بیشتر
    """
    try:
        sat_list = nimmanager.getSatListForNim(feid)
        if not sat_list:
            log_debug("no sat list for nim %d" % feid)
            return None

        log_debug("=== SAT LIST for nim %d (total=%d) ===" % (feid, len(sat_list)))
        for idx, sat in enumerate(sat_list[:30]):
            log_debug("  sat[%d] = %s" % (idx, str(sat)))

        pos_variants = set()
        try:
            sp = int(satpos)
            pos_variants.add(sp)
            pos_variants.add(sp * 10)
            pos_variants.add(sp * 100)
            if sp >= 360:
                pos_variants.add(sp // 10)
                pos_variants.add(sp // 100)
            pos_variants.add(sp % 3600)
            pos_variants.add(sp % 360)
        except:
            pass

        log_debug("pos_variants = %s" % str(sorted(pos_variants)))

        matches = []
        for idx, sat in enumerate(sat_list):
            try:
                sat_pos_raw = sat[0]
                if isinstance(sat_pos_raw, str):
                    sat_pos = int(float(sat_pos_raw))
                else:
                    sat_pos = int(sat_pos_raw)

                matched = False
                for pv in pos_variants:
                    if sat_pos == pv:
                        matched = True
                        break
                    if pv != 0 and (sat_pos // 10 == pv or sat_pos * 10 == pv):
                        matched = True
                        break

                if matched:
                    sat_name_str = sat[1] if len(sat) > 1 else ""
                    matches.append((idx, sat_pos, sat_name_str))
                    log_debug("  MATCH: idx=%d pos=%d name=%s" % (idx, sat_pos, sat_name_str))
            except Exception as e:
                continue

        if not matches:
            log_debug("no sat found for pos=%d (tried %s)" % (satpos, str(sorted(pos_variants))))
            return None

        if len(matches) == 1:
            log_debug("found unique sat idx=%d pos=%d name=%s" % (
                matches[0][0], matches[0][1], matches[0][2]))
            return matches[0][0]

        log_debug("multiple sats match (%d), using name='%s'" % (len(matches), sat_name))

        target_norm = _normalize_name(sat_name)
        for idx, pos, name in matches:
            name_norm = _normalize_name(name)
            for word in target_norm.split():
                if len(word) >= 3 and word in name_norm:
                    log_debug("MATCH by word '%s': idx=%d name=%s" % (word, idx, name))
                    return idx

        pos_number = int(satpos) // 100
        pos_decimal = int(satpos) % 100

        for idx, pos, name in matches:
            name_upper = str(name).upper()
            name_numbers = re.findall(r'\d+', name_upper)

            if str(pos_number) in name_numbers:
                if pos_decimal == 0:
                    log_debug("MATCH by int+decimal0: idx=%d name=%s" % (idx, name))
                    return idx
                else:
                    dec_str = str(pos_decimal).rstrip('0')
                    if dec_str and dec_str in ''.join(name_numbers):
                        log_debug("MATCH by decimal: idx=%d name=%s" % (idx, name))
                        return idx

        log_debug("WARNING: no name match, using first: idx=%d name=%s" % (
            matches[0][0], matches[0][2]))
        return matches[0][0]

    except Exception as e:
        import traceback
        log_debug("_find_sat_index error: %s" % str(e))
        log_debug(traceback.format_exc())
    return None


# ============================================================
# BISS
# ============================================================
def _find_softcam_key():
    paths = [
        "/etc/tuxbox/config/oscam-emu",
        "/etc/tuxbox/config/oscam-trunk",
        "/etc/tuxbox/config/oscam",
        "/etc/tuxbox/config/ncam",
        "/etc/tuxbox/config/gcam",
        "/etc/tuxbox/config",
        "/etc",
        "/usr/keys",
        "/var/keys",
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
        softcamkey = os.path.join(path, "SoftCam.Key")
        if os.path.exists(softcamkey):
            log_debug("found SoftCam.Key: %s" % softcamkey)
            return softcamkey

    log_debug("SoftCam.Key not found, fallback /usr/keys/SoftCam.Key")
    return "/usr/keys/SoftCam.Key"


_crc_table = array("L")
for _byte in range(256):
    _crc = 0
    _b = _byte
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


def _get_hash_from_ref(ref):
    try:
        sid = ref.getUnsignedData(1)
        tsid = ref.getUnsignedData(2)
        onid = ref.getUnsignedData(3)
        namespace = ref.getUnsignedData(4) | 0xA0000000

        if namespace & 0xFFFF == 0:
            data = "%04X%04X%04X%08X" % (sid, tsid, onid, namespace)
        else:
            data = "%04X%08X" % (sid, namespace)
        return _crc32(binascii.unhexlify(data))
    except Exception as e:
        log_debug("_get_hash_from_ref err: %s" % str(e))
        return None


def _get_hash(session):
    ref = session.nav.getCurrentlyPlayingServiceReference()
    if ref is None:
        return None
    return _get_hash_from_ref(ref)


def _get_orb(session):
    ref = session.nav.getCurrentlyPlayingServiceReference()
    if ref is None:
        return "?"
    orbpos = ref.getUnsignedData(4) >> 16
    if orbpos == 0xFFFF:
        return "C"
    elif orbpos == 0xEEEE:
        return "T"
    else:
        if orbpos > 1800:
            orbpos = 3600 - orbpos
            h = "W"
        else:
            h = "E"
        return ("%d.%d%s") % (orbpos / 10, orbpos % 10, h)


def _clean_cw(cw):
    cw = re.sub(r'[^0-9A-Fa-f]', '', str(cw or '')).upper()
    if re.match(r'^[0-9A-F]{16}$', cw):
        return cw
    return ""


def _get_service_info(session):
    try:
        from ServiceReference import ServiceReference
        ref = session.nav.getCurrentlyPlayingServiceReference()
        if ref is None:
            return {"name": "Unknown", "orb": "?"}
        name = ServiceReference(ref).getServiceName()
        orb = _get_orb(session)
        return {"name": name, "orb": orb}
    except Exception as e:
        log_debug("_get_service_info error: %s" % str(e))
        return {"name": "Unknown", "orb": "?"}


def _format_freq_from_feed(feed):
    try:
        freq = str(feed.get("freq", "")).strip()
        pol = str(feed.get("pol", "")).strip().upper()
        sr = str(feed.get("sr", "")).strip()
        if not freq:
            return ""
        return "%s %s %s" % (freq, pol, sr)
    except:
        return ""


def _save_biss_key_directly(session, softcam_path, cw):
    from ServiceReference import ServiceReference

    service = session.nav.getCurrentService()
    info = service and service.info()
    orb = _get_orb(session)

    if orb == "21.5E" or orb == "21.6E":
        if info is None:
            return False, ""
        sid = info.getInfo(iServiceInformation.sSID)
        vpid = info.getInfo(iServiceInformation.sVideoPID)
        sid_part = "{:04X}".format(sid)
        vpid_part = "{:04X}".format(vpid)
        keystr = "F %s%s 00 %s" % (sid_part, vpid_part, cw)
    else:
        h = _get_hash(session)
        if h is None:
            return False, ""
        keystr = "F %08X 00 %s" % (h, cw)

    try:
        ref = session.nav.getCurrentlyPlayingServiceReference()
        name = ServiceReference(ref).getServiceName() if ref else "Unknown"
    except:
        name = "Unknown"

    datastr = "\n%s ; Added by PomBiss on %s for %s at %s ; Edited by PomBiss" % (
        keystr, datetime.now(), name, orb)

    try:
        with open(softcam_path, "a") as f:
            f.write(datastr)
        log_debug("BISS key written: %s" % keystr)
        return True, keystr
    except Exception as e:
        log_debug("write SoftCam.Key error: %s" % str(e))
        return False, ""


# ============================================================
# ⭐ v59.1: Save Service Reference for M3U (with display_name)
# ============================================================
def save_service_reference(session, feed, service_ref):
    """
    v59.1: ذخیره Service Reference توی فایل JSON برای M3U
    - service_ref خام ذخیره می‌شه (URL-encode توی plugin.py)
    - display_name اضافه شده برای اسم کوتاه M3U
    - feed_key تمیزتر می‌شه
    """
    SERVICES_PATH = "/media/hdd/PomBiss_services.json"
    SERVICES_DIR = "/media/hdd"
    
    try:
        log_debug("=== save_service_reference START ===")
        log_debug("service_ref: %s" % service_ref)
        log_debug("feed_id: %s" % feed.get("feed_id", ""))
        log_debug("feed name: %s" % feed.get("name", ""))
        
        # اطمینان از وجود پوشه
        if not os.path.exists(SERVICES_DIR):
            try:
                os.makedirs(SERVICES_DIR)
            except Exception as e:
                log_debug("mkdir error: %s" % str(e))
                return False
        
        # خواندن فایل موجود
        services = {}
        if os.path.exists(SERVICES_PATH):
            try:
                with open(SERVICES_PATH, "r") as f:
                    services = json.load(f)
            except Exception as e:
                log_debug("JSON read error: %s" % str(e))
                services = {}
        
        # ⭐ ساخت کلید یکتا (اولویت: feed_id -> name -> timestamp)
        feed_key = feed.get("feed_id", "").strip()
        if not feed_key:
            feed_key = feed.get("name", "").strip()
        if not feed_key:
            feed_key = "feed_%s" % datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # پاکسازی کلید
        feed_key = feed_key.replace(" ", "_").replace("/", "_")
        feed_key = re.sub(r'[^\w\-]', '_', feed_key)
        feed_key = feed_key[:80]  # محدودیت طول
        
        # ⭐ نام نمایشی برای M3U
        display_name = feed.get("feed_id", "").strip()
        if not display_name:
            display_name = feed.get("name", "").strip()
        
        # محدود کردن طول نام نمایشی
        if len(display_name) > 100:
            display_name = display_name[:97] + "..."
        
        # ⭐ ساختار جدید JSON
        services[feed_key] = {
            "service_ref": str(service_ref),   # خام - URL-encode توی plugin.py
            "name": feed.get("name", "Unknown Feed"),
            "display_name": display_name,       # ⭐ نام کوتاه برای M3U
            "sat": feed.get("sat", ""),
            "position": feed.get("position", ""),
            "freq": feed.get("freq", ""),
            "pol": feed.get("pol", ""),
            "sr": feed.get("sr", ""),
            "cw": feed.get("cw", ""),
            "feed_id": feed.get("feed_id", ""),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        # نوشتن فایل
        with open(SERVICES_PATH, "w") as f:
            json.dump(services, f, indent=2, ensure_ascii=False)
        
        log_debug("Service saved: %s (total=%d)" % (feed_key, len(services)))
        return True
        
    except Exception as e:
        log_debug("save_service_reference error: %s" % str(e))
        import traceback
        log_debug(traceback.format_exc())
        return False


# ============================================================
# v59: Restart emulator - subprocess.Popen, no crash, no dup
# ============================================================
def restart_emulator():
    emu_keywords = ["oscam", "ncam", "cccam", "mgcamd", "gbox",
                    "wicardd", "camd", "emu", "cam"]

    found_pids = []
    for proc_dir in glob.glob("/proc/[0-9]*"):
        try:
            pid = int(os.path.basename(proc_dir))
            comm_path = os.path.join(proc_dir, "comm")
            if not os.path.exists(comm_path):
                continue
            with open(comm_path, "r") as f:
                comm = f.read().strip()

            comm_lower = comm.lower()
            is_emu = False
            for kw in emu_keywords:
                if kw in comm_lower:
                    is_emu = True
                    break
            if not is_emu:
                continue

            exe_path = os.path.join(proc_dir, "exe")
            try:
                exe_real = os.readlink(exe_path)
            except:
                exe_real = ""

            cmdline_path = os.path.join(proc_dir, "cmdline")
            cmdline = ""
            try:
                with open(cmdline_path, "rb") as f:
                    raw = f.read()
                cmdline = raw.replace(b"\x00", b" ").decode("utf-8", "ignore").strip()
            except:
                pass

            found_pids.append({
                "pid": pid, "comm": comm,
                "exe": exe_real, "cmdline": cmdline,
            })
        except Exception:
            continue

    if not found_pids:
        log_debug("restart_emulator: no emu pids found")
        return False

    log_debug("restart_emulator: found %d emu pids" % len(found_pids))

    # ⭐ SIGTERM first
    for info in found_pids:
        try:
            os.kill(info["pid"], signal.SIGTERM)
        except:
            pass

    time.sleep(2)

    # ⭐ SIGKILL for leftovers
    for info in found_pids:
        try:
            os.kill(info["pid"], signal.SIGKILL)
        except:
            pass

    time.sleep(1)

    # ⭐ Deduplicate + Popen
    restarted = False
    seen_cmds = set()
    for info in found_pids:
        exe = info["exe"]
        cmdline = info["cmdline"]

        if not exe or not os.path.exists(exe):
            continue

        if cmdline:
            cmd_parts = cmdline.split()
            if cmd_parts and cmd_parts[0] == exe:
                cmd_parts = cmd_parts[1:]
            if cmd_parts:
                full_cmd = [exe] + cmd_parts
            else:
                full_cmd = [exe]
        else:
            full_cmd = [exe]

        key = " ".join(full_cmd)
        if key in seen_cmds:
            log_debug("skip duplicate: %s" % key)
            continue
        seen_cmds.add(key)

        try:
            subprocess.Popen(
                full_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True
            )
            log_debug("started: %s" % key)
            restarted = True
        except Exception as e:
            log_debug("Popen err for %s: %s" % (key, str(e)))

    if restarted:
        time.sleep(2)

    return restarted


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
# Global timers (v59: prevent GC)
# ============================================================
_success_close_timer = None
_restart_timer = None


# ============================================================
# Success screen - v59 FINAL
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
        self["service_name"] = Label(_safe_text(service_name))
        self["freq_info"] = Label(_safe_text(freq_info))
        self["orbit"] = Label(_safe_text("Satellite: %s" % orbit if orbit else ""))
        self["cw_label"] = Label(_safe_text("CW: %s" % cw if cw else ""))
        self.base_msg = msg
        self.countdown = timeout
        self["msg"].setText(_safe_text("%s  (%d)" % (self.base_msg, self.countdown)))
        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(self._tick)
        except:
            self.timer.callback.append(self._tick)
        self.timer.start(1000, False)

    def _tick(self):
        self.countdown -= 1
        if self.countdown <= 0:
            try:
                self.timer.stop()
            except:
                pass
            self._do_close()
        else:
            try:
                self["msg"].setText(_safe_text("%s  (%d)" % (self.base_msg, self.countdown)))
            except:
                pass

    def _do_close(self):
        """
        v59 FINAL:
        - callback in GLOBAL timer (prevents GC)
        - then close screen
        """
        global _success_close_timer

        log_debug("SuccessScreen._do_close called")

        if self.on_close_cb:
            cb = self.on_close_cb

            def run_cb():
                log_debug("run_cb: executing on_close callback")
                try:
                    cb()
                    log_debug("run_cb: callback finished OK")
                except Exception as e:
                    log_debug("run_cb error: %s" % str(e))
                    import traceback
                    log_debug(traceback.format_exc())

            _success_close_timer = eTimer()
            try:
                _success_close_timer.timeout.connect(run_cb)
            except:
                _success_close_timer.callback.append(run_cb)
            _success_close_timer.start(500, True)
            log_debug("run_cb: timer started (500ms)")
        else:
            log_debug("_do_close: no callback!")

        try:
            self.close()
        except Exception as e:
            log_debug("self.close err: %s" % str(e))


# ============================================================
# KeyPusher v59
# ============================================================
_pusher = None


class _KeyPusher(object):
    def __init__(self, session, cw, feed=None):
        self.session = session
        self.cw = cw
        self.feed = feed or {}
        self.tries = 0
        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(self._tick)
        except:
            self.timer.callback.append(self._tick)

    def start(self):
        self.timer.start(POLL_MS, True)

    def _is_on_expected_transponder(self):
        try:
            if not self.feed:
                return True
            feed_freq = str(self.feed.get('freq', '')).strip()
            feed_sr = str(self.feed.get('sr', '')).strip()
            feed_pos = str(self.feed.get('position', '')).strip()

            service = self.session.nav.getCurrentService()
            if not service:
                return False
            feinfo = service.frontendInfo()
            if not feinfo:
                return False
            data = feinfo.getAll(True)
            if not data:
                return False

            current_freq_hz = data.get('frequency', 0)
            current_sr_hz = data.get('symbol_rate', 0)
            current_orb = data.get('orbital_position', 0)

            current_freq_khz = current_freq_hz // 1000
            current_sr_ksym = current_sr_hz // 1000

            try:
                if feed_freq and abs(int(current_freq_khz) - int(feed_freq)) > 3:
                    log_debug("mismatch freq: cur=%d exp=%s" % (current_freq_khz, feed_freq))
                    return False
            except:
                pass

            try:
                if feed_sr and abs(int(current_sr_ksym) - int(feed_sr)) > 10:
                    log_debug("mismatch sr: cur=%d exp=%s" % (current_sr_ksym, feed_sr))
                    return False
            except:
                pass

            try:
                if feed_pos:
                    exp_orb = _position_to_int(feed_pos)
                    if int(current_orb) != exp_orb:
                        log_debug("mismatch orb: cur=%d exp=%d" % (current_orb, exp_orb))
                        return False
            except:
                pass

            log_debug("OK: transponder matches")
            return True
        except Exception as e:
            log_debug("_is_on_expected_transponder err: %s" % str(e))
            return False

    def _is_cw_already_saved(self):
        try:
            softcam = _find_softcam_key()
            if not softcam or not os.path.exists(softcam):
                return False
            with open(softcam, "r") as f:
                content = f.read()
            return self.cw in content
        except:
            return False

    def _tick(self):
        global _pusher
        self.tries += 1
        if self.tries % 5 == 0:
            log_debug("KeyPusher waiting... tries=%d" % self.tries)

        if self.tries > 1:
            if not self._is_on_expected_transponder():
                log_debug("ABORT: wrong transponder")
                _pusher = None
                return

        if _service_has_biss(self.session):
            log_debug("BISS CAID found after %d tries" % self.tries)
            _pusher = None
            self._auto_save_and_restart()
        elif self.tries >= POLL_MAX_TRIES:
            log_debug("KeyPusher timeout, giving up")
            _pusher = None
        else:
            self.timer.start(POLL_MS, True)

    def _auto_save_and_restart(self):
        session = self.session

        if not self._is_on_expected_transponder():
            log_debug("ABORT save: wrong transponder")
            return

        if not _service_has_biss(session):
            log_debug("ABORT save: no BISS CAID")
            return

        if self._is_cw_already_saved():
            log_debug("SKIP: CW already in SoftCam.Key")
            return

        softcam = _find_softcam_key()
        if not softcam or not os.path.exists(softcam):
            log_debug("ABORT save: SoftCam.Key not found")
            return

        try:
            ok, keystr = _save_biss_key_directly(session, softcam, self.cw)
            if not ok:
                log_debug("save failed")
                return
        except Exception as e:
            import traceback
            log_debug("save key error: %s" % str(e))
            log_debug(traceback.format_exc())
            return

        info = _get_service_info(session)
        service_name = info.get("name", "")
        orb = info.get("orb", "?")
        freq_info = _format_freq_from_feed(self.feed)

        # ⭐ v59: restart_after_close with M3U save
        def restart_after_close():
            global _restart_timer
            log_debug("=== restart_after_close: START ===")

            # Stage 1: restart emulator
            try:
                result = restart_emulator()
                log_debug("restart_emulator() returned: %s" % result)
            except Exception as e:
                log_debug("restart_emulator error: %s" % str(e))
                import traceback
                log_debug(traceback.format_exc())

            # Stage 2: wait for emulator to boot
            time.sleep(3)

            # Stage 3: re-tune service
            try:
                if hasattr(session, 'nav') and session.nav:
                    ref = session.nav.getCurrentlyPlayingServiceReference()
                    if ref:
                        log_debug("re-tuning service...")
                        session.nav.playService(ref)
                        log_debug("service re-tuned OK")

                        # ⭐ Stage 4: ذخیره Service Reference برای M3U
                        try:
                            service_ref_str = ref.toString()
                            log_debug("service_ref_str = %s" % service_ref_str)
                            save_service_reference(session, self.feed, service_ref_str)
                            log_debug("M3U service reference saved")
                        except Exception as e:
                            log_debug("save_service_reference error: %s" % str(e))
                    else:
                        log_debug("no ref to retune")
                else:
                    log_debug("no session.nav")
            except Exception as e:
                log_debug("retune error: %s" % str(e))

            log_debug("=== restart_after_close: DONE ===")

        try:
            session.open(PomBissSuccessScreen,
                         "Key saved successfully!",
                         service_name,
                         freq_info,
                         orb,
                         self.cw,
                         5,
                         restart_after_close)
        except Exception as e:
            log_debug("Success screen error: %s" % str(e))
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
# Satfinder with params - v59
# ============================================================
def _open_satfinder_with_params(session, feed, feid):
    from Plugins.SystemPlugins.Satfinder.plugin import Satfinder

    try:
        freq = int(feed.get('freq', 0))
        sr = int(feed.get('sr', 0))
        pol = feed.get('pol', 'H').upper()
        satpos = _position_to_int(feed.get('position', '0'))
        sat_name = feed.get('sat', '')
    except Exception as e:
        log_debug("params error: %s" % str(e))
        return None

    pol_int = _pol_to_int(pol)

    log_debug("Opening Satfinder: freq=%d sr=%d pol=%d satpos=%d" % (
        freq, sr, pol_int, satpos))

    sat_idx = _find_sat_index(feid, satpos, sat_name)
    log_debug("sat_idx = %s" % str(sat_idx))

    # ⭐ fallback
    if sat_idx is None:
        try:
            sat_list = nimmanager.getSatListForNim(feid)
            if sat_list:
                target_norm = _normalize_name(sat_name)
                for idx, sat in enumerate(sat_list):
                    name = _normalize_name(sat[1] if len(sat) > 1 else "")
                    for word in target_norm.split():
                        if len(word) >= 3 and word in name:
                            sat_idx = idx
                            log_debug("FALLBACK sat_idx=%d by name '%s'" % (idx, word))
                            break
                    if sat_idx is not None:
                        break
        except Exception as e:
            log_debug("fallback err: %s" % str(e))

    if sat_idx is None:
        log_debug("WARNING: sat_idx still None! Trying index 0")
        sat_idx = 0

    log_debug("Final sat_idx = %s" % str(sat_idx))

    class PomBissSatfinder(Satfinder):
        def __init__(self, session):
            Satfinder.__init__(self, session)
            self.pombiss_feed = feed
            self.pombiss_feid = feid
            self.pombiss_freq = freq
            self.pombiss_sr = sr
            self.pombiss_pol = pol_int
            self.pombiss_sat_idx = sat_idx
            self.pombiss_applied = False
            self.pombiss_retries = 0
            self.pombiss_timer = eTimer()
            try:
                self.pombiss_timer.timeout.connect(self._pombiss_apply)
            except:
                self.pombiss_timer.callback.append(self._pombiss_apply)
            self.pombiss_timer.start(500, False)

        def _pombiss_apply(self):
            if self.pombiss_applied:
                return
            self.pombiss_retries += 1

            has_tuner = hasattr(self, 'tuner') and self.tuner is not None
            has_frontend = hasattr(self, 'frontend') and self.frontend is not None

            if not has_tuner or not has_frontend:
                if self.pombiss_retries < 20:
                    log_debug("waiting for tuner/frontend retry=%d" % self.pombiss_retries)
                    self.pombiss_timer.start(300, False)
                else:
                    log_debug("GAVE UP waiting for tuner")
                return

            self.pombiss_applied = True
            try:
                self.pombiss_timer.stop()
            except:
                pass

            log_debug("tuner/frontend ready - applying params")

            try:
                if hasattr(self, 'scan_nims') and self.scan_nims:
                    try:
                        self.scan_nims.value = str(feid)
                        log_debug("set scan_nims = %s" % str(feid))
                    except Exception as e:
                        log_debug("scan_nims err: %s" % str(e))

                if hasattr(self, 'scan_satselection'):
                    try:
                        if len(self.scan_satselection) > feid:
                            self.scan_satselection[feid].value = self.pombiss_sat_idx
                            log_debug("set scan_satselection[%d].value = %d" % (
                                feid, self.pombiss_sat_idx))
                    except Exception as e:
                        log_debug("scan_satselection err: %s" % str(e))

                if hasattr(self, 'tuning_type') and self.tuning_type:
                    try:
                        self.tuning_type.value = "single_transponder"
                        log_debug("set tuning_type = single_transponder")
                    except Exception as e:
                        log_debug("tuning_type err: %s" % str(e))

                if hasattr(self, 'scan_sat') and self.scan_sat:
                    try:
                        self.scan_sat.frequency.value = self.pombiss_freq
                        log_debug("set frequency = %d" % self.pombiss_freq)
                    except Exception as e:
                        log_debug("frequency err: %s" % str(e))

                    try:
                        self.scan_sat.symbolrate.value = self.pombiss_sr
                        log_debug("set symbolrate = %d" % self.pombiss_sr)
                    except Exception as e:
                        log_debug("symbolrate err: %s" % str(e))

                    try:
                        self.scan_sat.polarization.value = self.pombiss_pol
                        log_debug("set polarization = %d" % self.pombiss_pol)
                    except Exception as e:
                        log_debug("polarization err: %s" % str(e))

                    try:
                        self.scan_sat.system.value = eDVBFrontendParametersSatellite.System_DVB_S2
                    except:
                        pass

                    try:
                        self.scan_sat.modulation.value = eDVBFrontendParametersSatellite.Modulation_8PSK
                    except:
                        pass

                    try:
                        self.scan_sat.fec_s2.value = eDVBFrontendParametersSatellite.FEC_Auto
                    except:
                        pass

                    try:
                        self.scan_sat.fec.value = eDVBFrontendParametersSatellite.FEC_Auto
                    except:
                        pass

                    try:
                        self.scan_sat.pilot.value = eDVBFrontendParametersSatellite.Pilot_Auto
                    except:
                        pass

                    try:
                        self.scan_sat.rolloff.value = eDVBFrontendParametersSatellite.RollOff_alpha_0_35
                    except:
                        pass

                    try:
                        self.scan_sat.inversion.value = eDVBFrontendParametersSatellite.Inversion_Unknown
                    except:
                        pass

                try:
                    self.createSetup()
                    log_debug("createSetup called")
                except Exception as e:
                    log_debug("createSetup err: %s" % str(e))

                try:
                    if hasattr(self, 'retune'):
                        self.retune()
                        log_debug("retune called")
                except Exception as e:
                    log_debug("retune err: %s" % str(e))

                log_debug("--- params applied ---")

            except Exception as e:
                import traceback
                log_debug("_pombiss_apply error: %s" % str(e))
                log_debug(traceback.format_exc())

    return PomBissSatfinder


# ============================================================
# Entry point - v59.1 FINAL
# ============================================================
def open_signal_finder(session, feed):
    saved_ref = None
    try:
        saved_ref = session.nav.getCurrentlyPlayingServiceReference()
        log_debug("saved current ref for restore")
    except:
        pass

    try:
        log_debug("=" * 50)
        log_debug("=== START (OBH v59.1 FINAL) ===")
        log_debug("feed: " + str(feed))

        feid = _get_tuner()
        if feid is None:
            session.open(MessageBox,
                "No DVB-S tuner found!",
                MessageBox.TYPE_ERROR)
            return

        log_debug("using tuner: %d" % feid)

        try:
            CustomSatfinder = _open_satfinder_with_params(session, feed, feid)
        except ImportError as e:
            log_debug("Satfinder import error: %s" % str(e))
            CustomSatfinder = None
        except Exception as e:
            log_debug("Satfinder setup error: %s" % str(e))
            import traceback
            log_debug(traceback.format_exc())
            CustomSatfinder = None

        if CustomSatfinder is None:
            log_debug("falling back to ScanSetup")
            from Screens.ScanSetup import ScanSetup

            class PomBissScanSetup(ScanSetup):
                def __init__(self, session):
                    ScanSetup.__init__(self, session)
                    self.pombiss_feed = feed
                    self.pombiss_feid = feid
                    self.onLayoutFinish.append(self._apply)

                def _apply(self):
                    try:
                        freq_khz = int(self.pombiss_feed['freq'])
                        sr_ksym = int(self.pombiss_feed['sr'])
                        pol_int = _pol_to_int(self.pombiss_feed['pol'])

                        if hasattr(self, 'scan_sat'):
                            ss = self.scan_sat
                            try: ss.frequency.value = freq_khz
                            except: pass
                            try: ss.symbolrate.value = sr_ksym
                            except: pass
                            try: ss.polarization.value = pol_int
                            except: pass
                            try: ss.system.value = eDVBFrontendParametersSatellite.System_DVB_S2
                            except: pass
                            try: ss.modulation.value = eDVBFrontendParametersSatellite.Modulation_8PSK
                            except: pass

                        self.createSetup()
                    except Exception as e:
                        log_debug("fallback apply err: %s" % str(e))

                def startScanCallback(self, answer=None):
                    session = self.session
                    cw = self.pombiss_feed.get('cw', '')
                    self.doCloseRecursive()
                    if not answer:
                        return
                    push_key_to_keyadder(session, cw, self.pombiss_feed)

            session.open(PomBissScanSetup)
        else:
            def on_close(answer=None):
                log_debug("Satfinder closed")
                cw = feed.get('cw', '')
                if cw:
                    push_key_to_keyadder(session, cw, feed)

            session.openWithCallback(on_close, CustomSatfinder)

        log_debug("screen opened")

    except Exception as e:
        import traceback
        log_debug("ERROR: " + str(e))
        log_debug(traceback.format_exc())
        try:
            if saved_ref:
                session.nav.playService(saved_ref)
                log_debug("restored previous service after error")
        except:
            pass
        session.open(MessageBox, "Error: " + str(e),
                     MessageBox.TYPE_ERROR, timeout=8)