# Minimal pygame scaffold for Pacman GUI.
try:
    import pygame
except Exception as e:
    print("Pygame is required for the GUI. Install with: pip install pygame")
    print("Detail:", e)
    raise SystemExit(0)

import sys
from typing import List, Tuple

CELL = 32
FPS = 30

SAMPLE = [
    "%%%%%%%%%%%%",
    "%P....   E%",
    "%   %  %  %",
    "%   O     %",
    "%   %  %  %",
    "%%%%%%%%%%%%",
]

def parse_grid(grid: List[str]):
    start = None; foods = set(); exit_pos = None; pies = set()
    for r,row in enumerate(grid):
        for c,ch in enumerate(row):
            if ch == 'P': start = (r,c)
            elif ch == '.': foods.add((r,c))
            elif ch == 'E': exit_pos = (r,c)
            elif ch == 'O': pies.add((r,c))
    return start, foods, exit_pos, pies

def draw_grid(screen, grid, pac, foods, exit_pos, pies, ttl, step_mod):
    screen.fill((0,0,0))
    R, C = len(grid), len(grid[0])
    for r in range(R):
        for c in range(C):
            rect = pygame.Rect(c*CELL, r*CELL, CELL, CELL)
            ch = grid[r][c]
            if ch == '%':
                pygame.draw.rect(screen, (80,80,80), rect)
            else:
                pygame.draw.rect(screen, (20,20,20), rect)
                pygame.draw.rect(screen, (40,40,40), rect, 1)
            if (r,c) in pies:
                pygame.draw.circle(screen, (200,120,0), rect.center, CELL//6)
            if (r,c) in foods:
                pygame.draw.circle(screen, (220,220,220), rect.center, CELL//10)
            if exit_pos == (r,c):
                pygame.draw.rect(screen, (0,120,200), rect, 2)

    prect = pygame.Rect(pac[1]*CELL, pac[0]*CELL, CELL, CELL)
    pygame.draw.circle(screen, (255,200,0), prect.center, CELL//2 - 2)

    font = pygame.font.SysFont(None, 20)
    hud = font.render(f"TTL: {ttl}   step%30: {step_mod}", True, (255,255,255))
    screen.blit(hud, (8, CELL*len(grid)+6))

def main():
    grid = SAMPLE
    start, foods, exit_pos, pies = parse_grid(grid)
    pac = list(start); ttl = 0; step_mod = 0
    R, C = len(grid), len(grid[0])
    width, height = C*CELL, R*CELL + 28

    pygame.init()
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                dr = dc = 0
                if event.key == pygame.K_UP: dr = -1
                elif event.key == pygame.K_DOWN: dr = +1
                elif event.key == pygame.K_LEFT: dc = -1
                elif event.key == pygame.K_RIGHT: dc = +1

                nr, nc = pac[0]+dr, pac[1]+dc
                if 0 <= nr < R and 0 <= nc < C:
                    wall = (grid[nr][nc] == '%')
                    if not wall or ttl > 0:
                        pac = [nr, nc]; step_mod = (step_mod + 1) % 30
                        ttl = max(0, ttl-1)
                # collect
                if tuple(pac) in foods: foods.remove(tuple(pac))
                if tuple(pac) in pies: ttl = 5; pies.remove(tuple(pac))

        draw_grid(screen, grid, tuple(pac), foods, exit_pos, pies, ttl, step_mod)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit(); sys.exit(0)

if __name__ == "__main__":
    main()
