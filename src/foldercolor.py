"""Give a folder a colored icon, or put the normal icon back.

    foldercolor.py set <folder> <color>
    foldercolor.py reset <folder>
    foldercolor.py preset <preset.json>
    foldercolor.py reset-all
    foldercolor.py list

The icon is set through the folder's desktop.ini. Whatever icon the folder had
before (Documents, Downloads and the other special folders have their own) is
saved in desktop.ini, so `reset` puts it back.
"""

import ctypes
import json
import os
import sys
import uuid
from ctypes import wintypes
from pathlib import Path

from palette import COLORS

APP_DIR = Path(__file__).resolve().parent
ICON_DIR = APP_DIR / "icons"
STATE_FILE = Path(os.environ["LOCALAPPDATA"]) / "FolderColors" / "colored.json"

SECTION = "[.shellclassinfo]"
KEY_ICON = "IconResource"
KEY_ORIGINAL = "FolderColorsOriginal"
KEY_CREATED = "FolderColorsCreated"

FILE_ATTRIBUTE_NORMAL = 0x80
FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4
SHCNE_UPDATEDIR = 0x1000
SHCNE_UPDATEITEM = 0x2000
SHCNF_PATHW = 0x5

kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32
shlwapi = ctypes.windll.shlwapi

KNOWN_FOLDERS = {
    "Desktop":   "B4BFCC3A-DB2C-424C-B029-7FE99A87C641",
    "Documents": "FDD39AD0-238F-46AF-ADB4-6C85480369C7",
    "Downloads": "374DE290-123F-4565-9164-E4C79EB9C4A0",
    "Pictures":  "33E28130-4E1E-4676-835A-98395C3BC3BB",
    "Music":     "4BD8D571-6D19-48D3-BE97-422220080E43",
    "Videos":    "18989B1D-99B5-455B-841C-AB7C74E4DDFC",
    "Profile":   "5E6C858F-0E22-4760-9AFE-EA3317B67173",
}


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

    def __init__(self, text):
        u = uuid.UUID(text)
        super().__init__(u.time_low, u.time_mid, u.time_hi_version,
                         (ctypes.c_ubyte * 8)(*u.bytes[8:]))


def known_folder(name):
    path = ctypes.c_wchar_p()
    if shell32.SHGetKnownFolderPath(ctypes.byref(GUID(KNOWN_FOLDERS[name])), 0, None,
                                    ctypes.byref(path)) != 0:
        # Happens when the folder's entry is missing from the registry.
        # Windows then uses the default location in the user's profile.
        fallback = Path(os.environ["USERPROFILE"]) / name
        if fallback.is_dir():
            return str(fallback)
        raise OSError(f"Could not find the {name} folder")
    try:
        return path.value
    finally:
        ctypes.windll.ole32.CoTaskMemFree(path)


def expand(path):
    """Expands {Documents}, {Downloads}, ... and %VARIABLES% in a path."""
    for name in KNOWN_FOLDERS:
        token = "{" + name + "}"
        if token in path:
            path = path.replace(token, known_folder(name))
    return Path(os.path.expandvars(path))


# --- desktop.ini ----------------------------------------------------------

def read_ini(path):
    if not path.exists():
        return None
    data = path.read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = data.decode("utf-16")
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("mbcs")
    return text.splitlines()


def write_ini(path, lines):
    if path.exists():
        kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_NORMAL)
    # UTF-16 with a BOM is what Explorer itself writes, and it handles any path.
    path.write_text("\n".join(lines) + "\n", encoding="utf-16", newline="\r\n")
    kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)


def section_range(lines):
    """(start, end) line indexes of the [.ShellClassInfo] body, or None."""
    for i, line in enumerate(lines):
        if line.strip().lower() == SECTION:
            end = i + 1
            while end < len(lines) and not lines[end].strip().startswith("["):
                end += 1
            return i + 1, end
    return None


def get_key(lines, key):
    found = section_range(lines)
    if found:
        for line in lines[found[0]:found[1]]:
            name, sep, value = line.partition("=")
            if sep and name.strip().lower() == key.lower():
                return value.strip()
    return None


def set_key(lines, key, value):
    """Sets (or with value=None removes) a key in [.ShellClassInfo]."""
    found = section_range(lines)
    if not found:
        if value is None:
            return lines
        lines = ["[.ShellClassInfo]"] + lines
        found = (1, 1)
    start, end = found
    for i in range(start, end):
        name, sep, _ = lines[i].partition("=")
        if sep and name.strip().lower() == key.lower():
            if value is None:
                return lines[:i] + lines[i + 1:]
            lines[i] = f"{key}={value}"
            return lines
    if value is None:
        return lines
    # Insert after the last non-empty line of the section.
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[:end] + [f"{key}={value}"] + lines[end:]


def refresh(folder):
    shell32.SHChangeNotify(SHCNE_UPDATEITEM, SHCNF_PATHW, str(folder), None)
    shell32.SHChangeNotify(SHCNE_UPDATEDIR, SHCNF_PATHW, str(folder.parent), None)


# --- remembering which folders are colored --------------------------------

def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# --- commands --------------------------------------------------------------

def set_color(folder, color):
    folder = Path(folder).resolve()
    if color not in COLORS:
        raise SystemExit(f"Unknown color '{color}'. Choose one of: {', '.join(COLORS)}")
    if not folder.is_dir():
        raise SystemExit(f"Not a folder: {folder}")
    icon = ICON_DIR / f"{color}.ico"
    if not icon.exists():
        raise SystemExit(f"Missing icon {icon}. Run install.bat first.")

    ini = folder / "desktop.ini"
    lines = read_ini(ini)
    created = lines is None
    lines = lines or []

    if get_key(lines, KEY_ORIGINAL) is None and get_key(lines, KEY_CREATED) is None:
        original = get_key(lines, KEY_ICON)
        if original:
            lines = set_key(lines, KEY_ORIGINAL, original)
        else:
            lines = set_key(lines, KEY_CREATED, "1")
    lines = set_key(lines, KEY_ICON, f"{icon},0")
    write_ini(ini, lines)

    # Explorer only reads desktop.ini in folders marked read-only or system.
    shlwapi.PathMakeSystemFolderW(str(folder))
    refresh(folder)

    state = load_state()
    state[str(folder)] = color
    save_state(state)
    print(f"{folder}: {color}{' (new desktop.ini)' if created else ''}")


def reset_color(folder):
    folder = Path(folder).resolve()
    ini = folder / "desktop.ini"
    lines = read_ini(ini)
    state = load_state()
    state.pop(str(folder), None)
    save_state(state)
    if lines is None:
        return

    original = get_key(lines, KEY_ORIGINAL)
    created = get_key(lines, KEY_CREATED)
    if original is None and created is None:
        print(f"{folder}: not colored by FolderColors, left alone")
        return

    lines = set_key(lines, KEY_ICON, original)
    lines = set_key(lines, KEY_ORIGINAL, None)
    lines = set_key(lines, KEY_CREATED, None)

    leftover = [l for l in lines if l.strip() and l.strip().lower() != SECTION]
    if created and not leftover:
        kernel32.SetFileAttributesW(str(ini), FILE_ATTRIBUTE_NORMAL)
        ini.unlink()
        shlwapi.PathUnmakeSystemFolderW(str(folder))
    else:
        write_ini(ini, lines)
    refresh(folder)
    print(f"{folder}: reset")


def apply_preset(preset_file):
    preset = json.loads(Path(preset_file).read_text(encoding="utf-8"))
    for raw_path, color in preset.items():
        folder = expand(raw_path)
        if folder.is_dir():
            set_color(folder, color)
        else:
            print(f"{folder}: does not exist, skipped")


def reset_all():
    for folder in list(load_state()):
        if Path(folder).is_dir():
            reset_color(folder)
    save_state({})


def main(argv):
    if len(argv) >= 3 and argv[0] == "set":
        set_color(argv[1], argv[2])
    elif len(argv) >= 2 and argv[0] == "reset":
        reset_color(argv[1])
    elif len(argv) >= 2 and argv[0] == "preset":
        apply_preset(argv[1])
    elif argv[:1] == ["reset-all"]:
        reset_all()
    elif argv[:1] == ["list"]:
        for folder, color in load_state().items():
            print(f"{color:9} {folder}")
    else:
        print(__doc__)
        print("Colors:", ", ".join(COLORS))
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (SystemExit, Exception) as error:
        # From the right-click menu this runs under pythonw, which has no console.
        message = error.code if isinstance(error, SystemExit) else error
        if sys.stdout is None and not isinstance(message, (int, type(None))):
            ctypes.windll.user32.MessageBoxW(None, str(message), "FolderColors", 0x10)
        raise
