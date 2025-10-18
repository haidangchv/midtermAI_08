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
from heuristics import HeuristicTeleportAware
from astar import astar

# ----- I/O PATHS -----
REPO_ROOT = os.path.abspath(os.path.join(TASK2_DIR, "..", ".."))
INPUT_DIR = os.path.join(REPO_ROOT, "input")
OUTPUT_DIR = os.path.join(TASK2_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PATH_TXT = os.path.join(OUTPUT_DIR, "path.txt")
OUT_TXT  = os.path.join(OUTPUT_DIR, "output.txt")

# ----- CONSTANTS -----
CELL_LOGICAL = 32
HUD_H = 84
FPS = 30
AUTO_STEP_COOLDOWN_FRAMES = 8

# ---- COLORS ----
COLOR_BG        = (10, 10, 10)
COLOR_WALL      = (45, 45, 55)
COLOR_WALL_EDGE = (25, 25, 32)
COLOR_FLOOR     = (22, 22, 22)
COLOR_GRID      = (40, 40, 40)
COLOR_EXIT      = (0, 150, 230)
COLOR_FOOD      = (240, 240, 240)
COLOR_PIE       = (228, 146, 52)
COLOR_ANCHOR    = (0, 200, 255)
COLOR_HUD_TEXT  = (245, 245, 245)
COLOR_HUD_EMPH  = (80, 220, 180)

# ----- SPRITES -----
ASSETS_DIR = os.path.join(TASK2_DIR, "assets")
SPRITE_SIZE = CELL_LOGICAL

PACMAN_IMG = None      # fallback tĩnh
FOOD_IMG   = None
# Ghost nhiều màu (nếu có file). Fallback 1 ảnh chung.
GHOST_IMGS = {}        # {'red': Surface, 'blue': Surface, 'orange': Surface, 'pink': Surface}
GHOST_FALLBACK = None  # Surface 1 màu dùng chung

# Pacman 4-frame animation (há – mím) kiểu assets/player_images/{1..4}.png
PAC_FRAMES = []                     # list[Surface]
PAC_FRAME_SEQ = [0, 1, 2, 3, 2, 1]  # ping-pong
PAC_FRAME_INDEX = 0
PAC_ANIM_INTERVAL_MS = 90
LAST_PAC_DIR = 0  # 0=E,1=W,2=N,3=S

# ----- LAYOUT RESOLVE -----
def resolve_layout_path(cli_path=None):
    filename = "task02_pacman_example_map.txt"
    candidates = []
    if cli_path:
        candidates.append(cli_path)
    candidates += [
        os.path.join(REPO_ROOT, "input", filename),
        os.path.join(TASK2_DIR, "input", filename),
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

# ----- IMAGE UTILS -----
def _first_exist(paths):
    for p in paths:
        if os.path.isfile(p):
            return p
    return None

def load_img(path, size):
    """Load ảnh an toàn (convert_alpha chỉ khi đã set display)."""
    surf = pygame.image.load(path)
    if pygame.display.get_surface():
        try:
            surf = surf.convert_alpha()
        except pygame.error:
            pass
    return pygame.transform.smoothscale(surf, (size, size))

def load_sprite_pac():
    cand = [
        os.path.join(ASSETS_DIR, "pacman.png"),
        os.path.join(ASSETS_DIR, "Pacman.png"),
        os.path.join(ASSETS_DIR, "player.png"),
        os.path.join(ASSETS_DIR, "pac.png"),
    ]
    p = _first_exist(cand)
    if p:
        return load_img(p, SPRITE_SIZE)
    # fallback: hình tròn
    surf = pygame.Surface((SPRITE_SIZE, SPRITE_SIZE), pygame.SRCALPHA)
    pygame.draw.circle(surf, (255,205,0), (SPRITE_SIZE//2, SPRITE_SIZE//2), SPRITE_SIZE//2 - 2)
    return surf

def load_sprite_food():
    cand = [
        os.path.join(ASSETS_DIR, "food_images", "food.png"),
        os.path.join(ASSETS_DIR, "food.png"),
        os.path.join(ASSETS_DIR, "dot.png"),
    ]
    p = _first_exist(cand)
    if p:
        size = max(8, int(SPRITE_SIZE ))
        return load_img(p, size)
    # fallback: chấm tròn
    size = max(8, int(SPRITE_SIZE * 0.25))
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, COLOR_FOOD, (size//2, size//2), size//2)
    return surf

def load_sprite_ghosts(strict=False):
    """
    Tải ghost đủ 4 màu nếu có:
      assets/ghost_images/{red,blue,orange,pink}.png
    Nếu thiếu:
      - strict=True => raise FileNotFoundError
      - strict=False => fallback sang ảnh chung assets/ghost.png (nếu có)
    """
    names = ["red", "blue", "orange", "pink"]
    base_dir = os.path.join(ASSETS_DIR, "ghost_images")
    imgs = {}
    missing = []

    for name in names:
        p = os.path.join(base_dir, f"{name}.png")
        if os.path.isfile(p):
            imgs[name] = load_img(p, SPRITE_SIZE)
        else:
            missing.append(p)

    if missing and strict:
        raise FileNotFoundError("Thiếu ảnh ghost:\n" + "\n".join(f" - {m}" for m in missing))

    # Chuẩn bị fallback 1 ảnh
    fallback_paths = [
        os.path.join(ASSETS_DIR, "ghost.png"),
        os.path.join(ASSETS_DIR, "Ghost.png"),
        os.path.join(ASSETS_DIR, "enemy.png"),
    ]
    fp = _first_exist(fallback_paths)

    fb_img = load_img(fp, SPRITE_SIZE) if fp else None
    return imgs, fb_img

def load_pac_frames_from_player_images():
    """Ưu tiên assets/player_images/1..4.png; fallback assets/pacman_images/; nếu thiếu thì dùng PACMAN_IMG."""
    cand_dirs = [
        os.path.join(ASSETS_DIR, "player_images"),
        os.path.join(ASSETS_DIR, "pacman_images"),
    ]
    names = ["1.png", "2.png", "3.png", "4.png"]
    for d in cand_dirs:
        if all(os.path.isfile(os.path.join(d, n)) for n in names):
            return [load_img(os.path.join(d, n), SPRITE_SIZE) for n in names]
    base = PACMAN_IMG if PACMAN_IMG is not None else load_sprite_pac()
    return [base, base, base, base]

def _ensure_sprites_loaded():
    """Gọi SAU set_mode."""
    global PACMAN_IMG, FOOD_IMG, GHOST_IMGS, GHOST_FALLBACK
    if PACMAN_IMG is None: PACMAN_IMG = load_sprite_pac()
    if FOOD_IMG   is None: FOOD_IMG   = load_sprite_food()
    if not GHOST_IMGS or GHOST_FALLBACK is None:
        GHOST_IMGS, GHOST_FALLBACK = load_sprite_ghosts(strict=False)

def _ensure_pac_anim_loaded():
    global PAC_FRAMES, PAC_FRAME_INDEX
    if not PAC_FRAMES:
        PAC_FRAMES = load_pac_frames_from_player_images()
        PAC_FRAME_INDEX = 0

def _blit_center(surface, img, cell_rect):
    ir = img.get_rect()
    surface.blit(img, (cell_rect.x + (cell_rect.w - ir.w)//2,
                       cell_rect.y + (cell_rect.h - ir.h)//2))

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
        first_open_from_top_left(grid),
        first_open_from_top_right(grid),
        first_open_from_bottom_left(grid),
        first_open_from_bottom_right(grid)
    )

def is_at_anchor(grid, pac):
    return tuple(pac) in set(corner_anchors(grid))

# ----- SURFACE / SCALING -----
def make_logical_surface(grid: List[str]):
    w = len(grid[0]) * CELL_LOGICAL
    h = len(grid) * CELL_LOGICAL + HUD_H
    surf = pygame.Surface((w, h), pygame.SRCALPHA).convert_alpha()
    surf.fill((0, 0, 0, 0))
    return surf

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
    screen.fill(COLOR_BG)
    if rect.size != logical_surface.get_size():
        scaled = pygame.transform.smoothscale(logical_surface, rect.size)
        screen.blit(scaled, rect.topleft)
    else:
        screen.blit(logical_surface, rect.topleft)

# ----- DRAW / HUD -----
def draw_grid(surface, grid, pac, foods, exit_pos, pies, ghosts, ttl, step_mod, auto_mode):
    surface.fill((0, 0, 0, 0))
    R, C = len(grid), len(grid[0])
    cell = CELL_LOGICAL
    floor = pygame.Surface((cell, cell), pygame.SRCALPHA)
    floor.fill(COLOR_FLOOR)
    grid_edge = pygame.Surface((cell, cell), pygame.SRCALPHA)
    pygame.draw.rect(grid_edge, COLOR_GRID, pygame.Rect(0, 0, cell, cell), 1)

    # tiles
    for r in range(R):
        for c in range(C):
            x, y = c*cell, r*cell
            rect = pygame.Rect(x, y, cell, cell)
            ch = grid[r][c]
            if ch == '%':
                pygame.draw.rect(surface, COLOR_WALL, rect, border_radius=2)
                pygame.draw.rect(surface, COLOR_WALL_EDGE, rect, 1, border_radius=2)
            else:
                surface.blit(floor, (x, y))
                surface.blit(grid_edge, (x, y))
            # items
            if (r, c) in pies:
                pygame.draw.circle(surface, COLOR_PIE, rect.center, cell//5)
            if (r, c) in foods:
                _blit_center(surface, FOOD_IMG, rect)
            if exit_pos == (r, c):
                pygame.draw.rect(surface, COLOR_EXIT, rect, 3, border_radius=4)

    # ghosts (theo màu nếu có file)
    color_order = ["red", "blue", "pink", "orange"]  # đổi thứ tự tùy ý
    for i, ((gr, gc), _dir) in enumerate(ghosts):
        grect = pygame.Rect(gc*cell, gr*cell, cell, cell)
        key = color_order[i % len(color_order)]
        img = GHOST_IMGS.get(key, GHOST_FALLBACK) if GHOST_IMGS else GHOST_FALLBACK
        if img is None:
            # last-resort: chấm tròn đỏ
            img = pygame.Surface((cell, cell), pygame.SRCALPHA)
            pygame.draw.circle(img, (215,60,60), (cell//2, cell//2), cell//3)
        _blit_center(surface, img, grect)

    # PACMAN (4-frame + xoay/flip theo hướng)
    prect = pygame.Rect(pac[1]*cell, pac[0]*cell, cell, cell)
    try:
        fidx = PAC_FRAME_SEQ[PAC_FRAME_INDEX] if PAC_FRAMES else 0
        base_img = PAC_FRAMES[fidx] if PAC_FRAMES else PACMAN_IMG
    except Exception:
        base_img = PACMAN_IMG

    img = base_img
    if LAST_PAC_DIR == 1:      # West
        img = pygame.transform.flip(base_img, True, False)
    elif LAST_PAC_DIR == 2:    # North
        img = pygame.transform.rotate(base_img, 90)
    elif LAST_PAC_DIR == 3:    # South
        img = pygame.transform.rotate(base_img, 270)
    _blit_center(surface, img, prect)

    # anchors
    anchors = corner_anchors(grid)
    font_small = pygame.font.SysFont(None, 18)
    for i, (ar, ac) in enumerate(anchors):
        arect = pygame.Rect(ac*cell, ar*cell, cell, cell)
        pygame.draw.rect(surface, COLOR_ANCHOR, arect, 2, border_radius=4)
        tag = font_small.render(str(i+1), True, COLOR_ANCHOR)
        surface.blit(tag, (arect.x + 4, arect.y + 2))

    # HUD
    font = pygame.font.SysFont(None, 20)
    y0 = cell*R + 6
    remaining = len(foods)
    hud_bg = pygame.Surface((cell*C, HUD_H-6), pygame.SRCALPHA)
    hud_bg.fill((0, 0, 0, 120))
    surface.blit(hud_bg, (0, cell*R))

    hud1 = font.render(
        f"TTL: {ttl}   step%30: {step_mod}   AUTO: {'ON' if auto_mode else 'OFF'}   FOOD LEFT: {remaining}   PAC: ({pac[0]},{pac[1]})",
        True, COLOR_HUD_TEXT
    )
    surface.blit(hud1, (8, y0))

    if is_at_anchor(grid, pac):
        hint = font.render("Teleport: phím 1–4 (TL, TR, BL, BR)", True, COLOR_HUD_EMPH)
        surface.blit(hint, (8, y0 + 20))

    if tuple(pac) == exit_pos and remaining > 0:
        warn = font.render(f"⚠ Cần ăn thêm {remaining} food trước khi EXIT!", True, (255, 210, 90))
        surface.blit(warn, (8, y0 + 40))

# ----- OVERLAYS / RESET -----
def show_center_message(screen, text, millis=1200):
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    box_w, box_h = int(screen.get_width()*0.5), 120
    box_x = (screen.get_width() - box_w)//2
    box_y = (screen.get_height() - box_h)//2
    box = pygame.Rect(box_x, box_y, box_w, box_h)
    pygame.draw.rect(screen, (28, 28, 32), box, border_radius=12)
    pygame.draw.rect(screen, (255, 90, 90), box, 2, border_radius=12)
    font_big = pygame.font.SysFont(None, 42)
    font_small = pygame.font.SysFont(None, 22)
    msg = font_big.render(text, True, (255, 220, 220))
    hint = font_small.render("Resetting...", True, (220, 220, 220))
    screen.blit(msg, (box.centerx - msg.get_width()//2, box_y + 18))
    screen.blit(hint, (box.centerx - hint.get_width()//2, box_y + 68))
    pygame.display.flip()
    pygame.time.wait(millis)

def draw_endgame_overlay(screen, logical_surface, steps_text=""):
    """Vẽ overlay chiến thắng, không chặn loop; bấm R để chơi lại."""
    overlay = pygame.Surface(logical_surface.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))

    # khung hộp
    box_w, box_h = int(logical_surface.get_width() * 0.6), 180
    box_x = (logical_surface.get_width() - box_w)//2
    box_y = (logical_surface.get_height() - box_h)//2
    box = pygame.Rect(box_x, box_y, box_w, box_h)

    pygame.draw.rect(overlay, (28, 28, 32, 240), box, border_radius=12)
    pygame.draw.rect(overlay, (80, 220, 180, 255), box, 3, border_radius=12)

    font_big   = pygame.font.SysFont(None, 42)
    font_mid   = pygame.font.SysFont(None, 24)
    title      = font_big.render("Complete the mission!", True, (240, 240, 240))
    subtitle   = font_mid.render("Press R to play again • Esc to exit", True, (210, 210, 210))
    metric_txt = font_mid.render(steps_text, True, (210, 210, 210)) if steps_text else None

    overlay.blit(title,   (box.centerx - title.get_width()//2,   box_y + 26))
    if metric_txt:
        overlay.blit(metric_txt, (box.centerx - metric_txt.get_width()//2, box_y + 72))
    overlay.blit(subtitle,(box.centerx - subtitle.get_width()//2, box_y + 110))

    logical_surface.blit(overlay, (0, 0))

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
    Thực thi 1 action (N/S/E/W hoặc TUL/TUR/TBL/TBR) với tick ma + rotate mỗi 30 bước.
    ĐÂM TƯỜNG/teleport không hợp lệ -> NO-OP (không tăng bước/cost).
    """
    global LAST_PAC_DIR
    R, C = len(grid), len(grid[0])
    prev_r, prev_c = pac[0], pac[1]
    nr, nc = prev_r, prev_c

    if a in ("N","S","E","W"):
        drdc = {"N":(-1,0),"S":(1,0),"W":(0,-1),"E":(0,1)}
        dr, dc = drdc[a]
        tr, tc = nr + dr, nc + dc
        blocked = (
            not (0 <= tr < R and 0 <= tc < C) or
            (grid[tr][tc] == '%' and ttl <= 0)
        )
        if blocked:
            return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, logical_surface, False, False
        nr, nc = tr, tc
        # cập nhật hướng để xoay/flip animation
        LAST_PAC_DIR = {"E":0, "W":1, "N":2, "S":3}[a]

    elif a in ("TUL","TUR","TBL","TBR"):
        anchors = corner_anchors(grid)
        if tuple(pac) not in set(anchors):
            return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, logical_surface, False, False
        idx = {"TUL":0,"TUR":1,"TBL":2,"TBR":3}[a]
        nr, nc = anchors[idx]
        # teleport: giữ hướng hiện tại

    else:
        return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, logical_surface, False, False

    # thực hiện tick
    pac = [nr, nc]
    step_mod = (step_mod + 1) % 30
    ttl = max(0, ttl - 1)

    if tuple(pac) in foods:
        foods.remove(tuple(pac))
    if tuple(pac) in pies:
        ttl = 5
        pies.remove(tuple(pac))

    # Va chạm với ma (trước tick)
    for (gr,gc), _d in ghosts:
        if (gr,gc) == tuple(pac) and ttl == 0:
            show_center_message(screen, "💥 Bị ma bắt!")
            return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, logical_surface, True, False

    old_ghosts = ghosts
    ghosts = move_ghosts(grid, ghosts)

    # Sau tick + kiểm tra swap
    for (old_pos, _d1), (new_pos, _d2) in zip(old_ghosts, ghosts):
        if new_pos == tuple(pac):
            show_center_message(screen, "💥 Bị ma bắt!")
            return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, logical_surface, True, False
        if old_pos == (nr, nc) and new_pos == (prev_r, prev_c):
            show_center_message(screen, "💥 Bị ma bắt!")
            return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, logical_surface, True, False

    rotated = False
    if step_mod == 0:
        grid, pac_t, foods, pies, ghosts, exit_pos = rotate_world(
            grid, tuple(pac), foods, pies, ghosts, exit_pos
        )
        pac = list(pac_t)
        logical_surface = make_logical_surface(grid)
        rotated = True

    return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, logical_surface, False, rotated

# ----- I/O output -----
def write_outputs(path_coords, actions, cost):
    # path.txt
    with open(PATH_TXT, "w", encoding="utf-8") as f:
        for (r, c) in path_coords:
            f.write(f"{r} {c}\n")
    # output.txt
    name_map = {
        "N": "North",
        "S": "South",
        "E": "East",
        "W": "West",
        "TUL": "Stop", "TUR": "Stop", "TBL": "Stop", "TBR": "Stop",
    }
    pretty_actions = [name_map.get(a, "West") for a in actions]
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(f"cost: {int(cost) if cost == int(cost) else cost}\n")
        f.write("actions:\n")
        for act in pretty_actions:
            f.write(act + "\n")

# ----- Sanitizers để plan -----
def _to_pos(x):
    try:
        r, c = x
        if isinstance(r, int) and isinstance(c, int):
            return (r, c)
    except Exception:
        pass
    return None

def sanitize_inputs(grid, pac, foods, pies, ghosts, exit_pos):
    pac_t = _to_pos(pac) if pac is not None else None
    if pac_t is None:
        pac_t = (0, 0)

    exit_t = _to_pos(exit_pos) if exit_pos is not None else None
    if exit_t is None:
        exit_t = (0, 0)

    foods_set = set()
    try:
        for p in list(foods):
            pt = _to_pos(p)
            if pt is not None:
                foods_set.add(pt)
    except Exception:
        foods_set = set()

    pies_set = set()
    try:
        for p in list(pies):
            pt = _to_pos(p)
            if pt is not None:
                pies_set.add(pt)
    except Exception:
        pies_set = set()

    ghosts_list = []
    try:
        for g in list(ghosts):
            pos = None; d = None
            if isinstance(g, dict):
                pos = _to_pos(g.get("pos"))
                d = g.get("dir", +1)
            else:
                if isinstance(g, (list, tuple)) and len(g) == 2:
                    pos = _to_pos(g[0]); d = g[1]
            if pos is None:
                continue
            d = +1 if d not in (-1, +1) else d
            ghosts_list.append([pos, d])
    except Exception:
        ghosts_list = []

    return pac_t, foods_set, pies_set, ghosts_list, exit_t

# ----- PLANNER -----
def _run_astar_safe(problem, hz, goal_fn=None):
    """Gọi astar an toàn, luôn trả dict hoặc {}."""
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
        cur_ghosts = [(tuple(pos), d) for (pos, d) in ghosts]  # ((r,c), d)
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
                hz = HeuristicTeleportAware(prob)
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
                hz = HeuristicTeleportAware(prob)
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
    pygame.display.set_caption("Pacman – sprites & 4-frame animation, teleport anchors, BG replan on rotation")
    clock = pygame.time.Clock()

    # Dùng biến global để cập nhật animation index
    global PAC_FRAME_INDEX

    # Load sprites/frames SAU set_mode
    _ensure_sprites_loaded()
    _ensure_pac_anim_loaded()

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

    # Nhật ký khi hoàn thành
    run_actions_history = []   # action thực thi
    run_coords_history  = []   # toạ độ sau mỗi bước

    # Animation timer
    pac_anim_accum = 0

    # End game flag
    game_complete = False

    def reset_game():
        nonlocal grid, pac, foods, exit_pos, pies, ghosts, ttl, step_mod, logical_surface
        nonlocal auto_mode, auto_step_cooldown, planning_busy, game_complete
        (grid, pac, foods, exit_pos, pies, ghosts,
         ttl, step_mod, logical_surface, auto_mode, _) = reset_game_state()
        auto_step_cooldown = 0
        globals()["__GUI_AUTO_ACTIONS__"] = []
        planning_busy = False
        globals()["__PLANNER_THREAD__"] = None
        globals()["__PLANNER_DONE__"] = False
        globals()["__PLANNER_RESULT__"] = []
        run_actions_history.clear()
        run_coords_history.clear()
        game_complete = False

    def spawn_replan_background():
        nonlocal planning_busy
        if planning_busy:
            return
        planning_busy = True
        globals()["__PLANNER_DONE__"] = False
        globals()["__PLANNER_RESULT__"] = []

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
    print("Using map:", DEFAULT_LAYOUT_PATH)
    print("Output dir:", OUTPUT_DIR)

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

                # Restart khi đã hoàn thành
                if game_complete and event.key == pygame.K_r:
                    reset_game()
                    continue

                # Toggle AUTO
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

                # Teleport 1–4 / numpad 1–4
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
                        else:
                            if len(foods) == 0 and tuple(pac) == exit_pos:
                                game_complete = True
                    continue

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
                    else:
                        if len(foods) == 0 and tuple(pac) == exit_pos:
                            game_complete = True
                    continue

        # AUTO mode stepper + replan khi xoay
        if auto_mode and not game_complete:
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
                            run_actions_history.append(a)
                            run_coords_history.append(tuple(pac))
                            if rotated:
                                spawn_replan_background()
                            if len(foods) == 0 and tuple(pac) == exit_pos:
                                auto_mode = False
                                globals()["__GUI_AUTO_ACTIONS__"] = []
                                total_cost = float(len(run_actions_history))
                                write_outputs(run_coords_history, run_actions_history, total_cost)
                                print(f"[AUTO] Finished. Steps={len(run_actions_history)}. Files written to {OUTPUT_DIR}.")
                                # bật end game overlay
                                game_complete = True
                            auto_step_cooldown = AUTO_STEP_COOLDOWN_FRAMES
                else:
                    auto_mode = False

        # cập nhật animation
        dt_ms = clock.get_time()
        pac_anim_accum += dt_ms
        if pac_anim_accum >= PAC_ANIM_INTERVAL_MS:
            PAC_FRAME_INDEX = (PAC_FRAME_INDEX + 1) % len(PAC_FRAME_SEQ)
            pac_anim_accum = 0

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

        # End Game overlay
        if game_complete:
            steps_text = f"steps (AUTO): {len(run_actions_history)}" if run_actions_history else ""
            draw_endgame_overlay(screen, logical_surface, steps_text)

        scale_and_present(screen, logical_surface)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    print("Using map:", DEFAULT_LAYOUT_PATH)
    print("Output dir:", OUTPUT_DIR)
    main()
