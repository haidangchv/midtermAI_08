import pygame
import sys, os
from typing import List, Tuple, Set

# ----- IMPORT PATHS -----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))           # .../source/task2_pacman/gui
TASK2_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))       # .../source/task2_pacman
sys.path.insert(0, TASK2_DIR)

from pacman_problem import PacmanProblem
from heuristics import HeuristicPacmanMST
from astar import astar

# ----- CONSTANTS -----
CELL_LOGICAL = 32
HUD_H = 76            
FPS = 30

# Ghost moves (ms)
GHOST_MOVE_MS = 150
GHOST_EVENT = pygame.USEREVENT + 1

# Layout
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

# ---- corner anchors ----
def first_open_from_top_left(grid):
    R, C = len(grid), len(grid[0])
    for r in range(R):
        for c in range(C):
            if grid[r][c] != '%':
                return (r, c)
    return (0, 0)

def first_open_from_top_right(grid):
    R, C = len(grid), len(grid[0])
    for r in range(R):
        for c in range(C-1, -1, -1):
            if grid[r][c] != '%':
                return (r, c)
    return (0, C-1)

def first_open_from_bottom_left(grid):
    R, C = len(grid), len(grid[0])
    for r in range(R-1, -1, -1):
        for c in range(C):
            if grid[r][c] != '%':
                return (r, c)
    return (R-1, 0)

def first_open_from_bottom_right(grid):
    R, C = len(grid), len(grid[0])
    for r in range(R-1, -1, -1):
        for c in range(C-1, -1, -1):
            if grid[r][c] != '%':
                return (r, c)
    return (R-1, C-1)

def corner_anchors(grid):
    return (
        first_open_from_top_left(grid),     # TL : index 0
        first_open_from_top_right(grid),    # TR : index 1
        first_open_from_bottom_left(grid),  # BL : index 2
        first_open_from_bottom_right(grid)  # BR : index 3
    )

def is_at_anchor(grid, pac):
    return tuple(pac) in set(corner_anchors(grid))

# ----- auto fit to window -----
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

    # Vẽ góc neo (cyan)
    for (gr, gc) in corner_anchors(grid):
        corner_rect = pygame.Rect(gc*CELL_LOGICAL, gr*CELL_LOGICAL, CELL_LOGICAL, CELL_LOGICAL)
        pygame.draw.rect(surface, (0, 200, 255), corner_rect, 2)

    # HUD
    font = pygame.font.SysFont(None, 20)
    y0 = CELL_LOGICAL*len(grid) + 6
    remaining = len(foods)

    # Dòng 1: trạng thái + FOOD LEFT
    hud = font.render(
        f"TTL: {ttl}   step%30: {step_mod}   AUTO: {'ON' if auto_mode else 'OFF'}   FOOD LEFT: {remaining}",
        True, (255,255,255)
    )
    surface.blit(hud, (8, y0))

    # Dòng 2: hint teleport nếu đang ở neo
    if is_at_anchor(grid, pac):
        hint = font.render("Press 1–4 to teleport (TL, TR, BL, BR)", True, (0, 200, 255))
        surface.blit(hint, (8, y0 + 20))

    # Dòng 3: nếu đứng ở EXIT nhưng chưa đủ food, báo dưới HUD
    if tuple(pac) == exit_pos and remaining > 0:
        warn = font.render(f"⚠ Need {remaining} more food before EXIT!", True, (255, 200, 0))
        surface.blit(warn, (8, y0 + 40))

# ----- COMPLETED OVERLAY -----
def draw_completed_overlay(screen, logical_surface):
    """Vẽ overlay 'Completed' (không nằm trong HUD)."""
    # scale logical -> rect để biết vùng nội dung
    dst = compute_scaled_rect(screen.get_size(), logical_surface.get_size())

    # lớp mờ toàn màn hình
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))  # đen mờ
    screen.blit(overlay, (0, 0))

    # hộp thông điệp
    box_w, box_h = int(dst.width * 0.7), int(dst.height * 0.35)
    box_x = (screen.get_width() - box_w)//2
    box_y = (screen.get_height() - box_h)//2
    box = pygame.Rect(box_x, box_y, box_w, box_h)
    pygame.draw.rect(screen, (30, 30, 30), box, border_radius=12)
    pygame.draw.rect(screen, (80, 200, 170), box, 2, border_radius=12)

    title_font = pygame.font.SysFont(None, 48)
    text_font  = pygame.font.SysFont(None, 28)

    title = title_font.render("COMPLETED!", True, (80, 255, 200))
    tip   = text_font.render("Press R to restart — Press Q or Esc to quit", True, (230, 230, 230))

    screen.blit(title, (box.centerx - title.get_width()//2, box_y + 28))
    screen.blit(tip,   (box.centerx - tip.get_width()//2,   box_y + box_h - 28 - tip.get_height()))

def handle_completed_input(screen, logical_surface, reset_game_cb):
    import pygame
    keys = pygame.key.get_pressed()
    if keys[pygame.K_r]:
        reset_game_cb()
        return "restart"
    if keys[pygame.K_q] or keys[pygame.K_ESCAPE]:
        return "quit"
    return None

# ----- MAIN LOOP -----
def main():
    def reset_game():
        nonlocal grid, start, foods, exit_pos, pies, ghosts, pac, ttl, step_mod
        nonlocal logical_surface, auto_mode, auto_plan, auto_tick_cooldown, game_completed
        grid = load_layout_file(DEFAULT_LAYOUT_PATH)
        start, foods, exit_pos, pies, ghosts = parse_grid(grid)
        pac = list(start)
        ttl = 0
        step_mod = 0
        logical_surface = make_logical_surface(grid)
        auto_mode = False
        auto_plan = []
        auto_tick_cooldown = 0
        game_completed = False
        pygame.time.set_timer(GHOST_EVENT, GHOST_MOVE_MS)  # bật lại ghost timer

    # Khởi tạo ban đầu
    grid = load_layout_file(DEFAULT_LAYOUT_PATH)
    start, foods, exit_pos, pies, ghosts = parse_grid(grid)
    pac = list(start)
    ttl = 0
    step_mod = 0

    pygame.init()
    info = pygame.display.Info()
    start_w = int(info.current_w * 0.9)
    start_h = int(info.current_h * 0.9)
    screen = pygame.display.set_mode((start_w, start_h), pygame.RESIZABLE)
    pygame.display.set_caption("Pacman")
    clock = pygame.time.Clock()

    logical_surface = make_logical_surface(grid)

    # Timers & flags
    pygame.time.set_timer(GHOST_EVENT, GHOST_MOVE_MS)
    auto_mode = False
    auto_plan = []
    auto_tick_cooldown = 0
    game_completed = False   # NEW: khi True, hiện overlay, khoá điều khiển

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Resize 
            elif event.type == pygame.VIDEORESIZE or event.type == pygame.WINDOWSIZECHANGED:
                pass

            # Ghosts move
            elif event.type == GHOST_EVENT and not game_completed:
                ghosts = move_ghosts(grid, ghosts)
                # check after ghost move
                for (gr, gc), _ in ghosts:
                    if (gr, gc) == tuple(pac):
                        print("Bị ma bắt! (ghost timer)")
                        auto_mode = False
                        auto_plan = []
                        break

            elif event.type == pygame.KEYDOWN:
                # xử lý R / Q / Esc
                if game_completed:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        running = False
                    elif event.key in (pygame.K_r, ):
                        reset_game()
                    continue 

                dr = dc = 0
                if event.key == pygame.K_UP: dr = -1
                elif event.key == pygame.K_DOWN: dr = +1
                elif event.key == pygame.K_LEFT: dc = -1
                elif event.key == pygame.K_RIGHT: dc = +1

                # --- TELEPORT ---
                elif event.key in (
                    pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                    pygame.K_KP1, pygame.K_KP2, pygame.K_KP3, pygame.K_KP4
                ):
                    key2idx = {
                        pygame.K_1:0, pygame.K_2:1, pygame.K_3:2, pygame.K_4:3,
                        pygame.K_KP1:2, pygame.K_KP2:3, pygame.K_KP3:1, pygame.K_KP4:0,
                    }
                    anchors = corner_anchors(grid)
                    if not is_at_anchor(grid, pac):
                        print("[Teleport] Not at a corner anchor -> ignored")
                    else:
                        target = anchors[key2idx[event.key]]
                        pac = [target[0], target[1]]
                        step_mod = (step_mod + 1) % 30
                        ttl = max(0, ttl - 1)
                        # Collect ở điểm đích
                        if tuple(pac) in foods: foods.remove(tuple(pac))
                        if tuple(pac) in pies: ttl = 5; pies.remove(tuple(pac))
                        # Va chạm ma
                        for (gr, gc), _ in ghosts:
                            if (gr, gc) == tuple(pac):
                                print("Bị ma bắt! (teleport)")
                                auto_mode = False; auto_plan = []
                                break
                        # Xoay sau mỗi 30 bước
                        if step_mod == 0:
                            grid, pac, foods, pies, ghosts, exit_pos = rotate_world(
                                grid, tuple(pac), foods, pies, ghosts, exit_pos
                            )
                            pac = list(pac)
                            logical_surface = make_logical_surface(grid)
                        # Kiểm tra hoàn thành
                        if len(foods) == 0 and tuple(pac) == exit_pos:
                            print("Completed! All food collected and reached EXIT.")
                            auto_mode = False; auto_plan = []
                            game_completed = True
                            pygame.time.set_timer(GHOST_EVENT, 0)  # tắt ghost timer

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
                                auto_plan = [n.action for n in res["solution"][1:]]
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
                            # Collect
                            if tuple(pac) in foods: foods.remove(tuple(pac))
                            if tuple(pac) in pies: ttl = 5; pies.remove(tuple(pac))
                            # Collision with ghosts (they move via timer)
                            for (gr,gc), _ in ghosts:
                                if (gr,gc) == tuple(pac):
                                    print("Bị ma bắt!")
                                    auto_mode = False; auto_plan = []
                                    break
                            # Rotate world each 30 steps
                            if step_mod == 0:
                                grid, pac, foods, pies, ghosts, exit_pos = rotate_world(
                                    grid, tuple(pac), foods, pies, ghosts, exit_pos
                                )
                                pac = list(pac)
                                logical_surface = make_logical_surface(grid)
                            # Kiểm tra hoàn thành
                            if len(foods) == 0 and tuple(pac) == exit_pos:
                                print("🎉 Completed! All food collected and reached EXIT.")
                                auto_mode = False; auto_plan = []
                                game_completed = True
                                pygame.time.set_timer(GHOST_EVENT, 0)

        # AUTO step (every few frames for visibility)
        if not game_completed and auto_mode and auto_plan:
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
                        if tuple(pac) in foods: foods.remove(tuple(pac))
                        if tuple(pac) in pies: ttl = 5; pies.remove(tuple(pac))
                        for (gr,gc), _ in ghosts:
                            if (gr,gc) == tuple(pac):
                                print("Bị ma bắt! (AUTO dừng)")
                                auto_mode = False; auto_plan = []
                                break
                        if step_mod == 0:
                            grid, pac, foods, pies, ghosts, exit_pos = rotate_world(
                                grid, tuple(pac), foods, pies, ghosts, exit_pos
                            )
                            pac = list(pac)
                            logical_surface = make_logical_surface(grid)
                        # Kiểm tra hoàn thành
                        if len(foods) == 0 and tuple(pac) == exit_pos:
                            print("🎉 Completed! All food collected and reached EXIT.")
                            auto_mode = False; auto_plan = []
                            game_completed = True
                            pygame.time.set_timer(GHOST_EVENT, 0)
                auto_tick_cooldown = 4
            else:
                auto_tick_cooldown -= 1

        # Draw to logical surface, then scale to window
        draw_grid(logical_surface, grid, tuple(pac), foods, exit_pos, pies, ghosts, ttl, step_mod, auto_mode)
        scale_and_present(screen, logical_surface)

        # Nếu đã hoàn thành: vẽ overlay (ngoài HUD)
        if game_completed:
            draw_completed_overlay(screen, logical_surface)
            action = handle_completed_input(screen, logical_surface, reset_game)
            if action == "restart":
                pass
            elif action == "quit":
                running = False


        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
