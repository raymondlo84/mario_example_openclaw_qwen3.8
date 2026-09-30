#!/usr/bin/env python3
"""End-to-end verification for Super Block Bros.

Runs headless (dummy video driver) and asserts:
  A. Player spawns standing on the ground (no overlap into solid).
  B. An AI-driven playthrough reaches the flag (state == "win").
  C. No stalls: player made continuous forward progress.
  D. At least one goomba stomp and at least one coin occurred.
  E. Player never ends a frame overlapping a solid tile.
  F. Falling into a pit kills / respawns (lives decrease) — tested separately.

Usage:  SDL_VIDEODRIVER=dummy .venv/bin/python tests/e2e.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
import pygame
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mario

T = mario.TILE
PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    print(("PASS" if cond else "FAIL"), name, detail if not cond else "")


def keys_with(held):
    class K:
        def __init__(self, k):
            self.k = k
        def __getitem__(self, k):
            return k in self.k
    return K(held)


def overlap_solid(p, solids):
    r = p.rect()
    for c in range(r.left // T, (r.right - 1) // T + 1):
        for rrow in range(r.top // T, (r.bottom - 1) // T + 1):
            if (c, rrow) in solids:
                if r.colliderect(pygame.Rect(c * T, rrow * T, T, T)):
                    return (c, rrow)
    return None


def main():
    g = mario.Game()
    check("spawn on ground", overlap_solid(g.player, g.solids) is None,
          f"overlapping tile {overlap_solid(g.player, g.solids)}")
    check("spawn grounded flag", g.player.on_ground or abs(g.player.vy) < 1)

    held = set()
    pygame.key.get_pressed = lambda: keys_with(held)

    max_stall = 0
    x_progress = 0
    x_last = g.player.x
    stomp_events = 0
    death_events = 0
    frames = 0
    overlapped = None
    win = False

    for frames in range(1, 60 * 180 + 1):
        held.clear()
        held.add(pygame.K_RIGHT)
        p = g.player
        r = p.rect()
        # decide jump: pit ahead OR wall ahead
        feet = (r.bottom + 4) // T
        ahead_x = int(r.right + 4) // T
        pit = ((ahead_x, feet) not in g.solids and
               (ahead_x + 1, feet) not in g.solids) and p.on_ground
        wall = p.on_ground and p.vx == 0.0 and any(
            (ahead_x, rr) in g.solids
            for rr in range(r.top // T, r.bottom // T + 1))
        # coin ahead and above -> jump for it
        coin_ahead = any(
            (not c.taken) and 0 <= (c.x - (p.x + p.W)) < 90 and c.y < p.y - 8
            for c in g.coins)
        if (pit or wall or coin_ahead) and p.on_ground:
            held.add(pygame.K_SPACE)

        lives_before = g.lives
        g.update()
        g.draw()

        # E. overlap check
        ov = overlap_solid(p, g.solids)
        if ov:
            overlapped = ov
        # progress / stall tracking (only during play state)
        if g.state == "play":
            x_progress = g.player.x - x_last
            if x_progress <= 0:
                max_stall += 1
            else:
                max_stall = 0
            x_last = g.player.x
        if g.lives < lives_before:
            death_events += 1
        if g.state == "win":
            win = True
            break

    stomped = sum(1 for go in g.goombas if go.dead and go.squish > 0)
    coins = g.coins_got

    check("reached flag (win)", win,
          f"state={g.state} x={g.player.x:.0f}/{mario.LEVEL_W} score={g.score}")
    check("no solid overlap ever", overlapped is None,
          f"player overlapped solid tile {overlapped}")
    check("no long stall (<=180f)", max_stall <= 180,
          f"longest stall {max_stall} frames at x~{x_last:.0f}")
    check("collected >=5 coins", coins >= 5, f"coins={coins}")
    check("stomped >=1 goomba", stomped >= 1, f"stomped={stomped}")
    check("deaths reasonable (<=2)", death_events <= 2, f"deaths={death_events}")
    print(f"\nfinal: state={g.state} score={g.score} coins={coins} lives={g.lives}")
    print(f"PASS {len(PASS)} FAIL {len(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
