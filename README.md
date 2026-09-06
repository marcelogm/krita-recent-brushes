# Recent Brushes

[![CI](https://github.com/marcelogm/krita-recent-brushes/actions/workflows/ci.yml/badge.svg)](https://github.com/marcelogm/krita-recent-brushes/actions/workflows/ci.yml)

A Krita docker that lists the brush presets you have used recently, so you can
switch back to them with one click instead of digging through the preset
chooser.

## What it does

- Shows the presets you have used, ranked by how often and how recently you
  picked them. The ranking is the same frecency algorithm used by
  [zoxide](https://github.com/ajeetdsouza/zoxide)
  ([algorithm](https://github.com/ajeetdsouza/zoxide/wiki/Algorithm)): brushes
  used in the last hour rank highest, then the last day, then the last week.
- Click a preset to make it the active brush.
- Set how many presets to keep with the spinner at the top.
- Right-click a preset to ignore it. Ignored presets never show up again;
  the *Ignored* button lets you restore them.
- *Clear* empties the list.
- The history lives in `~/.local/share/krita/recent_brushes_history.json`.

## Install

In Krita, go to *Tools > Scripts > Import Python Plugin from Web*, paste

```
https://github.com/marcelogm/krita-recent-brushes
```

and confirm. Then enable *Recent Brushes* in *Settings > Configure Krita >
Python Plugin Manager*, restart Krita, and open the docker from
*Settings > Dockers > Recent Brushes*.

## Development

The plugin lives in `pykrita/`, mirroring Krita's own plugin folder. The
tests run outside Krita against a fake `krita` module and need `PyQt6` (or
`PyQt5`):

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest
.venv/bin/ruff check .
```

## License

[GPL-3.0](LICENSE).
