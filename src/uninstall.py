"""Puts every colored folder back to its normal icon, removes the right-click
menu and deletes %LOCALAPPDATA%\\Programs\\FolderColors."""

import shutil
import winreg

from install import INSTALL_DIR, MENU_KEY, SUBMENU_KEY


def delete_tree(path):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0,
                            winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                except OSError:
                    break
                delete_tree(rf"{path}\{child}")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except FileNotFoundError:
        pass


def main():
    import foldercolor
    print("Resetting colored folders...")
    foldercolor.reset_all()

    print("Removing the right-click menu")
    delete_tree(MENU_KEY)
    delete_tree(SUBMENU_KEY)

    print(f"Deleting {INSTALL_DIR}")
    shutil.rmtree(INSTALL_DIR, ignore_errors=True)
    print("Done.")


if __name__ == "__main__":
    main()
