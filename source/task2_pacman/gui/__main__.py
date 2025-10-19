# source/task2_pacman/gui/__main__.py

import os, sys

try:
    from .game import PacmanGame  # chạy bằng: python -m source.task2_pacman.gui
except Exception:
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))       # .../source/task2_pacman/gui
    PARENT   = os.path.dirname(THIS_DIR)                        # .../source/task2_pacman
    if PARENT not in sys.path:
        sys.path.insert(0, PARENT)
    from gui.game import PacmanGame

def main():
    cli_layout = sys.argv[1] if len(sys.argv) > 1 else None
    PacmanGame(cli_layout).run()

if __name__ == "__main__":
    main()
