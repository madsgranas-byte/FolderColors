# FolderColors
Colored folder icons for Windows 11, in the [Catppuccin Mocha](https://catppuccin.com/palette) colors.

![The 11 folder colors](docs/preview.png)

The icons are drawn by a small Python script, so there's nothing to download besides Python itself (no Pillow or other packages).

## Install

Run `install.bat`. It:

- draws the icons and copies the program to `%LOCALAPPDATA%\Programs\FolderColors`
- adds **Mappefarge** to the right-click menu of folders (for your user only)
- colors the folders listed in `presets\default.json`

To install a newer version, run `install.bat` again. To remove everything, run `uninstall.bat`. It puts every colored folder back to its normal icon first.

## Use

Right-click a folder and choose **Mappefarge**, then a color. **Standard** puts the normal icon back.

On Windows 11 the menu is under **Vis flere alternativer** (Show more options), or press Shift+F10.

From a terminal:

```
python %LOCALAPPDATA%\Programs\FolderColors\foldercolor.py set "C:\some\folder" blue
python %LOCALAPPDATA%\Programs\FolderColors\foldercolor.py reset "C:\some\folder"
python %LOCALAPPDATA%\Programs\FolderColors\foldercolor.py list
python %LOCALAPPDATA%\Programs\FolderColors\foldercolor.py reset-all
```

Colors: `mauve`, `lavender`, `blue`, `sky`, `teal`, `green`, `yellow`, `peach`, `red`, `pink`, `gray`.

## Presets

A preset is a JSON file that maps folders to colors. `{Desktop}`, `{Documents}`, `{Downloads}`, `{Pictures}`, `{Music}`, `{Videos}` and `{Profile}` are replaced with the real folder paths, and `%VARIABLES%` are expanded:

```json
{
  "{Documents}": "blue",
  "{Desktop}\\IN1000": "peach"
}
```

Apply one with `foldercolor.py preset my-preset.json`.

## How it works

- `src/render.py` draws each folder from rounded rectangles described by signed distance functions, which also gives smooth anti-aliased edges. Every icon is saved as an `.ico` with sizes from 16 to 256 px.
- `src/foldercolor.py` sets the folder's icon in its `desktop.ini` and marks the folder read-only, which is what makes Explorer read that file. Special folders like Documents and Downloads already have a `desktop.ini` with their own icon. That icon is saved as `FolderColorsOriginal` so `reset` can put it back. If the tool created `desktop.ini` itself, `reset` deletes it again.
- The colored folders are listed in `%LOCALAPPDATA%\FolderColors\colored.json`, so `uninstall.bat` knows which ones to reset.
- `src/install.py` adds the menu under `HKEY_CURRENT_USER\Software\Classes\Directory`, so it needs no admin rights.

If Explorer still shows an old icon, run `ie4uinit.exe -show` or restart Explorer.
