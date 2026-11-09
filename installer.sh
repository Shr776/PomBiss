#!/bin/sh
#
# ============================================================
#   PomBiss Plugin Installer v2.8
# ============================================================
#
#   Sports Feed Viewer for Enigma2
#
#   Supported Images:
#     - OpenBlackHole 5 / 6
#     - OpenATV 7.6 / 8.0
#     - OpenPLi 8.3 / 9.2
#     - Egami 11.2
#
#   GitHub: https://github.com/Shr776/PomBiss
#
#   This installer reads the file list of the GitHub repository
#   and installs EVERYTHING in it (root files, picon/, fonts/ ...)
#   with the same folder structure. New files added to GitHub
#   later are installed automatically.
# ============================================================

# --- Settings ---
PLUGIN_NAME="PomBiss"
PLUGIN_VERSION="2.8"
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/PomBiss"
GITHUB_USER="Shr776"
GITHUB_REPO="PomBiss"
GITHUB_BRANCH="main"
GITHUB_RAW="https://raw.githubusercontent.com/${GITHUB_USER}/${GITHUB_REPO}/${GITHUB_BRANCH}"
GITHUB_API="https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/git/trees/${GITHUB_BRANCH}?recursive=1"
TEMP_DIR="/tmp/pombiss_install"
LOG_FILE="/tmp/pombiss_install.log"

# Files that must exist, otherwise the installation is aborted
CRITICAL_FILES="__init__.py plugin.py version.txt"

: > "$LOG_FILE"
