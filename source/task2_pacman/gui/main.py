# GUI pygame: ma đi ngang dội tường, teleport 4 góc, xoay mê cung mỗi 30 bước, O -> TTL=5
try:
    import pygame
except Exception as e:
    print("Pygame is required for the GUI. Install with: pip install pygame")
    print("Detail:", e)
    raise SystemExit(0)

import sys
from typing import List, Tuple, Set

CELL = 32
FPS = 30

SAMPLE = [
    "%%%%%%%%%%%%",
    "%P..O...  E%",
    "%   %  %   %",
    "%   O     G%",
    "%   %  %   %",
    "%%%%%%%%%%%%",
]

def rotate_grid_cw(grid: List[str]) -> List[str]:
    R, C = len(grid), len(grid[0])
    return ["".join(grid[R - 1 - r][c] for r in range(R)) for c in range(C)]

def rot_pos_cw(p: Tuple[int,int], R: int, C: int) -> Tuple[int,int]:
    r, c = p
    return (c, R - 1 - r)

def parse_grid(grid: List[str]):
    start = None; foods: Set[Tuple[int,int]] = set(); exit_pos = None; pies: Set[Tuple[int,int]] = set(); ghosts=[]
    for r,row in enumerate(grid):
        for c,ch in enumerate(row):
            if ch == 'P': start = (r,c)
            elif ch == '.': foods.add((r,c))
            elif ch == 'E': exit_pos = (r,c)
            elif ch == 'O': pies.add((r,c))
            elif ch == 'G': ghosts.append([(r,c), +1])  # [pos, dir]
    return start, foods, exit_pos, pies, ghosts

def draw_grid(screen, grid, pac, foods, exit_pos, pies, ghosts, ttl, step_mod):
    screen.fill((0,0,0))
    R, C = len(grid), len(grid[0])
    for r in range(R):
        for c in range(C):
            rect = pygame.Rect(c*CELL, r*CELL, CELL, CELL)
            ch = grid[r][c]
            if ch == '%':
                pygame.draw.rect(screen, (75,75,75), rect)
            else:
                pygame.draw.rect(screen, (20,20,20), rect)
                pygame.draw.rect(screen, (40,40,40), rect, 1)
            if (r,c) in pies:
                pygame.draw.circle(screen, (200,120,0), rect.center, CELL//6)
            if (r,c) in foods:
                pygame.draw.circle(screen, (220,220,220), rect.center, CELL//10)
            if exit_pos == (r,c):
                pygame.draw.rect(screen, (0,120,200), rect, 2)

    # ghosts
    for (gr, gc), d in ghosts:
        grect = pygame.Rect(gc*CELL, gr*CELL, CELL, CELL)
        pygame.draw.circle(screen, (200,50,50), grect.center, CELL//3)

    # pacman
    prect = pygame.Rect(pac[1]*CELL, pac[0]*CELL, CELL, CELL)
    pygame.draw.circle(screen, (255,200,0), prect.center, CELL//2 - 2)

    # HUD
    font = pygame.font.SysFont(None, 20)
    hud = font.render(f"TTL: {ttl}   step%30: {step_mod}", True, (255,255,255))
    screen.blit(hud, (8, CELL*len(grid)+6))

def is_wall(grid: List[str], r: int, c: int) -> bool:
    R, C = len(grid), len(grid[0])
    if 0 <= r < R and 0 <= c < C:
        return grid[r][c] == '%'
    return True

def teleport_if_corner(grid: List[str], r: int, c: int) -> Tuple[int,int]:
    R, C = len(grid), len(grid[0])
    corners = {(0,0):(R-1,C-1),(0,C-1):(R-1,0),(R-1,0):(0,C-1),(R-1,C-1):(0,0)}
    return corners.get((r,c), (r,c))

def move_ghosts(grid: List[str], ghosts):
    R, C = len(grid), len(grid[0])
    out = []
    for i in range(len(ghosts)):
        (r,c), d = ghosts[i]
        nc = c + d
        if not (0 <= r < R and 0 <= nc < C) or grid[r][nc] == '%':
            d = -d
            nc = c + d
            if not (0 <= r < R and 0 <= nc < C) or grid[r][nc] == '%':
                out.append([(r,c), d])
                continue
        out.append([(r, nc), d])
    return out

def rotate_world(grid, pac, foods, pies, ghosts, exit_pos):
    R, C = len(grid), len(grid[0])
    new_grid = rotate_grid_cw(grid)
    new_pac = rot_pos_cw(pac, R, C)
    new_foods = {rot_pos_cw(p, R, C) for p in foods}
    new_pies = {rot_pos_cw(p, R, C) for p in pies}
    new_exit = rot_pos_cw(exit_pos, R, C)
    new_ghosts = [[rot_pos_cw(pos, R, C), d] for (pos, d) in ghosts]
    return new_grid, new_pac, new_foods, new_pies, new_ghosts, new_exit

def main():
    grid = SAMPLE
    start, foods, exit_pos, pies, ghosts = parse_grid(grid)
    pac = list(start)
    ttl = 0
    step_mod = 0

    R, C = len(grid), len(grid[0])
    width, height = C*CELL, R*CELL + 28

    pygame.init()
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Pacman – teleport corners, ghosts, 30-step rotation")
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

                # Pacman move
                nr, nc = pac[0] + dr, pac[1] + dc
                if 0 <= nr < len(grid) and 0 <= nc < len(grid[0]):
                    if not is_wall(grid, nr, nc) or ttl > 0:
                        pac = [nr, nc]
                        step_mod = (step_mod + 1) % 30
                        ttl = max(0, ttl - 1)

                        # Teleport on corner
                        pac[0], pac[1] = teleport_if_corner(grid, pac[0], pac[1])

                        # Collect
                        if tuple(pac) in foods: foods.remove(tuple(pac))
                        if tuple(pac) in pies:
                            ttl = 5
                            pies.remove(tuple(pac))

                        # Ghosts move after pacman
                        ghosts = move_ghosts(grid, ghosts)

                        # Collision -> reset (demo): ở bản problem là "None transition"
                        for (gr,gc), _ in ghosts:
                            if (gr,gc) == tuple(pac):
                                print(" Bị ma bắt! (demo GUI chỉ in thông báo)")
                                # bạn có thể làm hiệu ứng hoặc reset map tại đây

                        # Rotate every 30 steps
                        if step_mod == 0:
                            grid, pac, foods, pies, ghosts, exit_pos = rotate_world(grid, tuple(pac), foods, pies, ghosts, exit_pos)
                            pac = list(pac)

        draw_grid(screen, grid, tuple(pac), foods, exit_pos, pies, ghosts, ttl, step_mod)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
