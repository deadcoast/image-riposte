"""Foreground-only palettes. Terminal background ownership always stays with the host."""
from __future__ import annotations

# Exact user-supplied goks / greys of knights sunset tokens. Gaps are intentional.
GOKS = {
    "gokn0": "#2E3440", "gokn1": "#3B4252", "gokn2": "#434C5E",
    "gokn4": "#D8DEE9", "gokn5": "#E5E9F0", "gokn6": "#ECEFF4",
    "gokn7": "#8FBCBB", "gokn8": "#88C0D0", "gokn9": "#81A1C1",
    "gokn11": "#BF616A", "gokn12": "#D08770", "gokn13": "#EBCB8B",
}
_COMMON = {"bg": "default", "panel": "default", "raised": "default"}
PALETTES = {
    "goks": {**GOKS, **_COMMON, "text": "default", "line": GOKS["gokn9"],
             "muted": GOKS["gokn9"], "accent": GOKS["gokn8"], "ink": GOKS["gokn6"],
             "warn": GOKS["gokn13"], "danger": GOKS["gokn11"], "white": GOKS["gokn6"],
             "value": GOKS["gokn7"], "number": GOKS["gokn12"], "label": GOKS["gokn9"],
             "good": GOKS["gokn8"], "code": GOKS["gokn12"], "docstring": GOKS["gokn2"]},
    "dark": {**_COMMON, "text": "default", "line": "#77818f", "muted": "#a6aeba",
             "accent": "#afc8ef", "ink": "#eeeeee", "warn": "#e2c18b", "danger": "#ee9292",
             "white": "#ffffff", "value": "#afd3d9", "number": "#e7ae91", "label": "#a6aeba",
             "good": "#afc8ef", "code": "#e7ae91", "docstring": "#77818f"},
    "light": {**_COMMON, "text": "default", "line": "#687484", "muted": "#536478",
              "accent": "#255b8c", "ink": "#263344", "warn": "#826010", "danger": "#a43837",
              "white": "#263344", "value": "#38676a", "number": "#935438", "label": "#536478",
              "good": "#255b8c", "code": "#935438", "docstring": "#687484"},
    "mono": {**_COMMON, **{key: "default" for key in ("text", "line", "muted", "accent", "ink",
              "warn", "danger", "white", "value", "number", "label", "good", "code", "docstring")}},
}
THEMES = tuple(PALETTES)
