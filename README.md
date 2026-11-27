# Puzzle Maker — jigsaw cut lines for Rayforge

An addon for [Rayforge](https://rayforge.org) (and a standalone generator)
that creates **laser-ready jigsaw puzzle cut lines**: a grid of pieces with
interlocking tabs, optional tab jitter, an optional rounded border, and a
reproducible seed.

The tab geometry is a faithful port of Draradech's
[`jigsaw.html`](https://github.com/Draradech/jigsaw) (CC0), the generator
behind most online jigsaw tools. That means the figures are proven to cut
well, and a seed produces the same puzzle here as it does there.

```
┌───────────┬───────────┬───────────┐
│           │           │           │
├────╮  ╭───┼───╮  ╭────┼────╮  ╭───┤
│    ╰──╯   │   ╰──╯    │    ╰──╯   │
├───────────┼───────────┼───────────┤
│           │           │           │
└───────────┴───────────┴───────────┘
```

## What you get

In Rayforge: **Tools ▸ Create Puzzle…** opens a dialog with a live preview.
Pressing *Add to Document* creates a new layer holding

* one workpiece with all cut lines (border + interior grid), and
* a **Contour** step, so the puzzle is immediately cuttable.

Everything is placed centred inside your machine's work area, in a single
undo step. From there a *raster* image can be engraved before the cut by
putting the picture on a second layer — standard Rayforge workflow.

Outside Rayforge, the same engine runs on the command line:

```bash
python3 -m puzzle_maker.cli --columns 6 --rows 4 --width 200 --height 150 \
    --seed 7 -o puzzle.svg
```

## Features

| Setting | What it does |
|---|---|
| Width / height | Physical size on the material, in mm |
| Columns / rows | Number of pieces (any grid, not just square) |
| Seed | Same seed → same puzzle; share it to reproduce a layout |
| Tab size | How pronounced the tabs are (percent of a cell edge) |
| Jitter | Randomness of tab placement and shape |
| Corner radius | Rounded outer border, e.g. for a nicer look in wood |
| Add a Contour step | Whether the cut operation is created for you |

The dialog **remembers the last values you used** — including the seed — so a
puzzle only has to be set up once; *Reset* returns to the built-in defaults.
The values live in Rayforge's addon data directory
(`<config>/addon_data/puzzle_maker/last_puzzle.yaml`), so they travel with the
rest of your configuration, including a shared config on a NAS.

## Installing

### As a Rayforge addon

Rayforge installs addons from a git repository. In Rayforge open
*Settings ▸ Addons ▸ Add* and point it at this repository
(`https://github.com/kuerio/rayforge-addon-puzzle`), then pick a version
tag (`v0.1.0` or newer).

Alternatively, for development, symlink the package into your addon
directory and restart Rayforge:

```bash
git clone https://github.com/kuerio/rayforge-addon-puzzle
ln -s "$PWD/rayforge-addon-puzzle" ~/.config/rayforge/addons/puzzle_maker
```

The addon requires Rayforge 1.14 or newer and `api_version` 24 (the
version this was developed against). Rayforge logs `Config dir is …` on
startup if you are unsure where your config lives.

### Standalone use

No Rayforge, GTK or third-party packages are needed for the generator
itself — only Python 3.10+:

```bash
git clone https://github.com/kuerio/rayforge-addon-puzzle
cd rayforge-addon-puzzle
python3 -m puzzle_maker.cli --pieces 24 -o puzzle.svg
python3 scripts/demo.py      # a few samples in out/
```

## How it works

```
puzzle_maker/
├── core/            dependency-free geometry (testable, reusable)
│   ├── geometry.py  lines, cubic Béziers, bounds, Y flip
│   ├── rng.py       the reference sin(seed)-fract generator
│   ├── jigsaw.py    grid, tabs, jitter → paths
│   └── svg.py       one <path> element with one subpath per cut line
├── commands/        the editor command that adds a puzzle to the document
├── widgets/         GTK dialog, cairo preview
├── backend.py       registers the command (loaded in all processes)
└── frontend.py      registers the Tools menu entry (main process only)
```

Two deliberate choices:

* **One `<path>` element.** Rayforge's SVG importer turns one path element
  into one workpiece, so the whole puzzle lands as a single item.
* **No custom Rayforge step.** Puzzles are ordinary vector geometry, so the
  bundled Contour step does the cutting. A custom step would only add
  surface area for things to break.

## Development

```bash
python3 -m unittest discover -s tests -v   # no dependencies needed
python3 scripts/validate_addon.py          # manifest + layout checks
python3 scripts/demo.py                    # write samples to out/
```

`scripts/validate_addon.py` also enforces that `puzzle_maker/core/` never
imports Rayforge, GTK, numpy, cairo or pyvips, so the geometry stays
portable and testable.

## Compatibility / status

* **Cross-platform:** pure Python plus GTK4/Libadwaita (which Rayforge
  already requires). No compiled dependencies, no platform-specific paths,
  so the addon works on Linux, Windows and macOS.
* **Not yet verified against a running Rayforge build.** The core geometry
  and the SVG output are covered by unit tests; the Rayforge-facing code
  follows the same patterns as the bundled `laser_essentials` addon
  (`SvgImporter` + `PassthroughSpec`, `AddLayerAndSetActiveCommand`,
  `ListItemCommand`, `register_commands`, `register_actions`), but it has
  not been executed inside Rayforge yet. Expect a short round of fixes
  during the first install.

## Known issues / changelog

* **0.2.0** — the dialog remembers the last used parameters and gained a
  *Reset* button; `PuzzleParams` can round-trip to plain data
  (`to_dict`/`from_dict`), covered by tests.
* **0.1.1** — the generated Contour step is clamped to the machine's own
  speed limits (`cut_speed`, `travel_speed`); before, Rayforge flagged it
  with "travel_speed 5000 mm/min is above the machine's maximum".
* **0.1.0** — first version.

## Roadmap

* Live preview of an engraved image behind the cut lines.
* Interior "knob" variants (organic, fractal) besides the classic tabs.
* Optional per-piece numbering or labels for glue-up guides.
* Kerf-aware gap between pieces for tighter fits.

## Credits & license

MIT. The tab geometry and the random generator are ported from
[Draradech's jigsaw generator](https://github.com/Draradech/jigsaw), which
is released as CC0; the port keeps the same numbers so seeds are
interchangeable. Rayforge is a separate project by Samuel Abels and
contributors.
