import pygame
import sys, os
from typing import List, Tuple, Set

BASE_DIR = os.path.dirname(os.path.abspath(__file__))           # .../source/task2_pacman/gui
TASK2_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))       # .../source/task2_pacman
sys.path.insert(0, TASK2_DIR)

from pacman_problem import PacmanProblem
from heuristics import HeuristicPacmanMST
from astar import astar

CELL_LOGICAL = 32      # pixel/ô trên bề mặt logic
HUD_H = 28             # chiều cao HUD trên bề mặt logic
FPS = 30               # khung hình/giây

# Ghost moves on timer (ms)
GHOST_MOVE_MS = 200
# Custom pygame event id for ghost stepping
GHOST_EVENT = pygame.USEREVENT + 1

# Layout mặc định: ở gốc repo (cùng cấp folder 'source/')
DEFAULT_LAYOUT_PATH = os.path.abspath(os.path.join(TASK2_DIR, "..", "..", "task02_pacman_example_map.txt"))

# ----- FILE / GRID UTILS -----
def load_layout_file(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f if line.strip("\n")]
    w = max(len(x) for x in lines)
    return [row.ljust(w) for row in lines]

def rotate_grid_cw(grid: List[str]) -> List[str]:
    R, C = len(grid), len(grid[0])
    return ["".join(grid[R - 1 - r][c] for r in range(R)) for c in range(C)]

def rot_pos_cw(p: Tuple[int,int], R: int, C: int) -> Tuple[int,int]:
    # 90° CW: (r, c) -> (c, R-1-r)
    r, c = p
    return (c, R - 1 - r)

def parse_grid(grid: List[str]):
    start = None
    foods: Set[Tuple[int,int]] = set()
    exit_pos = None
    pies: Set[Tuple[int,int]] = set()
    ghosts = []
    for r,row in enumerate(grid):
        for c,ch in enumerate(row):
            if ch == 'P': start = (r,c)
            elif ch == '.': foods.add((r,c))
            elif ch == 'E': exit_pos = (r,c)
            elif ch == 'O': pies.add((r,c))
            elif ch == 'G': ghosts.append([(r,c), +1])  # [pos, dir]
    if start is None or exit_pos is None:
        raise ValueError("Layout cần có 'P' (start) và 'E' (exit).")
    return start, foods, exit_pos, pies, ghosts

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
    # đi ngang, đụng tường thì đảo chiều rồi thử bước
    R, C = len(grid), len(grid[0])
    out = []
    for (r,c), d in ghosts:
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

# ----- LOGICAL SURFACE & SCALING (auto fit to window) -----
def make_logical_surface(grid: List[str]):
    w = len(grid[0]) * CELL_LOGICAL
    h = len(grid) * CELL_LOGICAL + HUD_H
    return pygame.Surface((w, h)).convert_alpha()

def compute_scaled_rect(window_size, logical_size):
    Ww, Hw = window_size
    Wl, Hl = logical_size
    if Wl == 0 or Hl == 0:
        return pygame.Rect(0, 0, Ww, Hw)
    scale = min(Ww / Wl, Hw / Hl)
    Tw, Th = int(Wl * scale), int(Hl * scale)
    x = (Ww - Tw) // 2
    y = (Hw - Th) // 2
    return pygame.Rect(x, y, Tw, Th)

def scale_and_present(screen, logical_surface):
    rect = compute_scaled_rect(screen.get_size(), logical_surface.get_size())
    screen.fill((0, 0, 0))
    if rect.size != logical_surface.get_size():
        scaled = pygame.transform.smoothscale(logical_surface, rect.size)
        screen.blit(scaled, rect.topleft)
    else:
        screen.blit(logical_surface, rect.topleft)

# ----- DRAW -----
def draw_grid(surface, grid, pac, foods, exit_pos, pies, ghosts, ttl, step_mod, auto_mode):
    surface.fill((0,0,0,0))
    R, C = len(grid), len(grid[0])

    # Tiles + collectibles + exit
    for r in range(R):
        for c in range(C):
            rect = pygame.Rect(c*CELL_LOGICAL, r*CELL_LOGICAL, CELL_LOGICAL, CELL_LOGICAL)
            ch = grid[r][c]
            if ch == '%':
                pygame.draw.rect(surface, (75,75,75), rect)
            else:
                pygame.draw.rect(surface, (20,20,20), rect)
                pygame.draw.rect(surface, (40,40,40), rect, 1)
            if (r,c) in pies:
                pygame.draw.circle(surface, (200,120,0), rect.center, CELL_LOGICAL//6)
            if (r,c) in foods:
                pygame.draw.circle(surface, (220,220,220), rect.center, CELL_LOGICAL//10)
            if exit_pos == (r,c):
                pygame.draw.rect(surface, (0,120,200), rect, 2)

    # ghosts
    for (gr, gc), d in ghosts:
        grect = pygame.Rect(gc*CELL_LOGICAL, gr*CELL_LOGICAL, CELL_LOGICAL, CELL_LOGICAL)
        pygame.draw.circle(surface, (200,50,50), grect.center, CELL_LOGICAL//3)

    # pacman
    prect = pygame.Rect(pac[1]*CELL_LOGICAL, pac[0]*CELL_LOGICAL, CELL_LOGICAL, CELL_LOGICAL)
    pygame.draw.circle(surface, (255,200,0), prect.center, CELL_LOGICAL//2 - 2)

    # HUD
    font = pygame.font.SysFont(None, 20)
    hud = font.render(f"TTL: {ttl}   step%30: {step_mod}   AUTO: {'ON' if auto_mode else 'OFF'}", True, (255,255,255))
    surface.blit(hud, (8, CELL_LOGICAL*len(grid)+6))

# ----- MAIN LOOP -----
def main():
    # Load layout & parse
    grid = load_layout_file(DEFAULT_LAYOUT_PATH)
    start, foods, exit_pos, pies, ghosts = parse_grid(grid)
    pac = list(start)
    ttl = 0
    step_mod = 0

    pygame.init()
    # Create a resizable window (90% of screen)
    info = pygame.display.Info()
    start_w = int(info.current_w * 0.9)
    start_h = int(info.current_h * 0.9)
    screen = pygame.display.set_mode((start_w, start_h), pygame.RESIZABLE)
    pygame.display.set_caption("Pacman – manual/AUTO(A*), ghost timer, auto-scale, rotate 90°")
    clock = pygame.time.Clock()

    # Logical surface (render target) which will be scaled to the window
    logical_surface = make_logical_surface(grid)

    # Ghost timer
    pygame.time.set_timer(GHOST_EVENT, GHOST_MOVE_MS)

    # Auto-play
    auto_mode = False
    auto_plan = []          # list of 'N','S','E','W'
    auto_tick_cooldown = 0  # frames between two auto steps (for visualization)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Window resized - next frame will auto-scale content
            elif event.type == pygame.VIDEORESIZE or event.type == pygame.WINDOWSIZECHANGED:
                pass

            # Ghosts move on timer, independent of Pacman
            elif event.type == GHOST_EVENT:
                ghosts = move_ghosts(grid, ghosts)
                # collision check after ghost move
                for (gr, gc), _ in ghosts:
                    if (gr, gc) == tuple(pac):
                        print("💥 Bị ma bắt! (ghost timer)")
                        auto_mode = False
                        auto_plan = []
                        break

            elif event.type == pygame.KEYDOWN:
                dr = dc = 0
                if event.key == pygame.K_UP: dr = -1
                elif event.key == pygame.K_DOWN: dr = +1
                elif event.key == pygame.K_LEFT: dc = -1
                elif event.key == pygame.K_RIGHT: dc = +1

                # Toggle AUTO planning with A*
                elif event.key == pygame.K_a:
                    auto_mode = not auto_mode
                    auto_plan = []
                    if auto_mode:
                        foods_list = sorted(list(foods))
                        pies_list = sorted(list(pies))
                        ghosts_list = [(tuple(pos), d) for (pos, d) in ghosts]
                        try:
                            prob = PacmanProblem(grid, tuple(pac), foods_list, exit_pos, pies=pies_list, ghosts=ghosts_list)
                            h = HeuristicPacmanMST(grid, exit_pos)
                            res = astar(prob, h, graph_search=True)
                            if res.get("solution"):
                                auto_plan = [n.action for n in res["solution"][1:]]  # bỏ node gốc
                                print(f"[AUTO] plan len={len(auto_plan)} cost={res['cost']}")
                            else:
                                print("[AUTO] No solution found.")
                                auto_mode = False
                        except Exception as e:
                            print("[AUTO] Planning error:", e)
                            auto_mode = False

                # Manual step
                if dr or dc:
                    nr, nc = pac[0] + dr, pac[1] + dc
                    if 0 <= nr < len(grid) and 0 <= nc < len(grid[0]):
                        wall = is_wall(grid, nr, nc)
                        if not wall or ttl > 0:
                            pac = [nr, nc]
                            step_mod = (step_mod + 1) % 30
                            ttl = max(0, ttl - 1)
                            # Teleport corners
                            pac[0], pac[1] = teleport_if_corner(grid, pac[0], pac[1])
                            # Collect
                            if tuple(pac) in foods: foods.remove(tuple(pac))
                            if tuple(pac) in pies: ttl = 5; pies.remove(tuple(pac))
                            # Collision with ghosts (they move via timer)
                            for (gr,gc), _ in ghosts:
                                if (gr,gc) == tuple(pac):
                                    print("💥 Bị ma bắt!")
                                    auto_mode = False; auto_plan = []
                                    break
                            # Rotate world each 30 steps
                            if step_mod == 0:
                                grid, pac, foods, pies, ghosts, exit_pos = rotate_world(grid, tuple(pac), foods, pies, ghosts, exit_pos)
                                pac = list(pac)
                                logical_surface = make_logical_surface(grid)  # keep aspect on rotate

        # AUTO step (every few frames for visibility)
        if auto_mode and auto_plan:
            if auto_tick_cooldown == 0:
                a = auto_plan.pop(0)
                drdc = {"N":(-1,0),"S":(1,0),"W":(0,-1),"E":(0,1)}
                dr, dc = drdc[a]
                nr, nc = pac[0] + dr, pac[1] + dc
                if 0 <= nr < len(grid) and 0 <= nc < len(grid[0]):
                    wall = is_wall(grid, nr, nc)
                    if not wall or ttl > 0:
                        pac = [nr, nc]
                        step_mod = (step_mod + 1) % 30
                        ttl = max(0, ttl - 1)
                        pac[0], pac[1] = teleport_if_corner(grid, pac[0], pac[1])
                        if tuple(pac) in foods: foods.remove(tuple(pac))
                        if tuple(pac) in pies: ttl = 5; pies.remove(tuple(pac))
                        for (gr,gc), _ in ghosts:
                            if (gr,gc) == tuple(pac):
                                print("💥 Bị ma bắt! (AUTO dừng)")
                                auto_mode = False; auto_plan = []
                                break
                        if step_mod == 0:
                            grid, pac, foods, pies, ghosts, exit_pos = rotate_world(grid, tuple(pac), foods, pies, ghosts, exit_pos)
                            pac = list(pac)
                            logical_surface = make_logical_surface(grid)  # keep aspect on rotate
                auto_tick_cooldown = 4
            else:
                auto_tick_cooldown -= 1

        # Draw to logical surface, then scale to window
        draw_grid(logical_surface, grid, tuple(pac), foods, exit_pos, pies, ghosts, ttl, step_mod, auto_mode)
        scale_and_present(screen, logical_surface)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
