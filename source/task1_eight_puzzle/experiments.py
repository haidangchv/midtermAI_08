import argparse, random, time
from astar import astar
from bfs import bfs
from problem import EightPuzzleProblem
from heuristics import HCeilHalf
from draw_tree import draw_tree

GOALS = [
    ((1,2,3),(4,5,6),(7,8,0)),  # G1
    ((8,7,6),(5,4,3),(2,1,0)),  # G2
    ((0,1,2),(3,4,5),(6,7,8)),  # G3
    ((0,8,7),(6,5,4),(3,2,1)),  # G4
]

def shuffle_state(state, k=5, seed=0):
    random.seed(seed)
    P = EightPuzzleProblem(state, GOALS)
    s = state
    for _ in range(k):
        acts = list(P.actions(s))
        if not acts: break
        s = P.result(s, random.choice(acts))
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n", type=int, default=1, help="số case random")
    args = ap.parse_args()

    init = ((1,2,3),(4,5,6),(7,0,8))
    for i in range(args.n):
        s0 = shuffle_state(init, k=5, seed=args.seed + i)
        prob = EightPuzzleProblem(s0, GOALS)
        h = HCeilHalf(GOALS[0])

        t0 = time.time(); res_a = astar(prob, h, graph_search=True); dt_a = (time.time()-t0)*1000
        if res_a["solution"]: draw_tree(res_a["solution"], n=5)

        t1 = time.time(); res_b = bfs(prob, graph_search=True); dt_b = (time.time()-t1)*1000

        print(f"[Case {i}] A*: cost={res_a['cost']}, expanded={res_a['expanded']}, generated={res_a['generated']}, time_ms={dt_a:.2f}")
        print(f"[Case {i}] BFS: cost={res_b['cost']}, expanded={res_b['expanded']}, generated={res_b['generated']}, time_ms={dt_b:.2f}")

if __name__ == "__main__":
    main()
