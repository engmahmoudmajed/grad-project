# Assets

Place the following font files in this folder:

| File | Source |
|------|--------|
| `PixelOperator.ttf` | https://www.dafont.com/pixel-operator.font |
| `lineawesome-webfont.ttf` | https://icons8.com/line-awesome (download the webfont package) |

These fonts are used by the OLED display module (`oled_display.py`).

If the fonts cannot be found at runtime, the system will automatically fall back to
PIL's built-in default font (no icons, but text will still display correctly).
