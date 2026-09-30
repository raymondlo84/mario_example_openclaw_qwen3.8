# Learnings

Debugging log from building and fixing this game (OpenClaw + Qwen3.8-27B-NVFP4
via vLLM, 2026-09-30). Worth reading if you're generating pygame games with an
LLM, or debugging tile-based platformer physics.

## The three real bugs, in order of discovery

### 1. Level geometry: everything floated in mid-air

The level was originally a 7-row string map; the first "fix" to give the world
vertical room inserted 6 empty rows *below* the ground line. Result: ground at
the bottom of the screen, but pipes/bricks/coins/goombas 7 tiles above it —
an unplayable level where the player just ran under floating junk.

**Lesson:** when changing grid-map dimensions, regenerate the whole map and
*assert* the invariants (every non-ground object sits on or above a support
column; the bottom row is all ground except intended pits). A one-line
`assert` in `parse_level()` would have caught this.

### 2. A broken "collision resolver" (first rewrite)

The first collision pass used a single `collide_tiles(rect, solids)` that
tried to return both x- and y-corrections from one pass. It had an
unreachable code path (guarded on `rect.w >= 0` after an `if rect.w <= 0`
check) and, more importantly, **no notion of which axis the overlap came
from** — it would push the player into the ground when landing, then back
out next frame, forever.

**Lesson:** tile platformers need *axis-separated* movement — move X,
resolve X, move Y, resolve Y — never resolve both axes in one pass.

### 3. The tuple-unpacking bug (the killer)

The rewritten `move_axis(x, y, w, h, dx, dy, solids)` returns
`(new_x, new_y, hit)`. The Y-axis call site read the **first** element into
`ny`:

```python
ny, _, hit_y = move_axis(self.x, self.y, self.W, self.H, 0.0, self.vy, solids)
self.y = ny          # ny was actually new_x  =>  self.y = self.x every frame
```

So every frame the player's y snapped to its x, it sank into the ground row,
and jittered against what *looked* like a wall at the pit edge.

**Lesson:** never name both unpacked values in a way the bug can hide in —
`_, ny, hit_y = move_axis(...)` makes the intent explicit. Even better,
don't return a 3-tuple where two fields are "the same axis value unchanged";
return a small result object or `(y_new, hit)` per axis.

## How the bug was actually found (process notes)

1. **Instrumented traces that lied by omission.** Early traces printed
   `x, y` before/after `update()` and showed `vy` changing but `y` stuck —
   which was *real*, but the obvious conclusion ("move_axis returns wrong
   y") pointed at the wrong function. The value was returned correctly; the
   *caller* misread it.
2. **Statement-by-statement bisection** finally isolated it: a hand-rolled
   copy of `update()` with a print after each line showed `self.y` correct at
   line N, wrong at line N+1.
3. **Disassembly as ground truth.** `dis.dis(Player.update)` proved the
   bytecode stored `ny` into `self.y` — i.e. the file on disk and the
   in-memory function agreed, so the bug was in the *logic*, not a stale
   `.pyc` or a shadowed class.
4. **Unit vs integration.** A minimal `Player.update`-only loop reproduced
   the bug with no game loop, camera, or draw involved — that isolation step
   was the fastest win.

## Verification that counts (for LLM-built GUI apps)

- A "no exception after 300 frames" smoke test is **not** verification.
- **Drive an actual bot** (`bot.py`) and assert on game state: reached flag,
  no stall > N frames, no solid overlap, coins collected, stomps happened.
  `tests/e2e.py` does this — 8 checks, all must pass.
- **Look at pixels.** Save frames on a real display (`DISPLAY=:1` here) and
  view them. Boot/mid/end frames caught the "everything floats in the sky"
  level bug that every numeric test missed.
- **Compare dumb vs smart bot.** Running the same bot with `--no-jump`
  (wall-jumps only) *intentionally* dies to goombas and pits; that run
  validates death/respawn/lives/respawn-position logic, which the winning
  run never exercises.

## Environment notes (this host)

- PEP 668 blocks `pip3 install` system-wide → use a venv
  (`python3 -m venv .venv && .venv/bin/pip install pygame`).
- `SDL_VIDEODRIVER=dummy` for headless; **never** `SDL_VIDEODRIVER=` (empty
  string) — that breaks window creation with `pygame.error: windows not
  available`.
- Real windows: `DISPLAY=:1` is X11 with local auth; `xrandr` shows
  2560x1440.
- GIF from frames: `ffmpeg -framerate 30 -start_number N -i f%04d.png
  -frames:v M -vf "scale=480:-1,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" out.gif`
  (`-frames:v` is an *output* option — after the input, not before).

## Reproducing the self-play

```bash
./run.sh                      # human play
.venv/bin/python bot.py       # full self-play (headless), prints event log
.venv/bin/python bot.py --no-jump --record /tmp/frames --log /tmp/run.jsonl
.venv/bin/python tests/e2e.py # 8-check acceptance suite
```
