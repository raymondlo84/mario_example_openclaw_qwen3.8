# Super Block Bros

A simple Mario-style platformer built with pygame. All graphics are drawn
procedurally — no image assets needed.

## Play

```bash
./run.sh        # creates the venv and installs pygame on first run
```

Or manually:

```bash
python3 -m venv .venv && .venv/bin/pip install pygame
.venv/bin/python mario.py
```

## Controls

| Key | Action |
|-----|--------|
| Arrows / A-D | Move |
| Space / W / Up | Jump |
| R | Restart (game over / win / anytime) |
| Esc | Quit |

## Features

- Tile-based collision (ground, bricks, pipes)
- Goombas: stomp from above for +100, side-touch costs a life (3 lives)
- Spinning coins (+50 each)
- Flag finish with level-clear screen
- Scrolling camera, parallax hills and clouds
- HUD with score / coins / lives
