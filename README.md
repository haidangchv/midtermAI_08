# Midterm Skeleton (A* – 8-Puzzle & Pacman)

## Quick start
```bash midtermAI_08
# Task 1: Bài toán 8-Puzzle
cd source/task1_eight_puzzle
'Astar_8Puzzle.ipynb' : Jupyter Notebook chứa mã thực thi cho bài toán 8-Puzzle.

# Task 2: GUI Pacman
## yêu cầu: pip install pygame
python -m source.task2_pacman.gui   
### Đầu ra chế độ AUTO
- Viết vào: `output/path.txt` và `output/output.txt`
    + Định dạng output.txt: 
    cost: <tong_so_buoc>
    actions:
    North
    West
    ...

    + Định dạng path.txt: mỗi dòng là một toạ độ r c của Pacman sau mỗi bước.

# Task 2: thí nghiệm A* (không GUI)
python source/task2_pacman/experiments.py
### Đầu ra thí nghiệm
- Viết vào: `output/experiments_report.txt`  
  Định dạng (1 dòng):
  cost=<int> | expanded=<int> | generated=<int> | time=<ms>ms

- Ghi console (ví dụ):
  Done: cost=135 | exp=12345 | gen=23456 | time=987.6ms

```

Thư mục chính:
- `source/task1_eight_puzzle`: Astar_8Puzzle.ipynb
- `source/task2_pacman`: PacmanProblem + heuristic MST + thí nghiệm; `gui/` có khung pygame; `Task2_Pacman.pdf`: Tài liệu bài làm.
- `presentation_template.pdf`, `demo.txt`.

Cấu trúc thư mục:
midterm_08_52300186/
├── source/
 |          ├── task1_eight_puzzle/
 |           |          ├── Astar_8Puzzle.ipynb
 |           |          ├── ClassDiagram.png
 |           |          ├── goal.png
 |           |          ├── tree_h0_nodes.png
 |           |          └── tree_hpair_nodes.png
 |          ├── task2_pacman/
 |           |          ├── assets/
 |           |           |          ├── food_images/
 |           |           |           |          └── food.png
 |           |           |          ├── ghost_images/
 |           |           |           |          ├── blue.png
 |           |           |           |          ├── dead.png
 |           |           |           |          ├── orange.png
 |           |           |           |          ├── pink.png
 |           |           |           |          ├── powerup.png
 |           |           |           |          └── red.png
 |           |           |          ├── player_images/
 |           |           |           |          ├── 1.png
 |           |           |           |          ├── 2.png
 |           |           |           |          ├── 3.png
 |           |           |           |          └── 4.png
 |           |          ├── gui/
 |           |           |          ├── action.py
 |           |           |          ├── assets.py
 |           |           |          ├── config.py
 |           |           |          ├── game.py
 |           |           |          ├── io_output.py
 |           |           |          ├── layout.py
 |           |           |          ├── planner.py
 |           |           |          ├── render.py
 |           |           |          └── __main__.py
 |           |          ├── input/
 |           |           |          └── task02_pacman_example_map.txt
 |           |          ├── output/
 |           |           |          ├── experiments_report.txt
 |           |           |          ├── output.txt
 |           |           |          └── path.txt
 |           |          ├── astar.py
 |           |          ├── Classdiagram_task2.png
 |           |          ├── experiments.py
 |           |          ├── heuristics.py
 |           |          ├── pacman_problem.py
 |           |          └── Task2_Pacman.pdf
├── demo.txt
├── presentation.pdf
└── README.md
