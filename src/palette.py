"""Folder colors, taken from Catppuccin Mocha (https://catppuccin.com/palette)."""

# name -> (menu label, hex color)
COLORS = {
    "mauve":    ("Lilla",     "#cba6f7"),
    "lavender": ("Lavendel",  "#b4befe"),
    "blue":     ("Blå",       "#89b4fa"),
    "sky":      ("Himmelblå", "#89dceb"),
    "teal":     ("Turkis",    "#94e2d5"),
    "green":    ("Grønn",     "#a6e3a1"),
    "yellow":   ("Gul",       "#f9e2af"),
    "peach":    ("Oransje",   "#fab387"),
    "red":      ("Rød",       "#f38ba8"),
    "pink":     ("Rosa",      "#f5c2e7"),
    "gray":     ("Grå",       "#9399b2"),
}


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
