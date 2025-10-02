import argparse, random, time
from astar import astar
from problem import EightPuzzleProblem
from heuristics import HCeilHalf
from draw_tree import draw_tree

GOALS = [
    ((1,2,3),(4,5,6),(7,8,0)),
    # TODO: thêm 3 goal còn lại theo đề
]

def shuffle_state(state, k=5, seed=0):
    random.seed(seed)
    P = EightPuzzleProblem(state, GOALS)
    s = state
    for _ in range(k):
        acts = list(P.actions(s))
        if not acts:
            break
        s = P.result(s, random.choice(acts))
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n", type=int, default=1, help="số case random")
    args = ap.parse_args()

    init = ((1,2,3),(4,5,6),(7,0,8))  # sample
    for i in range(args.n):
        s0 = shuffle_state(init, k=5, seed=args.seed + i)
        prob = EightPuzzleProblem(s0, GOALS)
        h = HCeilHalf(GOALS[0])
        t0 = time.time()
        res = astar(prob, h, graph_search=True)
        dt = (time.time() - t0) * 1000
        if res["solution"]:
            draw_tree(res["solution"], n=5)
        print(f"[Case {i}] cost={res['cost']}, expanded={res['expanded']}, generated={res['generated']}, time_ms={dt:.2f}")

if __name__ == "__main__":
    main()
