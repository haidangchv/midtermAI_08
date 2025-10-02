from astar import astar
from pacman_problem import PacmanProblem
from heuristics import HeuristicPacmanMST

SAMPLE = [
    "%%%%%%%%",
    "%P....E%",
    "%......%",
    "%%%%%%%%",
]

def parse_sample(grid):
    start = None; foods = []; exit_pos = None
    for r,row in enumerate(grid):
        for c,ch in enumerate(row):
            if ch == 'P': start = (r,c)
            elif ch == '.': foods.append((r,c))
            elif ch == 'E': exit_pos = (r,c)
    return start, foods, exit_pos

def main():
    start, foods, exit_pos = parse_sample(SAMPLE)
    prob = PacmanProblem(SAMPLE, start, foods, exit_pos)
    h = HeuristicPacmanMST(SAMPLE, exit_pos)
    res = astar(prob, h, graph_search=True)
    print("cost:", res["cost"], "expanded:", res["expanded"], "generated:", res["generated"])

if __name__ == "__main__":
    main()
