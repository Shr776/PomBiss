# -*- coding: utf-8 -*-
"""
PomBiss Registration Module
- Uses urllib.request with SSL context (CERT_NONE)
- Works without VPN on Enigma2 receivers
"""

import os
import json
import hashlib
import time
import ssl

try:
    import urllib.request
    import urllib.error
except:
    import urllib2 as urllib

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.InputBox import InputBox
from Components.Label import Label
from Components.ActionMap import ActionMap
from enigma import eTimer


API_URL = "https://script.google.com/macros/s/AKfycbzG7c8KHNhMA1mvrJWa8TooyXgKY3Ss0ZT5Dizmjibzo3yFI-awBoim-c9QAzx2sIBz/exec"


def log_debug(msg):
    try:
        with open("/tmp/PomBiss_Registration.log", "a") as f:
            f.write("[Registration] %s\n" % msg)
    except:
        pass


# ============================================================
# MAC Address
# ============================================================
def get_mac_address():
    try:
        if os.path.exists("/sys/class/net/eth0/address"):
            with open("/sys/class/net/eth0/address", "r") as f:
                mac = f.read().strip().upper()
            if mac and mac != "00:00:00:00:00:00":
                log_debug("MAC from eth0: %s" % mac)
                return mac
    except Exception as e:
        log_debug("eth0 error: %s" % str(e))

    for i in range(4):
        try:
            path = "/sys/class/net/wlan%d/address" % i
            if os.path.exists(path):
                with open(path, "r") as f:
                    mac = f.read().strip().upper()
                if mac and mac != "00:00:00:00:00:00":
                    log_debug("MAC from wlan%d: %s" % (i, mac))
                    return mac
        except:
            continue

    log_debug("No MAC found!")
    return ""


def hash_password(password):
    try:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()
    except:
        return password


# ============================================================
# API request
# ============================================================
def api_request(data):
    try:
        json_data = json.dumps(data).encode("utf-8")

        log_debug("Sending request: %s" % json.dumps(data)[:200])

        req = urllib.request.Request(
            API_URL,
            data=json_data,
            headers={"Content-Type": "application/json"}
        )

        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        log_debug("Opening URL with SSL context...")

        try:
            response = urllib.request.urlopen(req, timeout=20, context=context)
        except TypeError:
            response = urllib.request.urlopen(req, timeout=20)

        result = response.read().decode("utf-8")

        log_debug("Response: %s" % result[:300])

        if not result:
            return None

        try:
            return json.loads(result)
        except Exception as e:
            log_debug("JSON parse error: %s" % str(e))
            return None

    except Exception as e:
        log_debug("api_request error: %s" % str(e))
        import traceback
        log_debug(traceback.format_exc())
        return None


def api_check_status(mac):
    return api_request({"action": "check", "mac": mac})


def api_register(data):
    return api_request(data)


# ============================================================
# Lists
# ============================================================
RECEIVERS = [
    "VU+", "Dreambox", "Zgemma", "Gigablue", "Octagon",
    "Mutant", "Edision", "Formuler", "Xtrent", "Other"
]

GENDERS = ["Male", "Female"]

COUNTRIES = [
    "Iran", "Turkey", "Germany", "Iraq", "Afghanistan",
    "United Arab Emirates", "Saudi Arabia", "Pakistan", "India",
    "Azerbaijan", "Armenia", "Russia", "United Kingdom",
    "United States", "France", "Italy", "Spain", "Netherlands",
    "Belgium", "Sweden", "Norway", "Denmark", "Austria",
    "Switzerland", "Greece", "Egypt", "Morocco", "Algeria",
    "Tunisia", "Libya", "Lebanon", "Jordan", "Kuwait", "Qatar",
    "Bahrain", "Oman", "Yemen", "Syria", "Other"
]


# ============================================================
# Registration Screen
# ============================================================
class RegistrationScreen(Screen):

    skin = '''
    <screen name="RegistrationScreen" position="center,center" size="900,680"
            title="PomBiss Registration" flags="wfNoBorder" backgroundColor="#0a0a1a">

        <widget name="line_top" position="50,20" size="800,3"
                font="Regular;1" transparent="0" backgroundColor="#00aaff" />

        <widget name="title" position="0,35" size="900,50"
                font="Regular;36" transparent="1" foregroundColor="#00ff88"
                halign="center" valign="center" />

        <widget name="subtitle" position="0,90" size="900,35"
                font="Regular;20" transparent="1" foregroundColor="#8888aa"
                halign="center" valign="center" />

        <widget name="line_top2" position="50,135" size="800,3"
                font="Regular;1" transparent="0" backgroundColor="#00aaff" />

        <widget name="label_user" position="80,160" size="350,40"
                font="Regular;22" transparent="1" foregroundColor="#ffffff"
                halign="left" valign="center" />
        <widget name="value_user" position="450,160" size="400,40"
                font="Regular;22" transparent="1" foregroundColor="#ffaa00"
                halign="left" valign="center" />

        <widget name="label_pass" position="80,210" size="350,40"
                font="Regular;22" transparent="1" foregroundColor="#ffffff"
                halign="left" valign="center" />
        <widget name="value_pass" position="450,210" size="400,40"
                font="Regular;22" transparent="1" foregroundColor="#ffaa00"
                halign="left" valign="center" />

        <widget name="label_country" position="80,260" size="350,40"
                font="Regular;22" transparent="1" foregroundColor="#ffffff"
                halign="left" valign="center" />
        <widget name="value_country" position="450,260" size="400,40"
                font="Regular;22" transparent="1" foregroundColor="#ffaa00"
                halign="left" valign="center" />

        <widget name="label_receiver" position="80,310" size="350,40"
                font="Regular;22" transparent="1" foregroundColor="#ffffff"
                halign="left" valign="center" />
        <widget name="value_receiver" position="450,310" size="400,40"
                font="Regular;22" transparent="1" foregroundColor="#ffaa00"
                halign="left" valign="center" />

        <widget name="label_model" position="80,360" size="350,40"
                font="Regular;22" transparent="1" foregroundColor="#8888aa"
                halign="left" valign="center" />
        <widget name="value_model" position="450,360" size="400,40"
                font="Regular;22" transparent="1" foregroundColor="#ffaa00"
                halign="left" valign="center" />

        <widget name="label_age" position="80,410" size="350,40"
                font="Regular;22" transparent="1" foregroundColor="#ffffff"
                halign="left" valign="center" />
        <widget name="value_age" position="450,410" size="400,40"
                font="Regular;22" transparent="1" foregroundColor="#ffaa00"
                halign="left" valign="center" />

        <widget name="label_email" position="80,460" size="350,40"
                font="Regular;22" transparent="1" foregroundColor="#8888aa"
                halign="left" valign="center" />
        <widget name="value_email" position="450,460" size="400,40"
                font="Regular;22" transparent="1" foregroundColor="#ffaa00"
                halign="left" valign="center" />

        <widget name="label_team" position="80,510" size="350,40"
                font="Regular;22" transparent="1" foregroundColor="#8888aa"
                halign="left" valign="center" />
        <widget name="value_team" position="450,510" size="400,40"
                font="Regular;22" transparent="1" foregroundColor="#ffaa00"
                halign="left" valign="center" />

        <widget name="label_gender" position="80,560" size="350,40"
                font="Regular;22" transparent="1" foregroundColor="#8888aa"
                halign="left" valign="center" />
        <widget name="value_gender" position="450,560" size="400,40"
                font="Regular;22" transparent="1" foregroundColor="#ffaa00"
                halign="left" valign="center" />

        <widget name="line_bot" position="50,610" size="800,3"
                font="Regular;1" transparent="0" backgroundColor="#00aaff" />

        <widget name="mac_label" position="0,625" size="900,30"
                font="Regular;18" transparent="1" foregroundColor="#00ffff"
                halign="center" valign="center" />

        <widget name="help" position="0,655" size="900,25"
                font="Regular;14" transparent="1" foregroundColor="#666666"
                halign="center" valign="center" />

    </screen>'''

    def __init__(self, session, on_success=None, on_cancel=None):
        Screen.__init__(self, session)
        self.on_success = on_success
        self.on_cancel = on_cancel

        self._reg_timer = None

        self.mac = get_mac_address()
        log_debug("RegistrationScreen MAC: %s" % self.mac)

        self.data = {
            "username": "",
            "password": "",
            "country": "Iran",
            "receiver": "VU+",
            "receiver_model": "",
            "age": "",
            "email": "",
            "favorite_team": "",
            "gender": "Male",
        }

        self.fields = [
            ("username", "Username", True),
            ("password", "Password", True),
            ("country", "Country", True),
            ("receiver", "Receiver", True),
            ("receiver_model", "Model (opt)", False),
            ("age", "Age", True),
            ("email", "Email (opt)", False),
            ("favorite_team", "Team (opt)", False),
            ("gender", "Gender (opt)", False),
        ]
        self.current_field = 0

        self["line_top"] = Label("")
        self["title"] = Label("PomBiss Registration")
        self["subtitle"] = Label("First time? Register below")
        self["line_top2"] = Label("")
        self["line_bot"] = Label("")

        self["label_user"] = Label("")
        self["value_user"] = Label("(empty)")
        self["label_pass"] = Label("")
        self["value_pass"] = Label("(empty)")
        self["label_country"] = Label("")
        self["value_country"] = Label("Iran")
        self["label_receiver"] = Label("")
        self["value_receiver"] = Label("VU+")
        self["label_model"] = Label("")
        self["value_model"] = Label("(empty)")
        self["label_age"] = Label("")
        self["value_age"] = Label("(empty)")
        self["label_email"] = Label("")
        self["value_email"] = Label("(empty)")
        self["label_team"] = Label("")
        self["value_team"] = Label("(empty)")
        self["label_gender"] = Label("")
        self["value_gender"] = Label("Male")

        self["mac_label"] = Label("MAC: %s" % self.mac)
        self["help"] = Label("Up/Down: Select  |  OK: Edit  |  GREEN: Register  |  RED: Cancel")

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.edit_field,
                "cancel": self.cancel,
                "red": self.cancel,
                "green": self.register,
                "up": self.key_up,
                "down": self.key_down,
            },
            -1
        )

        self._update_labels()
        log_debug("RegistrationScreen initialized")

    def _update_labels(self):
        labels_map = [
            ("label_user", "Username", True),
            ("label_pass", "Password", True),
            ("label_country", "Country", True),
            ("label_receiver", "Receiver", True),
            ("label_model", "Model (opt)", False),
            ("label_age", "Age", True),
            ("label_email", "Email (opt)", False),
            ("label_team", "Team (opt)", False),
            ("label_gender", "Gender (opt)", False),
        ]

        for i, (lbl_name, text, required) in enumerate(labels_map):
            try:
                if i == self.current_field:
                    self[lbl_name].setText("\u25BA %s:" % text)
                    try:
                        self[lbl_name].instance.setForegroundColor(0xffff00)
                    except:
                        pass
                else:
                    self[lbl_name].setText("    %s:" % text)
                    try:
                        if required:
                            self[lbl_name].instance.setForegroundColor(0xffffff)
                        else:
                            self[lbl_name].instance.setForegroundColor(0x8888aa)
                    except:
                        pass
            except Exception as e:
                log_debug("_update_labels error: %s" % str(e))

    def key_up(self):
        self.current_field = (self.current_field - 1) % len(self.fields)
        self._update_labels()

    def key_down(self):
        self.current_field = (self.current_field + 1) % len(self.fields)
        self._update_labels()

    def edit_field(self):
        field_key = self.fields[self.current_field][0]

        if field_key == "country":
            self._select_from_list("Country", COUNTRIES, "country")
        elif field_key == "receiver":
            self._select_from_list("Receiver", RECEIVERS, "receiver")
        elif field_key == "gender":
            self._select_from_list("Gender", GENDERS, "gender")
        else:
            self._input_text(field_key)

    def _select_from_list(self, title, items, data_key):
        tuple_list = [(str(item), str(item)) for item in items]

        def cb(answer):
            if answer and answer[1]:
                self.data[data_key] = answer[1]
                self._update_display()
                log_debug("%s = %s" % (data_key, answer[1]))

        self.session.openWithCallback(cb, ChoiceBox, title=title, list=tuple_list)

    def _input_text(self, field_key):
        current_value = self.data.get(field_key, "")
        title = "Enter %s" % field_key.capitalize()

        def cb(answer):
            if answer is not None:
                self.data[field_key] = answer.strip()
                self._update_display()
                log_debug("%s = %s" % (field_key, answer))

        self.session.openWithCallback(cb, InputBox, title=title, text=current_value)

    def _update_display(self):
        try:
            self["value_user"].setText(self.data["username"] or "(empty)")
            self["value_pass"].setText("*" * len(self.data["password"]) if self.data["password"] else "(empty)")
            self["value_country"].setText(self.data["country"] or "Iran")
            self["value_receiver"].setText(self.data["receiver"] or "VU+")
            self["value_model"].setText(self.data["receiver_model"] or "(empty)")
            self["value_age"].setText(self.data["age"] or "(empty)")
            self["value_email"].setText(self.data["email"] or "(empty)")
            self["value_team"].setText(self.data["favorite_team"] or "(empty)")
            self["value_gender"].setText(self.data["gender"] or "Male")
        except Exception as e:
            log_debug("_update_display error: %s" % str(e))

    def register(self):
        log_debug("Register button pressed")

        if not self.data["username"]:
            self.session.open(MessageBox, "Please enter Username",
                              MessageBox.TYPE_ERROR, timeout=4)
            return
        if len(self.data["username"]) < 3:
            self.session.open(MessageBox, "Username must be at least 3 chars",
                              MessageBox.TYPE_ERROR, timeout=4)
            return
        if not self.data["password"]:
            self.session.open(MessageBox, "Please enter Password",
                              MessageBox.TYPE_ERROR, timeout=4)
            return
        if len(self.data["password"]) < 6:
            self.session.open(MessageBox, "Password must be at least 6 chars",
                              MessageBox.TYPE_ERROR, timeout=4)
            return
        if not self.data["age"]:
            self.session.open(MessageBox, "Please enter Age",
                              MessageBox.TYPE_ERROR, timeout=4)
            return
        try:
            age_int = int(self.data["age"])
            if age_int < 10 or age_int > 100:
                raise ValueError()
        except:
            self.session.open(MessageBox, "Age must be between 10 and 100",
                              MessageBox.TYPE_ERROR, timeout=4)
            return

        if not self.mac:
            self.session.open(MessageBox, "Cannot read MAC address",
                              MessageBox.TYPE_ERROR, timeout=4)
            return

        register_data = {
            "action": "register",
            "username": self.data["username"],
            "password_hash": hash_password(self.data["password"]),
            "country": self.data["country"],
            "receiver": self.data["receiver"],
            "receiver_model": self.data["receiver_model"],
            "age": str(self.data["age"]),
            "mac": self.mac,
            "email": self.data["email"],
            "favorite_team": self.data["favorite_team"],
            "gender": self.data["gender"],
        }

        log_debug("Register data ready - starting timer")

        def do_register():
            log_debug("=== do_register CALLED ===")
            log_debug("Sending registration via urllib...")

            result = api_register(register_data)

            if result is None:
                log_debug("Result is None - network error")
                self.session.open(MessageBox,
                                  "Network error.\n\nPlease check connection.",
                                  MessageBox.TYPE_ERROR, timeout=8)
                return

            log_debug("Result: %s" % str(result))
            status = result.get("status", "")
            message = result.get("message", "")

            if status == "ok":
                log_debug("Registration successful")
                self.session.open(MessageBox,
                                  "\u2705 Registration successful!\n\n%s" % message,
                                  MessageBox.TYPE_INFO, timeout=5)
                self._show_pending()
            elif status == "error":
                log_debug("Registration error: %s" % message)
                self.session.open(MessageBox,
                                  "\u274C %s" % message,
                                  MessageBox.TYPE_ERROR, timeout=6)
            else:
                self.session.open(MessageBox,
                                  "Unknown response:\n%s" % str(result)[:200],
                                  MessageBox.TYPE_ERROR, timeout=8)

        self._reg_timer = eTimer()
        try:
            self._reg_timer.timeout.connect(do_register)
        except:
            self._reg_timer.callback.append(do_register)
        self._reg_timer.start(500, True)

    def _show_pending(self):
        self.close()
        self.session.open(PendingScreen, self.mac, self.on_success)

    def cancel(self):
        log_debug("Registration cancelled")
        if self.on_cancel:
            self.on_cancel()
        self.close()


# ============================================================
# Pending Screen
# ============================================================
class PendingScreen(Screen):

    skin = '''
    <screen name="PendingScreen" position="center,center" size="800,450"
            title="Pending Approval" flags="wfNoBorder" backgroundColor="#0a0a1a">

        <widget name="line_top" position="50,30" size="700,3"
                font="Regular;1" transparent="0" backgroundColor="#ffaa00" />

        <widget name="icon" position="0,60" size="800,80"
                font="Regular;60" transparent="1" foregroundColor="#ffaa00"
                halign="center" valign="center" />

        <widget name="title" position="0,150" size="800,60"
                font="Regular;36" transparent="1" foregroundColor="#ffaa00"
                halign="center" valign="center" />

        <widget name="msg1" position="0,220" size="800,40"
                font="Regular;22" transparent="1" foregroundColor="#ffffff"
                halign="center" valign="center" />

        <widget name="msg2" position="0,265" size="800,40"
                font="Regular;22" transparent="1" foregroundColor="#ffffff"
                halign="center" valign="center" />

        <widget name="mac_label" position="0,320" size="800,35"
                font="Regular;18" transparent="1" foregroundColor="#00ffff"
                halign="center" valign="center" />

        <widget name="status_line" position="0,360" size="800,30"
                font="Regular;16" transparent="1" foregroundColor="#8888aa"
                halign="center" valign="center" />

        <widget name="line_bot" position="50,400" size="700,3"
                font="Regular;1" transparent="0" backgroundColor="#ffaa00" />

        <widget name="help" position="0,415" size="800,25"
                font="Regular;14" transparent="1" foregroundColor="#666666"
                halign="center" valign="center" />
    </screen>'''

    def __init__(self, session, mac, on_success=None):
        Screen.__init__(self, session)
        self.mac = mac
        self.on_success = on_success
        self._check_timer = None
        self._open_timer = None

        self["line_top"] = Label("")
        self["icon"] = Label("\u23F3")
        self["title"] = Label("Waiting for Approval")
        self["msg1"] = Label("Your registration is pending.")
        self["msg2"] = Label("Admin will verify your account soon.")
        self["mac_label"] = Label("MAC: %s" % mac)
        self["status_line"] = Label("Checking every 10 seconds...")
        self["line_bot"] = Label("")
        self["help"] = Label("GREEN: Check Now  |  RED: Close")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self.check_now,
                "cancel": self.close,
                "red": self.close,
                "green": self.check_now,
            },
            -1
        )

        self._check_timer = eTimer()
        try:
            self._check_timer.callback.append(self.auto_check)
        except:
            self._check_timer.timeout.connect(self.auto_check)
        self._check_timer.start(10000, False)

    def auto_check(self):
        log_debug("Auto-check status")
        self.check_now()

    def check_now(self):
        result = api_check_status(self.mac)
        if result is None:
            self["status_line"].setText("Network error - retrying...")
            return

        status = result.get("status", "")
        user_status = result.get("user_status", "")

        log_debug("Status check: status=%s, user_status=%s" % (status, user_status))

        if status == "ok":
            if user_status == "active":
                log_debug("User is ACTIVE - closing pending and opening plugin")
                try:
                    self._check_timer.stop()
                except:
                    pass

                # ⭐ ذخیره session و callback
                saved_session = self.session
                saved_success = self.on_success

                # ⭐ اول PendingScreen رو ببند
                self.close()

                # ⭐ با تایمر، بعد از بسته شدن، پلاگین باز بشه
                def open_plugin():
                    log_debug("Opening PomBiss plugin now")
                    try:
                        if saved_success:
                            saved_success()
                    except Exception as e:
                        log_debug("open_plugin error: %s" % str(e))

                self._open_timer = eTimer()
                try:
                    self._open_timer.timeout.connect(open_plugin)
                except:
                    self._open_timer.callback.append(open_plugin)
                self._open_timer.start(700, True)

            elif user_status == "blocked":
                log_debug("User is BLOCKED")
                try:
                    self._check_timer.stop()
                except:
                    pass
                self.close()
                self.session.open(BlockedScreen, self.mac)
            elif user_status == "pending":
                self["status_line"].setText("Still pending - checking again...")
            else:
                self["status_line"].setText("Unknown status: %s" % user_status)
        elif status == "not_found":
            self["status_line"].setText("Not found - retrying...")
        else:
            self["status_line"].setText("Response: %s" % str(result)[:50])


# ============================================================
# Blocked Screen
# ============================================================
class BlockedScreen(Screen):

    skin = '''
    <screen name="BlockedScreen" position="center,center" size="800,400"
            title="Access Denied" flags="wfNoBorder" backgroundColor="#0a0a1a">

        <widget name="line_top" position="50,30" size="700,3"
                font="Regular;1" transparent="0" backgroundColor="#ff0000" />

        <widget name="icon" position="0,60" size="800,80"
                font="Regular;60" transparent="1" foregroundColor="#ff0000"
                halign="center" valign="center" />

        <widget name="title" position="0,150" size="800,60"
                font="Regular;36" transparent="1" foregroundColor="#ff0000"
                halign="center" valign="center" />

        <widget name="msg1" position="0,220" size="800,40"
                font="Regular;22" transparent="1" foregroundColor="#ffffff"
                halign="center" valign="center" />

        <widget name="msg2" position="0,265" size="800,40"
                font="Regular;22" transparent="1" foregroundColor="#ffffff"
                halign="center" valign="center" />

        <widget name="mac_label" position="0,320" size="800,35"
                font="Regular;18" transparent="1" foregroundColor="#00ffff"
                halign="center" valign="center" />

        <widget name="line_bot" position="50,360" size="700,3"
                font="Regular;1" transparent="0" backgroundColor="#ff0000" />

        <widget name="help" position="0,370" size="800,25"
                font="Regular;14" transparent="1" foregroundColor="#666666"
                halign="center" valign="center" />
    </screen>'''

    def __init__(self, session, mac):
        Screen.__init__(self, session)
        self.mac = mac

        self["line_top"] = Label("")
        self["icon"] = Label("\u274C")
        self["title"] = Label("Access Denied")
        self["msg1"] = Label("Your account has been blocked.")
        self["msg2"] = Label("Contact admin for more information.")
        self["mac_label"] = Label("MAC: %s" % mac)
        self["line_bot"] = Label("")
        self["help"] = Label("Press OK or EXIT to close")

        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {
                "ok": self.close,
                "cancel": self.close,
            },
            -1
        )


# ============================================================
# Check registration
# ============================================================
def check_registration(session, on_success, on_cancel=None):
    mac = get_mac_address()
    log_debug("=== check_registration ===")
    log_debug("MAC: %s" % mac)

    if not mac:
        session.open(MessageBox,
                     "Cannot read MAC address!",
                     MessageBox.TYPE_ERROR, timeout=8)
        if on_cancel:
            on_cancel()
        return

    result = api_check_status(mac)
    log_debug("API result: %s" % str(result))

    if result is None:
        session.openWithCallback(
            lambda ans: check_registration(session, on_success, on_cancel) if ans else (on_cancel() if on_cancel else None),
            MessageBox,
            "Cannot connect to server.\n\n"
            "Please check your internet connection.\n\n"
            "Try again?",
            MessageBox.TYPE_YESNO
        )
        return

    status = result.get("status", "")
    log_debug("API status: %s" % status)

    if status == "not_found":
        log_debug("New user - showing registration")
        session.open(RegistrationScreen, on_success, on_cancel)

    elif status == "ok":
        user_status = result.get("user_status", "")
        log_debug("User status: %s" % user_status)

        if user_status == "active":
            log_debug("User is ACTIVE")
            if on_success:
                on_success()
        elif user_status == "pending":
            log_debug("User is PENDING")
            session.open(PendingScreen, mac, on_success)
        elif user_status == "blocked":
            log_debug("User is BLOCKED")
            session.open(BlockedScreen, mac)
            if on_cancel:
                on_cancel()
        else:
            session.open(MessageBox,
                         "Unknown status: %s" % user_status,
                         MessageBox.TYPE_ERROR, timeout=8)
            if on_cancel:
                on_cancel()
    else:
        session.open(MessageBox,
                     "Server error: %s" % str(result)[:200],
                     MessageBox.TYPE_ERROR, timeout=8)
        if on_cancel:
            on_cancel()