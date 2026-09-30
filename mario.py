#!/usr/bin/env python3
"""
Super Block Bros — a simple Mario-style platformer.
Runs with pygame; all graphics are drawn procedurally (no assets needed).

Controls:
  Move:  A/D or Left/Right arrows
  Jump:  W, Up arrow, or Space
  Restart after game over/win: R
  Quit:  Esc

Run:  .venv/bin/python mario.py
"""

import math
import random
import sys

import pygame

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TILE = 40
WIDTH, HEIGHT = 960, 540
GRAVITY = 0.55
MOVE_SPEED = 5.0
JUMP_SPEED = 14.5
MAX_FALL = 16.0
FRICTION = 0.82

SKY = (92, 148, 252)
GROUND_TOP = (120, 84, 50)
GROUND_BODY = (160, 106, 60)
BRICK = (188, 96, 50)
BRICK_DARK = (120, 52, 24)
PIPE_GREEN = (64, 176, 96)
PIPE_DARK = (28, 110, 56)
CLOUD = (255, 255, 255)

WHITE = (255, 255, 255)
BLACK = (20, 20, 24)
RED = (220, 40, 40)
YELLOW = (250, 204, 21)
BLUE = (48, 96, 220)

FONT_SIZE = 22

# Level layout: strings of characters
#   # ground   B brick   P pipe (2 tiles tall)   C coin
#   F flag pole   G goomba spawn   . empty
LEVEL_LINES = [
    "..........................................................................",
    "..........................................................................",
    "..........................................................................",
    "..........................................................................",
    "..........................................................................",
    "..........................................................................",
    "..........................................................................",
    "..........................................................................",
    ".........CCC..............................CCC.............................",
    ".........BBB......CC.....BBB.....CC.......BBB.....CC......BBB.....CC......",
    "..........................................................................",
    "..........................................................................",
    "........G.....P.....G...............P.G...............PG........G.....F...",
    "############################..################..##########################",
]
LEVEL_W = len(LEVEL_LINES[0]) * TILE
LEVEL_H = len(LEVEL_LINES) * TILE


def parse_level():
    """Return (solids set, coins dict, goombas list, flag x, ground_top_y)."""
    solids = set()          # (col, row) tiles that block movement
    coins = {}              # (col, row) -> True
    goombas = []
    flag_x = None
    for row, line in enumerate(LEVEL_LINES):
        for col, ch in enumerate(line):
            x, y = col * TILE, row * TILE
            if ch == "#":
                solids.add((col, row))
            elif ch == "B":
                solids.add((col, row))
            elif ch == "P":
                solids.add((col, row))
                solids.add((col, row - 1))
            elif ch == "C":
                coins[(col, row)] = True
            elif ch == "G":
                goombas.append(Goomba(x, y))
            elif ch == "F":
                flag_x = x + TILE // 2
    ground_top = (len(LEVEL_LINES) - 1) * TILE
    return solids, coins, goombas, flag_x, ground_top


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
class Player:
    W, H = 30, 42

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = 0.0, 0.0
        self.on_ground = False
        self.facing = 1  # 1 right, -1 left
        self.walking = 0  # walk-cycle phase

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    def update(self, keys, solids):
        ax = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            ax -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            ax += 1
        if ax:
            self.facing = ax
            self.vx += ax * 0.9
            self.vx = max(-MOVE_SPEED, min(MOVE_SPEED, self.vx))
            if self.on_ground:
                self.walking += 0.25
        else:
            self.vx *= FRICTION
            if abs(self.vx) < 0.05:
                self.vx = 0.0

        jumping = keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]
        if jumping and self.on_ground:
            self.vy = -JUMP_SPEED
            self.on_ground = False

        self.vy = min(self.vy + GRAVITY, MAX_FALL)

        # X axis
        nx, _, hit_x = move_axis(self.x, self.y, self.W, self.H, self.vx, 0.0, solids)
        self.x = nx
        if hit_x:
            self.vx = 0.0
        # Y axis
        _, ny, hit_y = move_axis(self.x, self.y, self.W, self.H, 0.0, self.vy, solids)
        self.y = ny
        if hit_y:
            self.vy = 0.0
        self.on_ground = (self.vy >= 0.0) and grounded(self.x, self.y, self.W, self.H, solids)

    def draw(self, surf, cam_x):
        x, y = int(self.x - cam_x), int(self.y)
        # hat
        pygame.draw.rect(surf, RED, (x + 3, y, self.W - 6, 7), border_radius=3)
        pygame.draw.rect(surf, RED, (x + (2 if self.facing > 0 else -1), y + 4, self.W - 4, 4))
        # face
        pygame.draw.rect(surf, (244, 196, 148), (x + 6, y + 8, self.W - 12, 12), border_radius=4)
        # eyes
        ex = x + (16 if self.facing > 0 else 8)
        pygame.draw.circle(surf, BLACK, (ex, y + 13), 2)
        pygame.draw.rect(surf, BLACK, (ex - 4, y + 7, 8, 3), border_radius=1)  # mustache-ish
        # body / overalls
        pygame.draw.rect(surf, BLUE, (x + 4, y + 20, self.W - 8, 12), border_radius=2)
        pygame.draw.rect(surf, RED, (x + 2, y + 18, self.W - 4, 5))
        # legs
        step = int(math.sin(self.walking) * 3) if self.on_ground else 2
        pygame.draw.rect(surf, BLUE, (x + 5, y + 32, 9, 10 - step), border_radius=2)
        pygame.draw.rect(surf, BLUE, (x + self.W - 14, y + 32, 9, 10 + step), border_radius=2)
        # shoes
        pygame.draw.rect(surf, (90, 50, 20), (x + 4, y + 38 - step, 11, 4), border_radius=2)
        pygame.draw.rect(surf, (90, 50, 20), (x + self.W - 15, y + 38 + step, 11, 4), border_radius=2)


class Goomba:
    W, H = 32, 30
    SPEED = 1.2

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx = -self.SPEED
        self.vy = 0.0
        self.dead = False
        self.squish = 0
        self.bob = random.uniform(0, math.tau)

    def rect(self):
        if self.dead:
            return pygame.Rect(int(self.x), int(self.y + self.H - 10), self.W, 10)
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    def update(self, solids):
        if self.dead:
            self.squish += 1
            return
        self.bob += 0.15
        # gravity
        self.vy = min(self.vy + 0.5, 12.0)
        # X axis
        nx, _, hit_x = move_axis(self.x, self.y, self.W, self.H, self.vx, 0.0, solids)
        self.x = nx
        if hit_x:
            self.vx = -self.vx
            if self.vx == 0:
                self.vx = self.SPEED
        # Y axis
        _, ny, hit_y = move_axis(self.x, self.y, self.W, self.H, 0.0, self.vy, solids)
        self.y = ny
        if hit_y:
            self.vy = 0.0

    def stomp(self):
        self.dead = True

    def draw(self, surf, cam_x):
        x, y = int(self.x - cam_x), int(self.y)
        if self.dead:
            pygame.draw.rect(surf, (110, 62, 30), (x, y + self.H - 8, self.W, 8), border_radius=4)
            return
        bob = int(math.sin(self.bob) * 1.5)
        # body
        pygame.draw.ellipse(surf, (140, 76, 36), (x, y + 6 + bob, self.W, self.H - 6), )
        pygame.draw.ellipse(surf, (170, 96, 48), (x + 4, y + 8 + bob, self.W - 8, self.H - 10))
        # eyes
        pygame.draw.ellipse(surf, WHITE, (x + 7, y + 12 + bob, 7, 9))
        pygame.draw.ellipse(surf, WHITE, (x + self.W - 14, y + 12 + bob, 7, 9))
        pygame.draw.circle(surf, BLACK, (x + 10, y + 18 + bob), 2)
        pygame.draw.circle(surf, BLACK, (x + self.W - 11, y + 18 + bob), 2)
        # angry brows
        pygame.draw.line(surf, BLACK, (x + 6, y + 10 + bob), (x + 14, y + 13 + bob), 2)
        pygame.draw.line(surf, BLACK, (x + self.W - 6, y + 10 + bob), (x + self.W - 14, y + 13 + bob), 2)
        # feet
        pygame.draw.ellipse(surf, (60, 32, 16), (x + 2, y + self.H - 7, 12, 7))
        pygame.draw.ellipse(surf, (60, 32, 16), (x + self.W - 14, y + self.H - 7, 12, 7))


class Coin:
    def __init__(self, col, row):
        self.x = col * TILE + TILE // 2
        self.y = row * TILE + TILE // 2
        self.phase = random.uniform(0, math.tau)
        self.taken = False

    def update(self):
        self.phase += 0.12

    def draw(self, surf, cam_x):
        if self.taken:
            return
        x = int(self.x - cam_x)
        squash = abs(math.sin(self.phase))
        w = max(4, int(22 * squash))
        y = int(self.y + math.sin(self.phase + 1.0) * 3)
        pygame.draw.ellipse(surf, YELLOW, (x - w // 2, y - 11, w, 22))
        pygame.draw.ellipse(surf, (255, 240, 160), (x - w // 2 + 3, y - 8, w - 6, 10))


class Flag:
    def __init__(self, x, ground_top):
        self.x = x
        self.top = ground_top - 6 * TILE
        self.ground_top = ground_top
        self.won = False
        self.slide = 0.0

    def update(self, player_bottom_near_ground):
        if self.won and self.slide < (self.ground_top - self.top):
            self.slide = min(self.ground_top - self.top, self.slide + 3)

    def draw(self, surf, cam_x):
        x = int(self.x - cam_x)
        top = int(self.top + self.slide)
        pygame.draw.rect(surf, (160, 170, 180), (x - 3, self.top, 6, self.ground_top - self.top))
        pygame.draw.rect(surf, (120, 130, 140), (x - 3, self.top, 2, self.ground_top - self.top))
        pygame.draw.circle(surf, (220, 220, 120), (x, self.top - 6), 8)
        pygame.draw.polygon(surf, RED,
                            [(x + 3, top), (x + 34, top + 14), (x + 3, top + 28)])
        pygame.draw.polygon(surf, WHITE,
                            [(x + 9, top + 7), (x + 22, top + 14), (x + 9, top + 21)])


# ---------------------------------------------------------------------------
# Collision helpers
# ---------------------------------------------------------------------------
def tile_at(col, row, solids):
    return (col, row) in solids


def _tiles_spanning(x, y, w, h):
    """Yield solid (tx, ty) tiles that a float rect could overlap."""
    c0, c1 = int(x) // TILE, int(x + w - 0.001) // TILE
    r0, r1 = int(y) // TILE, int(y + h - 0.001) // TILE
    for c in range(c0, c1 + 1):
        for r in range(r0, r1 + 1):
            yield c, r


def _overlaps(x0, y0, w, h, x1, y1, w1, h1):
    return x0 < x1 + w1 and x1 < x0 + w and y0 < y1 + h1 and y1 < y0 + h


def move_axis(x, y, w, h, dx, dy, solids):
    """Axis-separated move: one of dx/dy is 0.
    Returns (new_x, new_y, hit) where hit means the axis was blocked.
    Only corrects collisions against tiles NOT overlapped before the move,
    so resting on a surface never counts as a collision."""
    nx, ny = x + dx, y + dy
    hit = False
    for c, r in _tiles_spanning(nx, ny, w, h):
        if (c, r) not in solids:
            continue
        tx, ty = c * TILE, r * TILE
        if _overlaps(x, y, w, h, tx, ty, TILE, TILE):
            continue  # already overlapping before this move: not our collision
        if dy != 0:
            ny = (ty - h) if dy > 0 else (ty + TILE)
        else:
            nx = (tx - w) if dx > 0 else (tx + TILE)
        hit = True
    return nx, ny, hit


def grounded(x, y, w, h, solids):
    """Is there solid ground within 1px below the feet?"""
    for fx in (x + 3.0, x + w - 3.0):
        c, r = int(fx) // TILE, int(y + h + 1) // TILE
        if (c, r) in solids:
            return True
    return False


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------
class Background:
    def __init__(self, seed=7):
        rnd = random.Random(seed)
        self.clouds = [(rnd.randint(0, LEVEL_W), rnd.randint(40, 190), rnd.uniform(0.7, 1.4))
                       for _ in range(26)]
        self.hills = [(rnd.randint(0, LEVEL_W), rnd.randint(60, 140)) for _ in range(18)]

    def draw(self, surf, cam_x):
        surf.fill(SKY)
        for hx, h in self.hills:
            sx = int(hx - cam_x * 0.4)
            if -300 < sx < WIDTH + 300:
                pygame.draw.circle(surf, (110, 190, 120), (sx, HEIGHT - 80), h)
                pygame.draw.circle(surf, (80, 170, 100), (sx, HEIGHT - 80), h - 20)
        for cx, cy, s in self.clouds:
            sx = int(cx - cam_x * 0.7)
            if -200 < sx < WIDTH + 200:
                r = int(18 * s)
                for dx, dy, rr in ((-r, 4, r), (0, 0, int(r * 1.2)), (r, 4, r)):
                    pygame.draw.circle(surf, CLOUD, (sx + dx, cy + dy), rr)
                    pygame.draw.circle(surf, (235, 240, 255), (sx + dx, cy + dy + 4), rr - 4)


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Super Block Bros")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("dejavusansmono", FONT_SIZE, bold=True)
        self.font_small = pygame.font.SysFont("dejavusansmono", 15, bold=True)
        self.bg = Background()
        self.score = 0
        self.lives = 3
        self.coins_got = 0
        self.reset(hard=False)

    def reset(self, hard=True):
        self.solids, self.coins_map, self.goomba_list, self.flag_x, self.ground_top = parse_level()
        self.player = Player(2 * TILE, self.ground_top - Player.H)
        self.goombas = self.goomba_list
        self.coins = [Coin(c, r) for (c, r) in self.coins_map]
        self.flag = Flag(self.flag_x, self.ground_top)
        if hard:
            self.score = 0
            self.lives = 3
            self.coins_got = 0
        self.cam_x = 0
        self.state = "play"   # play | dead | gameover | win
        self.state_timer = 0
        self.death_timer = 0
        self.win_t = 0
        self.messages = []

    def msg(self, text, life=90):
        self.messages.append((text, life))

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return False
                if e.key == pygame.K_r:
                    if self.state in ("gameover", "win") or self.lives <= 0:
                        self.reset(hard=True)
                    elif self.state == "dead":
                        self.state_timer = 1
                    elif self.state == "play":
                        self.reset(hard=True)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                pass  # jump handled in update
        return True

    def die(self):
        if self.state != "play":
            return
        self.lives -= 1
        self.state = "dead"
        self.state_timer = 70
        self.death_timer = 0

    def update(self):
        keys = pygame.key.get_pressed()
        if self.state == "play":
            self.player.update(keys, self.solids)
            self.goomba_update()
            self.coin_update()
            self.flag.update(True)
            # camera
            target = self.player.x + self.player.W // 2 - WIDTH // 2
            self.cam_x = max(0, min(target, LEVEL_W - WIDTH))
            # fell off
            if self.player.y > LEVEL_H + 100:
                self.die()
            # flag reached
            pr = self.player.rect()
            if pr.right >= self.flag.x - 4 and not self.flag.won:
                self.flag.won = True
                self.score += 1000
                self.msg("LEVEL CLEAR! +1000", 200)
                self.state = "win"
                self.win_t = 0
        elif self.state == "dead":
            self.state_timer -= 1
            self.death_timer += 1
            self.player.y += 2.2  # little tumble
            if self.state_timer <= 0:
                if self.lives <= 0:
                    self.state = "gameover"
                else:
                    px, py = 2 * TILE, self.ground_top - Player.H
                    self.player = Player(px, py)
                    self.state = "play"
        elif self.state == "win":
            self.win_t += 1
            self.flag.update(True)
            self.player.x = min(self.player.x + 2, self.flag.x - 40)
        # messages
        self.messages = [(t, l - 1) for t, l in self.messages if l - 1 > 0]

    def goomba_update(self):
        pr = self.player.rect()
        for g in self.goombas:
            if g.dead and g.squish > 30:
                continue
            # only simulate nearby
            if abs(g.x - self.player.x) < WIDTH * 1.2:
                g.update(self.solids)
            if g.dead:
                continue
            gr = g.rect()
            if gr.colliderect(pr) and pr.centery < gr.centery + 6 and self.state == "play":
                g.stomp()
                self.score += 100
                self.msg("+100", 50)
                self.player.vy = -JUMP_SPEED * 0.6
                self.on_ground_stomp = True
            elif gr.colliderect(pr) and self.state == "play":
                self.die()
            if g.y > LEVEL_H + 100:
                g.dead = True

    def coin_update(self):
        pr = self.player.rect()
        for c in self.coins:
            c.update()
            if not c.taken:
                cr = pygame.Rect(c.x - 11, c.y - 11, 22, 22)
                if cr.colliderect(pr):
                    c.taken = True
                    self.coins_got += 1
                    self.score += 50
                    self.msg("+50", 40)
        # coin bonus
        if self.coins_got > 0 and self.coins_got % 10 == 0:
            pass

    def draw_tile(self, surf, col, row, cam_x, ground_top_row):
        x, y = col * TILE - cam_x, row * TILE
        if x < -TILE or x > WIDTH or y < -TILE or y > HEIGHT + TILE:
            return
        if row >= ground_top_row - 1 and (col, row) in self.solids and row == ground_top_row:
            pygame.draw.rect(surf, GROUND_TOP, (x, y, TILE, TILE))
            pygame.draw.rect(surf, (150, 108, 64), (x, y + 6, TILE, TILE - 6))
            pygame.draw.rect(surf, GROUND_BODY, (x, y + 14, TILE, TILE - 14))
            for dx in (4, 20):
                pygame.draw.circle(surf, (120, 80, 44), (x + dx + 4, y + 26), 4)
        elif (col, row) in self.solids:
            if (col, row - 1) not in self.solids and (col, row + 1) not in self.solids \
                    and (col - 1, row) not in self.solids and (col + 1, row) not in self.solids:
                # pipe top
                pygame.draw.rect(surf, PIPE_GREEN, (x - 4, y, TILE + 8, TILE))
                pygame.draw.rect(surf, PIPE_DARK, (x - 4, y, 6, TILE))
            elif (col, row - 1) in self.solids:
                # pipe body
                pygame.draw.rect(surf, PIPE_GREEN, (x, y, TILE, TILE))
                pygame.draw.rect(surf, PIPE_DARK, (x, y, 6, TILE))
                pygame.draw.rect(surf, (120, 220, 150), (x + TILE - 10, y, 5, TILE))
            else:
                # brick
                pygame.draw.rect(surf, BRICK, (x, y, TILE, TILE))
                pygame.draw.rect(surf, BRICK_DARK, (x, y, TILE, 3))
                pygame.draw.rect(surf, BRICK_DARK, (x, y + TILE // 2, TILE, 3))
                pygame.draw.rect(surf, BRICK_DARK, (x + TILE // 2, y, 3, TILE // 2))
                pygame.draw.rect(surf, BRICK_DARK, (x + 3, y + TILE // 2, 3, TILE // 2))
                pygame.draw.rect(surf, BRICK_DARK, (x + TILE - 6, y + TILE // 2, 3, TILE // 2))

    def draw(self):
        self.bg.draw(self.screen, self.cam_x)
        ground_top_row = self.ground_top // TILE
        for (c, r) in self.solids:
            self.draw_tile(self.screen, c, r, int(self.cam_x), ground_top_row)
        for c in self.coins:
            c.draw(self.screen, self.cam_x)
        self.flag.draw(self.screen, self.cam_x)
        for g in self.goombas:
            if abs(g.x - self.player.x) < WIDTH + 200:
                g.draw(self.screen, self.cam_x)
        if self.state not in ("gameover",):
            self.player.draw(self.screen, self.cam_x)

        # HUD (with drop shadow)
        hud_text = f"SCORE {self.score:06d}   COINS {self.coins_got:02d}   LIVES {self.lives}"
        sh = self.font.render(hud_text, True, BLACK)
        hud = self.font.render(hud_text, True, WHITE)
        self.screen.blit(sh, (14, 12))
        self.screen.blit(hud, (12, 10))

        # floating messages
        for i, (t, l) in enumerate(self.messages):
            m = self.font_small.render(t, True, YELLOW)
            self.screen.blit(m, (WIDTH // 2 - m.get_width() // 2, 90 + i * 22 - (90 - l) // 3))

        if self.state == "dead":
            self.draw_center_text("OOPS!", YELLOW)
        elif self.state == "gameover":
            self.draw_center_text("GAME OVER", RED)
            self.draw_center_text("Press R to restart", WHITE, dy=48)
        elif self.state == "win":
            self.draw_center_text("COURSE CLEAR!", YELLOW)
            self.draw_center_text(f"Final score {self.score}  —  Press R to play again",
                                  WHITE, dy=48)

        # controls hint
        hint = self.font_small.render("Arrows/WASD move  ·  Space jump  ·  R restart  ·  Esc quit",
                                      True, WHITE)
        self.screen.blit(hint, (12, HEIGHT - 24))

        pygame.display.flip()

    def draw_center_text(self, text, color, dy=0, size=None):
        f = self.font if size is None else size
        m = (self.font if size is None else size).render(text, True, color)
        sh = (self.font if size is None else size).render(text, True, BLACK)
        x = (WIDTH - m.get_width()) // 2
        self.screen.blit(sh, (x + 2, 150 + dy + 2))
        self.screen.blit(m, (x, 150 + dy))

    def run(self):
        while True:
            if not self.handle_events():
                break
            self.update()
            self.draw()
            self.clock.tick(60)
        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    Game().run()
