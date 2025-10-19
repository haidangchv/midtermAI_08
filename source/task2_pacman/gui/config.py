import os, sys

# ----- FIX IMPORT PATHS -----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))           # .../task2_pacman/gui
TASK2_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))       # .../task2_pacman
sys.path.insert(0, TASK2_DIR)

# ----- I/O PATHS -----
REPO_ROOT  = os.path.abspath(os.path.join(TASK2_DIR, "..", ".."))
INPUT_DIR  = os.path.join(REPO_ROOT, "input")
OUTPUT_DIR = os.path.join(TASK2_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----- FILES -----
PATH_TXT = os.path.join(OUTPUT_DIR, "path.txt")
OUT_TXT  = os.path.join(OUTPUT_DIR, "output.txt")

# ----- CONSTANTS -----
CELL_LOGICAL = 32
HUD_H = 84
FPS = 60
AUTO_STEP_COOLDOWN_FRAMES = 6

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

# ----- ASSETS -----
ASSETS_DIR = os.path.join(TASK2_DIR, "assets")
SPRITE_SIZE = CELL_LOGICAL

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
        os.path.join(BASE_DIR, filename),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(
        "Không tìm thấy file layout. Đặt file vào 'input/task02_pacman_example_map.txt' "
        "hoặc truyền đường dẫn khi chạy."
    )
