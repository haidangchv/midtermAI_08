from astar import astar
from pacman_problem import PacmanProblem
from bfs import bfs  # <-- thêm
from heuristics import HeuristicPacmanMST

SAMPLE = [
    "%%%%%%%%",
    "%P....E%",
    "%......%",
    "%%%%%%%%",
]

def parse_sample(grid):
    start = None; foods = []; exit_pos = None; pies = []
    for r,row in enumerate(grid):
        for c,ch in enumerate(row):
            if ch == 'P': start = (r,c)
            elif ch == '.': foods.append((r,c))
            elif ch == 'E': exit_pos = (r,c)
            elif ch == 'O': pies.append((r,c))
    return start, foods, exit_pos, pies

def main():
    start, foods, exit_pos, pies = parse_sample(SAMPLE)
    # Thêm 1 ma đi ngang ở hàng giữa: bắt đầu bên trái, hướng sang phải
    ghosts = [((1,1), +1)]
    prob = PacmanProblem(SAMPLE, start, foods, exit_pos, pies=pies, ghosts=ghosts)
    h = HeuristicPacmanMST(SAMPLE, exit_pos)
    res_a = astar(prob, h, graph_search=True)
    print("[A*] cost:", res_a["cost"], "expanded:", res_a["expanded"], "generated:", res_a["generated"])

    res_b = bfs(prob, graph_search=True)
    print("[BFS] cost:", res_b["cost"], "expanded:", res_b["expanded"], "generated:", res_b["generated"])


if __name__ == "__main__":
    main()
