# Midterm Skeleton (A* – 8-Puzzle & Pacman)

## Quick start
```bash
# Task 1: thử A* vs BFS
cd source/task1_eight_puzzle
python experiments.py --seed 42 --n 2

# Task 2: thử A* (không GUI)
cd ../task2_pacman
python experiments.py

# GUI Pacman (pygame scaffold)
cd gui
python main.py   # yêu cầu: pip install pygame
```

Thư mục chính:
- `source/task1_eight_puzzle`: A* generic, 8-Puzzle với 4 goal, BFS để so sánh, thí nghiệm & vẽ cây (txt).
- `source/task2_pacman`: PacmanProblem + heuristic MST + thí nghiệm; `gui/` có khung pygame.
- `results/`: nơi lưu log/ảnh.
- `presentation_template.md`, `demo.txt`.
