# source/task2_pacman/gui/main.py
# GUI pygame: manual + AUTO (A* actions), ghost tick-theo-bước, auto scaling,
# rotate 90° mỗi 30 bước, teleport anchors, HUD FOOD LEFT & PAC(r,c),
# I/O path.txt & output.txt (output dir = source/task2_pacman/output),
# AUTO có cooldown và REPLAN nền (thread) mỗi khi xoay để tránh đơ UI.
# Chỉ khi HOÀN THÀNH nhiệm vụ mới xuất toàn bộ hành trình ra file.

try:
    import pygame
except Exception as e:
        print("Pygame is required for the GUI. Install with: pip install pygame")
        print("Detail:", e)
        raise SystemExit(0)

import sys, os
import threading
from typing import List, Tuple, Set

# ----- FIX IMPORT PATHS -----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))           # .../source/task2_pacman/gui
TASK2_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))       # .../source/task2_pacman
sys.path.insert(0, TASK2_DIR)

from pacman_problem import PacmanProblem
from heuristics import HeuristicMazeMST
from astar import astar

# ----- I/O PATHS -----
REPO_ROOT = os.path.abspath(os.path.join(TASK2_DIR, "..", ".."))
INPUT_DIR = os.path.join(REPO_ROOT, "input")  # dò input ở gốc dự án\input
OUTPUT_DIR = os.path.join(TASK2_DIR, "output")  # theo yêu cầu: source\task2_pacman\output
os.makedirs(OUTPUT_DIR, exist_ok=True)

def resolve_layout_path(cli_path=None):
    filename = "task02_pacman_example_map.txt"
    candidates = []
    if cli_path:
        candidates.append(cli_path)
    candidates += [
        os.path.join(REPO_ROOT, "input", filename),
        os.path.join(TASK2_DIR, "input", filename),   # hỗ trợ nếu để tại source\task2_pacman\input
        os.path.join(REPO_ROOT, filename),
        os.path.join(TASK2_DIR, filename),
        os.path.join(os.path.dirname(__file__), filename),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(
        "Không tìm thấy file layout. Đặt file vào 'input/task02_pacman_example_map.txt' "
        "hoặc truyền đường dẫn khi chạy."
    )

CLI_LAYOUT = sys.argv[1] if len(sys.argv) > 1 else None
DEFAULT_LAYOUT_PATH = resolve_layout_path(CLI_LAYOUT)

PATH_TXT = os.path.join(OUTPUT_DIR, "path.txt")
OUT_TXT  = os.path.join(OUTPUT_DIR, "output.txt")

# ----- CONSTANTS -----
CELL_LOGICAL = 32
HUD_H = 84
FPS = 30
AUTO_STEP_COOLDOWN_FRAMES = 8  # auto chậm rãi

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
            elif ch == 'G': ghosts.append([(r,c), +1])
    if start is None or exit_pos is None:
        raise ValueError("Layout cần có 'P' (start) và 'E' (exit).")
    return start, foods, exit_pos, pies, ghosts

def is_wall(grid: List[str], r: int, c: int) -> bool:
    R, C = len(grid), len(grid[0])
    if 0 <= r < R and 0 <= c < C:
        return grid[r][c] == '%'
    return True

def move_ghosts(grid: List[str], ghosts):
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

# ---- corner anchors (ô đi được gần mỗi góc) ----
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
        first_open_from_top_left(grid),     # TL -> index 0
        first_open_from_top_right(grid),    # TR -> index 1
        first_open_from_bottom_left(grid),  # BL -> index 2
        first_open_from_bottom_right(grid)  # BR -> index 3
    )

def is_at_anchor(grid, pac):
    return tuple(pac) in set(corner_anchors(grid))

# ----- SURFACE / SCALING -----
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

# ----- DRAW / HUD -----
def draw_grid(surface, grid, pac, foods, exit_pos, pies, ghosts, ttl, step_mod, auto_mode):
    surface.fill((0,0,0,0))
    R, C = len(grid), len(grid[0])

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

    for (gr, gc), _ in ghosts:
        grect = pygame.Rect(gc*CELL_LOGICAL, gr*CELL_LOGICAL, CELL_LOGICAL, CELL_LOGICAL)
        pygame.draw.circle(surface, (200,50,50), grect.center, CELL_LOGICAL//3)

    prect = pygame.Rect(pac[1]*CELL_LOGICAL, pac[0]*CELL_LOGICAL, CELL_LOGICAL, CELL_LOGICAL)
    pygame.draw.circle(surface, (255,200,0), prect.center, CELL_LOGICAL//2 - 2)

    for (gr, gc) in corner_anchors(grid):
        corner_rect = pygame.Rect(gc*CELL_LOGICAL, gr*CELL_LOGICAL, CELL_LOGICAL, CELL_LOGICAL)
        pygame.draw.rect(surface, (0, 200, 255), corner_rect, 2)

    # HUD
    font = pygame.font.SysFont(None, 20)
    y0 = CELL_LOGICAL*len(grid) + 6
    remaining = len(foods)
    hud = font.render(
        f"TTL: {ttl}   step%30: {step_mod}   AUTO: {'ON' if auto_mode else 'OFF'}   "
        f"FOOD LEFT: {remaining}   PAC: ({pac[0]},{pac[1]})",
        True, (255,255,255)
    )
    surface.blit(hud, (8, y0))
    if is_at_anchor(grid, pac):
        hint = font.render("Press 1–4 to teleport (TL, TR, BL, BR)", True, (0, 200, 255))
        surface.blit(hint, (8, y0 + 20))
    if tuple(pac) == exit_pos and remaining > 0:
        warn = font.render(f"⚠ Need {remaining} more food before EXIT!", True, (255, 200, 0))
        surface.blit(warn, (8, y0 + 40))

# ----- OVERLAYS / RESET -----
def show_center_message(screen, text, millis=1200):
    screen.fill((0, 0, 0))
    font_big = pygame.font.SysFont(None, 48)
    font_small = pygame.font.SysFont(None, 24)
    msg = font_big.render(text, True, (255, 80, 80))
    hint = font_small.render("Resetting...", True, (220, 220, 220))
    rect = msg.get_rect(center=(screen.get_width()//2, screen.get_height()//2 - 16))
    rect2 = hint.get_rect(center=(screen.get_width()//2, screen.get_height()//2 + 24))
    screen.blit(msg, rect)
    screen.blit(hint, rect2)
    pygame.display.flip()
    pygame.time.wait(millis)

def reset_game_state():
    grid = load_layout_file(DEFAULT_LAYOUT_PATH)
    start, foods, exit_pos, pies, ghosts = parse_grid(grid)
    pac = list(start)
    ttl = 0
    step_mod = 0
    logical_surface = make_logical_surface(grid)
    auto_mode = False
    auto_plan = []
    return grid, pac, foods, exit_pos, pies, ghosts, ttl, step_mod, logical_surface, auto_mode, auto_plan

# ----- ACTION EXECUTOR -----
def apply_action_step(a, grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, screen, logical_surface):
    """
    Thực thi 1 action (N/S/E/W hoặc TUL/TUR/TBL/TBR) với tick ma + rotate 30 bước.
    Trả về: (grid, pac(list), foods(set), pies(set), ghosts(list), exit_pos, ttl, step_mod, logical_surface, died, rotated)
    """
    R, C = len(grid), len(grid[0])
    nr, nc = pac[0], pac[1]

    if a in ("N","S","E","W"):
        drdc = {"N":(-1,0),"S":(1,0),"W":(0,-1),"E":(0,1)}
        dr, dc = drdc[a]
        tr, tc = nr + dr, nc + dc
        if 0 <= tr < R and 0 <= tc < C:
            if grid[tr][tc] != '%' or ttl > 0:
                nr, nc = tr, tc
    elif a in ("TUL","TUR","TBL","TBR"):
        anchors = corner_anchors(grid)
        if tuple(pac) in set(anchors):
            idx = {"TUL":0,"TUR":1,"TBL":2,"TBR":3}[a]
            nr, nc = anchors[idx]
    else:
        pass  # không đổi

    pac = [nr, nc]
    step_mod = (step_mod + 1) % 30
    ttl = max(0, ttl - 1)

    if tuple(pac) in foods:
        foods.remove(tuple(pac))
    if tuple(pac) in pies:
        ttl = 5
        pies.remove(tuple(pac))

    # --- Va chạm với ma: trước/sau tick + swap ---
    # trước tick đã đi vào ô ma?
    for (gr,gc), _d in ghosts:
        if (gr,gc) == tuple(pac) and ttl == 0:
            show_center_message(screen, "💥 Bị ma bắt!")
            return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, logical_surface, True, False

    old_ghosts = ghosts
    ghosts = move_ghosts(grid, ghosts)

    # sau tick hoặc swap cạnh
    for (old_pos, _d1), (new_pos, _d2) in zip(old_ghosts, ghosts):
        if new_pos == tuple(pac):
            show_center_message(screen, "💥 Bị ma bắt!")
            return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, logical_surface, True, False
        if old_pos == tuple(pac) and new_pos == (nr - (nr - pac[0]), nc - (nc - pac[1])):  # bảo thủ, swap check
            show_center_message(screen, "💥 Bị ma bắt!")
            return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, logical_surface, True, False

    rotated = False
    if step_mod == 0:
        grid, pac, foods, pies, ghosts, exit_pos = rotate_world(
            grid, tuple(pac), foods, pies, ghosts, exit_pos
        )
        pac = list(pac)
        logical_surface = make_logical_surface(grid)
        rotated = True

    return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, logical_surface, False, rotated

# ----- I/O output -----
def write_outputs(path_coords, actions, cost):
    # path.txt: mỗi dòng "r c"
    with open(PATH_TXT, "w", encoding="utf-8") as f:
        for (r, c) in path_coords:
            f.write(f"{r} {c}\n")

    # output.txt: cost + actions (mỗi action trên 1 dòng)
    name_map = {
        "N": "North",
        "S": "South",
        "E": "East",
        "W": "West",
        # Teleport -> Stop theo format đề
        "TUL": "Stop", "TUR": "Stop", "TBL": "Stop", "TBR": "Stop",
    }
    pretty_actions = [name_map.get(a, "West") for a in actions]

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(f"cost: {int(cost) if cost == int(cost) else cost}\n")
        f.write("actions:\n")
        for act in pretty_actions:
            f.write(act + "\n")

# ----- Sanitizers để tránh None/format sai khi plan -----
def _to_pos(x):
    """Trả tuple (r,c) nếu hợp lệ, ngược lại trả None."""
    try:
        r, c = x
        if isinstance(r, int) and isinstance(c, int):
            return (r, c)
    except Exception:
        pass
    return None

def sanitize_inputs(grid, pac, foods, pies, ghosts, exit_pos):
    """
    Chuẩn hoá & lọc rác:
    - pac, exit_pos: (r,c)
    - foods, pies: set[(r,c)]
    - ghosts: list[((r,c), dir)] với dir ∈ {-1, +1}
    """
    # pac
    pac_t = _to_pos(pac) if pac is not None else None
    if pac_t is None:
        pac_t = (0, 0)

    # exit
    exit_t = _to_pos(exit_pos) if exit_pos is not None else None
    if exit_t is None:
        exit_t = (0, 0)

    # foods
    foods_set = set()
    try:
        for p in list(foods):
            pt = _to_pos(p)
            if pt is not None:
                foods_set.add(pt)
    except Exception:
        foods_set = set()

    # pies
    pies_set = set()
    try:
        for p in list(pies):
            pt = _to_pos(p)
            if pt is not None:
                pies_set.add(pt)
    except Exception:
        pies_set = set()

    # ghosts
    ghosts_list = []
    try:
        for g in list(ghosts):
            pos = None; d = None
            if isinstance(g, dict):
                pos = _to_pos(g.get("pos"))
                d = g.get("dir", +1)
            else:
                if isinstance(g, (list, tuple)) and len(g) == 2:
                    pos = _to_pos(g[0])
                    d = g[1]
            if pos is None:
                continue
            d = +1 if d not in (-1, +1) else d
            ghosts_list.append([pos, d])
    except Exception:
        ghosts_list = []

    return pac_t, foods_set, pies_set, ghosts_list, exit_t

# ----- PLANNER -----
def _run_astar_safe(problem, hz, goal_fn=None):
    """Gọi astar với/không với max_expanded; LUÔN trả dict hoặc {}."""
    try:
        try:
            res = astar(problem, hz, graph_search=True, goal_fn=goal_fn, max_expanded=200000)
        except TypeError:
            res = astar(problem, hz, graph_search=True, goal_fn=goal_fn)
    except Exception as e:
        print("[A*] Exception:", e)
        return {}
    return res if isinstance(res, dict) else {}

def plan_from_snapshot(grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod):
    """
    Lập kế hoạch (A*): ăn food gần nhất theo cost rồi đến Exit.
    LUÔN trả (actions, path_coords, cost). Nếu không tìm được plan, trả ([], [], 0.0).
    """
    try:
        pac, foods, pies, ghosts, exit_pos = sanitize_inputs(grid, pac, foods, pies, ghosts, exit_pos)

        cur_grid   = list(grid)
        cur_pac    = tuple(pac)
        cur_foods  = sorted(list(foods))
        cur_pies   = sorted(list(pies))
        cur_ghosts = [(tuple(pos), d) for (pos, d) in ghosts]  # đảm bảo dạng ((r,c), d)
        cur_exit   = exit_pos
        cur_ttl    = int(ttl) if isinstance(ttl, int) else 0
        cur_step   = int(step_mod) % 30 if isinstance(step_mod, int) else 0

        total_actions, total_coords, total_cost = [], [], 0.0

        while True:
            # Chặng cuối: tới Exit
            if len(cur_foods) == 0:
                prob = PacmanProblem(cur_grid, cur_pac, cur_foods, cur_exit,
                                     pies=cur_pies, ghosts=cur_ghosts,
                                     ttl0=cur_ttl, steps_mod30_0=cur_step, rot_idx0=0)
                hz = HeuristicMazeMST(prob)
                res = _run_astar_safe(prob, hz, goal_fn=None)

                if not res or not res.get("solution"):
                    return total_actions, total_coords, total_cost

                states, actions = res["solution"], res["actions"]
                for s in states[1:]:
                    if s is not None:
                        total_coords.append(s.pacman)
                total_actions.extend(actions if actions else [])
                total_cost += float(res.get("cost", 0.0))
                return total_actions, total_coords, total_cost

            # Còn food: thử tới “một food bất kỳ”, chọn cost nhỏ nhất
            best = None
            target_count_after = len(cur_foods) - 1
            def goal_fn(s, target_count=target_count_after):
                return (s is not None) and (len(s.foods) == target_count)

            for _ in list(cur_foods):
                prob = PacmanProblem(cur_grid, cur_pac, cur_foods, cur_exit,
                                     pies=cur_pies, ghosts=cur_ghosts,
                                     ttl0=cur_ttl, steps_mod30_0=cur_step, rot_idx0=0)
                hz = HeuristicMazeMST(prob)
                res = _run_astar_safe(prob, hz, goal_fn=goal_fn)

                if not res or not res.get("solution"):
                    continue

                cand_cost = float(res.get("cost", float("inf")))
                if (best is None) or (cand_cost < best[0]):
                    best = (cand_cost, res)

            if best is None:
                return total_actions, total_coords, total_cost

            _, res = best
            states, actions = res["solution"], res["actions"]
            for s in states[1:]:
                if s is not None:
                    total_coords.append(s.pacman)
            total_actions.extend(actions if actions else [])
            total_cost += float(res.get("cost", 0.0))

            # cập nhật snapshot theo state cuối chặng
            s_last = states[-1] if states else None
            if s_last is None:
                return total_actions, total_coords, total_cost

            cur_pac    = s_last.pacman
            cur_foods  = list(s_last.foods)
            cur_pies   = list(s_last.pies)
            cur_ghosts = [(g.pos, g.dir) for g in s_last.ghosts]
            cur_ttl    = s_last.ttl
            cur_step   = s_last.steps_mod30

    except Exception as e:
        print("[PLAN] Exception in plan_from_snapshot:", e)
        return [], [], 0.0

# ----- MAIN -----
def main():
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
    pygame.display.set_caption("Pacman – A* actions, ghost-per-step, teleport anchors, BG replan on rotation")
    clock = pygame.time.Clock()

    logical_surface = make_logical_surface(grid)

    # AUTO runtime
    auto_mode = False
    auto_step_cooldown = 0
    globals()["__GUI_AUTO_ACTIONS__"] = []

    # Replan nền (thread)
    planning_busy = False
    globals()["__PLANNER_THREAD__"] = None
    globals()["__PLANNER_DONE__"] = False
    globals()["__PLANNER_RESULT__"] = []

    # Lịch sử xuất ra file khi hoàn thành
    run_actions_history = []   # chuỗi action THỰC THI (N/S/E/W/TUL/TUR/TBL/TBR)
    run_coords_history  = []   # toạ độ sau mỗi bước

    def reset_game():
        nonlocal grid, pac, foods, exit_pos, pies, ghosts, ttl, step_mod, logical_surface, auto_mode, auto_step_cooldown, planning_busy
        (grid, pac, foods, exit_pos, pies, ghosts,
         ttl, step_mod, logical_surface, auto_mode, _) = reset_game_state()
        auto_step_cooldown = 0
        globals()["__GUI_AUTO_ACTIONS__"] = []
        # reset planner thread flags
        planning_busy = False
        globals()["__PLANNER_THREAD__"] = None
        globals()["__PLANNER_DONE__"] = False
        globals()["__PLANNER_RESULT__"] = []
        # reset lịch sử
        run_actions_history.clear()
        run_coords_history.clear()

    def spawn_replan_background():
        """Khởi tạo replan nền từ snapshot hiện tại; UI vẫn mượt."""
        nonlocal planning_busy
        if planning_busy:
            return  # đã có replan đang chạy

        planning_busy = True
        globals()["__PLANNER_DONE__"] = False
        globals()["__PLANNER_RESULT__"] = []

        # snapshot an toàn (copy cấu trúc thay đổi)
        snap_grid   = list(grid)
        snap_pac    = tuple(pac)
        snap_foods  = set(foods)
        snap_pies   = set(pies)
        snap_ghosts = [(tuple(pos), d) for (pos, d) in ghosts]
        snap_exit   = exit_pos
        snap_ttl    = ttl
        snap_step   = step_mod

        def _worker():
            try:
                acts, _, _ = plan_from_snapshot(
                    snap_grid, snap_pac, snap_foods, snap_pies, snap_ghosts, snap_exit, snap_ttl, snap_step
                )
            except Exception:
                acts = []
            globals()["__PLANNER_RESULT__"] = acts
            globals()["__PLANNER_DONE__"] = True

        t = threading.Thread(target=_worker, daemon=True)
        globals()["__PLANNER_THREAD__"] = t
        t.start()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE or event.type == pygame.WINDOWSIZECHANGED:
                pass

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                    continue

                # Toggle AUTO, không ghi file; reset lịch sử
                if event.key == pygame.K_a:
                    auto_mode = not auto_mode
                    auto_step_cooldown = 0
                    globals()["__GUI_AUTO_ACTIONS__"] = []
                    run_actions_history.clear()
                    run_coords_history.clear()

                    if auto_mode:
                        try:
                            actions, coords, total_cost = plan_from_snapshot(
                                grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod
                            )
                            if not actions:
                                print("[AUTO] No plan.")
                                auto_mode = False
                                continue
                            globals()["__GUI_AUTO_ACTIONS__"] = list(actions)
                            print(f"[AUTO] Planned len={len(actions)}")
                        except Exception as e:
                            print("[AUTO] Planning error:", e)
                            auto_mode = False
                            globals()["__GUI_AUTO_ACTIONS__"] = []
                    continue

                # Teleport 1–4 / numpad 1–4 (manual)
                if event.key in (
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
                        target_action = {0:"TUL",1:"TUR",2:"TBL",3:"TBR"}[key2idx[event.key]]
                        (grid, pac, foods, pies, ghosts, exit_pos,
                         ttl, step_mod, logical_surface, died, rotated) = apply_action_step(
                            target_action, grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, screen, logical_surface
                        )
                        if died:
                            reset_game()

                # Manual N/S/E/W
                key_to_action = {
                    pygame.K_UP:"N", pygame.K_DOWN:"S", pygame.K_LEFT:"W", pygame.K_RIGHT:"E",
                }
                if event.key in key_to_action:
                    a = key_to_action[event.key]
                    (grid, pac, foods, pies, ghosts, exit_pos,
                     ttl, step_mod, logical_surface, died, rotated) = apply_action_step(
                        a, grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, screen, logical_surface
                    )
                    if died:
                        reset_game()

        # --- AUTO: chạy theo ACTION với cooldown + REPLAN nền khi XOAY ---
        if auto_mode:
            if planning_busy:
                if globals()["__PLANNER_DONE__"]:
                    new_actions = globals().get("__PLANNER_RESULT__", [])
                    globals()["__GUI_AUTO_ACTIONS__"] = list(new_actions)
                    planning_busy = False
                    globals()["__PLANNER_THREAD__"] = None
                    globals()["__PLANNER_DONE__"] = False
                    globals()["__PLANNER_RESULT__"] = []
                    auto_step_cooldown = AUTO_STEP_COOLDOWN_FRAMES
            else:
                acts = globals().get("__GUI_AUTO_ACTIONS__", [])
                if acts:
                    if auto_step_cooldown > 0:
                        auto_step_cooldown -= 1
                    else:
                        a = acts.pop(0)
                        (grid, pac, foods, pies, ghosts, exit_pos,
                         ttl, step_mod, logical_surface, died, rotated) = apply_action_step(
                            a, grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, screen, logical_surface
                        )
                        if died:
                            auto_mode = False
                            globals()["__GUI_AUTO_ACTIONS__"] = []
                        else:
                            # ghi nhận lịch sử sau mỗi bước thành công
                            run_actions_history.append(a)
                            run_coords_history.append(tuple(pac))

                            if rotated:
                                spawn_replan_background()

                            # Completed?
                            if len(foods) == 0 and tuple(pac) == exit_pos:
                                auto_mode = False
                                globals()["__GUI_AUTO_ACTIONS__"] = []
                                total_cost = float(len(run_actions_history))
                                write_outputs(run_coords_history, run_actions_history, total_cost)
                                print(f"[AUTO] Finished. Steps={len(run_actions_history)}. Files written to {OUTPUT_DIR}.")

                            auto_step_cooldown = AUTO_STEP_COOLDOWN_FRAMES
                else:
                    auto_mode = False

        # vẽ
        draw_grid(logical_surface, grid, tuple(pac), foods, exit_pos, pies, ghosts, ttl, step_mod, auto_mode)

        # Overlay báo replan
        if planning_busy:
            overlay = pygame.Surface(logical_surface.get_size(), pygame.SRCALPHA)
            hud_rect = pygame.Rect(0, len(grid)*CELL_LOGICAL, logical_surface.get_width(), HUD_H)
            pygame.draw.rect(overlay, (0, 0, 0, 140), hud_rect)
            font = pygame.font.SysFont(None, 22)
            msg = font.render("Replanning...", True, (80, 220, 180))
            overlay.blit(msg, (8, len(grid)*CELL_LOGICAL + 8))
            logical_surface.blit(overlay, (0,0))

        scale_and_present(screen, logical_surface)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    print("Using map:", DEFAULT_LAYOUT_PATH)
    print("Output dir:", OUTPUT_DIR)
    main()
