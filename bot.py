#!/usr/bin/env python3
"""Self-play bot for Super Block Bros.

Plays the level automatically (headless), with optional frame recording
(for GIF capture) and per-frame event logging.

Usage:
  .venv/bin/python bot.py                      # play once, print stats + events
  .venv/bin/python bot.py --record frames      # also save a screenshot every 2nd frame
  .venv/bin/python bot.py --record f --log run.jsonl
  .venv/bin/python bot.py --no-jump            # "dumb" bot: only jumps at walls
                                               # (dies to goombas/pits on purpose)

Then make a GIF from the frames dir:
  ffmpeg -framerate 30 -start_number 1 -i frames/f%04d.png \\
    -vf "scale=480:-1,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" out.gif
Use -start_number A and -frames:v N to cut a segment (A = frame//2 of the
game frame you want to start at; see the --log jsonl for "rec" indexes).
"""
import argparse
import json
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mario

T = mario.TILE


def play(record=None, log=None, no_jump=False, win_hold=90, max_time_s=240):
    g = mario.Game()

    class K:
        def __init__(s, k):
            s.k = k

        def __getitem__(s, k):
            return k in s.k

    held = set()
    pygame.key.get_pressed = lambda: K(held)

    events = []
    win_frames = 0
    frame = 0
    while frame < 60 * max_time_s:
        frame += 1
        held.clear()
        held.add(pygame.K_RIGHT)
        if g.state == "play":
            p = g.player
            r = p.rect()
            feet = (r.bottom + 4) // T
            ax_ = int(r.right + 4) // T
            pit = ((ax_, feet) not in g.solids and
                   (ax_ + 1, feet) not in g.solids) and p.on_ground
            wall = p.on_ground and p.vx == 0.0 and any(
                (ax_, rr) in g.solids
                for rr in range(r.top // T, r.bottom // T + 1))
            coin = any((not c.taken) and 0 <= (c.x - (p.x + p.W)) < 90 and c.y < p.y - 8
                       for c in g.coins)
            if wall and p.on_ground:
                held.add(pygame.K_SPACE)  # both bot modes jump at walls
            elif not no_jump and (pit or coin) and p.on_ground:
                held.add(pygame.K_SPACE)

        prev_score, prev_lives, prev_state = g.score, g.lives, g.state
        g.update()
        g.draw()

        # event detection
        ev = None
        if g.lives < prev_lives:
            ev = "death"
        elif g.state == "win" and prev_state == "play":
            ev = "flag"
        elif g.score - prev_score == 100:
            ev = "stomp"
        elif g.score - prev_score == 50:
            ev = "coin"

        rec_idx = None
        if record and frame % 2 == 0:
            rec_idx = frame // 2
            os.makedirs(record, exist_ok=True)
            pygame.image.save(g.screen, f"{record}/f{rec_idx:04d}.png")
        if log:
            with open(log, "a") as f:
                f.write(json.dumps({
                    "frame": frame, "rec": rec_idx,
                    "x": round(g.player.x, 1), "y": round(g.player.y, 1),
                    "state": g.state, "score": g.score, "coins": g.coins_got,
                    "lives": g.lives, "event": ev, "on_ground": g.player.on_ground,
                }) + "\n")
        if ev:
            events.append((frame, ev))

        if g.state == "win":
            win_frames += 1
            if win_frames >= win_hold:
                break
        if g.state == "gameover":
            break

    print(f"frames: {frame}  state: {g.state}  score: {g.score}  "
          f"coins: {g.coins_got}  lives: {g.lives}")
    for f_, e in events:
        print(f"  f{f_:4d} {e}")
    return g, events


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--record", metavar="DIR", help="dir to save frames/")
    ap.add_argument("--log", metavar="FILE", help="jsonl per-frame log")
    ap.add_argument("--no-jump", action="store_true",
                    help="dumb bot: only jumps at walls, dies to goombas/pits")
    a = ap.parse_args()
    if a.log:
        open(a.log, "w").close()
    play(a.record, a.log, a.no_jump)
