
### ۲. محتوای بالا رو **کامل کپی کن و پیست کن**

### ۳. **Commit changes**

---

## 🎯 یا راه بهتر: یه فایل `CHANGELOG.md` بساز

**اگه میخوای یه فایل دائمی برای همه نسخه‌ها داشته باشی، `CHANGELOG.md` بساز:**

```markdown
# Changelog

All notable changes to PomBiss Plugin are documented in this file.

## [2.1] - October 2026

### 🆕 Added
- Telnet installer (`installer.sh`)
- Multi-image support (OpenBlackHole 5/6, OpenATV 7.6/8.0, OpenPLi 8.3)
- Auto-detection dispatcher for SignalFinder
- Full documentation in 4 languages

### 🐛 Fixed
- **Duplicate BISS key issue** — no more duplicate keys in `SoftCam.Key`
- **Smart satellite detection** — by name + position
- **`_py3` dependency removed** — works on Python 2 and Python 3
- **`eLabel_setText` crash** on Python 2 (Unicode characters)
- **Button visibility** — text now visible on colored backgrounds
- **Auto-restart** after emulator restart

### 🔧 Changed
- Refactored `signalfinder.py` dispatcher
- Improved `KeyPusher` logic (3 checks before saving)
- Better logging in `/tmp/PomBiss.log`

### 📄 Documentation
- Added `README.md` in 4 languages (Farsi, English, Arabic, Turkish)
- Added tested images table
- Added installation instructions

---

## [1.9] - Previous Release

### 🆕 Added
- Initial public release
- Feed viewer from Telegram
- Auto BISS key saving
- MAC Address registration
- Auto-update from GitHub

### ✨ Features
- Beautiful Neon UI
- Dual panel layout
- Clear old keys feature
- Contact Us screen

---

**Legend:**
- 🆕 Added — New features
- 🐛 Fixed — Bug fixes
- 🔧 Changed — Changes in existing functionality
- 📄 Documentation — Documentation changes
- ❌ Removed — Removed features
