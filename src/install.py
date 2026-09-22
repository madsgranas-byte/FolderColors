"""Builds the icons, copies FolderColors to %LOCALAPPDATA%\\Programs\\FolderColors
and adds "Mappefarge" to the right-click menu of folders (for your user only)."""

import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path

from palette import COLORS
from render import build_icons

SRC = Path(__file__).resolve().parent
INSTALL_DIR = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "FolderColors"

MENU_KEY = r"Software\Classes\Directory\shell\FolderColors"
SUBMENU = r"Directory\ContextMenus\FolderColors"
SUBMENU_KEY = "Software\\Classes\\" + SUBMENU
ECF_SEPARATORBEFORE = 0x20


def set_values(path, values):
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE) as key:
        for name, value in values.items():
            kind = winreg.REG_DWORD if isinstance(value, int) else winreg.REG_SZ
            winreg.SetValueEx(key, name, 0, kind, value)


def add_menu(pythonw, script):
    icons = INSTALL_DIR / "icons"
    set_values(MENU_KEY, {
        "MUIVerb": "Mappefarge",
        "Icon": str(icons / "mauve.ico"),
        "ExtendedSubCommandsKey": SUBMENU,
    })
    for i, (name, (label, _)) in enumerate(COLORS.items()):
        entry = rf"{SUBMENU_KEY}\shell\{i:02}_{name}"
        set_values(entry, {"MUIVerb": label, "Icon": str(icons / f"{name}.ico")})
        set_values(entry + r"\command", {"": f'"{pythonw}" "{script}" set "%V" {name}'})
    reset = rf"{SUBMENU_KEY}\shell\99_reset"
    set_values(reset, {
        "MUIVerb": "Standard",
        "Icon": r"%SystemRoot%\System32\imageres.dll,-3",
        "CommandFlags": ECF_SEPARATORBEFORE,
    })
    set_values(reset + r"\command", {"": f'"{pythonw}" "{script}" reset "%V"'})


def main():
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = Path(sys.executable)

    print("Building icons...")
    build_icons(INSTALL_DIR / "icons")

    print(f"Copying to {INSTALL_DIR}")
    for name in ("foldercolor.py", "palette.py"):
        shutil.copy2(SRC / name, INSTALL_DIR / name)
    shutil.copytree(SRC.parent / "presets", INSTALL_DIR / "presets", dirs_exist_ok=True)

    print("Adding 'Mappefarge' to the folder right-click menu")
    add_menu(pythonw, INSTALL_DIR / "foldercolor.py")

    # Ask Explorer to drop cached icons so rebuilt icons show up.
    subprocess.run(["ie4uinit.exe", "-show"], check=False)
    print("Done.")


if __name__ == "__main__":
    main()
