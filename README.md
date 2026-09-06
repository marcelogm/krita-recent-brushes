# Recent Brushes

[![CI](https://github.com/marcelogm/krita-recent-brushes/actions/workflows/ci.yml/badge.svg)](https://github.com/marcelogm/krita-recent-brushes/actions/workflows/ci.yml)

A Krita docker that lists the brush presets you have used recently, so you can
switch back to them with one click instead of digging through the preset
chooser.

## What it does

- Shows the presets you have used. The *Smart (Frecency)* mode ranks them by
  how often and how recently you picked them, using the same frecency
  algorithm as [zoxide](https://github.com/ajeetdsouza/zoxide)
  ([algorithm](https://github.com/ajeetdsouza/zoxide/wiki/Algorithm)):
  brushes used in the last hour rank highest, then the last day, then the
  last week. The *Recent* mode simply lists the last ones you used.
- Click a preset to make it the active brush.
- Pick the mode with the combo at the top left.
- The gear button opens the settings; *Max* sets how many presets to keep.
- Right-click a preset to ignore it. Ignored presets never show up again;
  the *Ignored brushes* button lets you restore them.
- The *Clear history* button empties the list.
- The history lives in `~/.local/share/krita/recent_brushes_history.json`.

Krita only started emitting a signal when the brush preset changes in 6.0.3.
To keep working on 5.2 and earlier 6.0 releases, the plugin polls the active
view a few times per second while the docker is visible. Switching to the
signal is planned once 6.0.3 is common.

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
`PyQt5`). CI runs them on Python 3.10 (bundled with Krita 5.2), 3.13 (bundled
with Krita 6.0) and 3.14, and fails below 95% coverage:

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest
.venv/bin/ruff check .
```

## License

Copyright (C) 2026 Marcelo Martins. Released under the [GPL-3.0](LICENSE).
