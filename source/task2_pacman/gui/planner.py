from astar import astar
from heuristics import HeuristicPacmanMST
from pacman_problem import PacmanProblem

def _run_astar_safe(problem, hz, goal_fn=None, max_expanded=200000):
    try:
        try:
            res = astar(problem, hz, graph_search=True, goal_fn=goal_fn, max_expanded=max_expanded)
        except TypeError:
            res = astar(problem, hz, graph_search=True, goal_fn=goal_fn)
    except Exception as e:
        print("[A*] Exception:", e)
        return {}
    return res if isinstance(res, dict) else {}

def _to_pos(x):
    try:
        r,c = x
        if isinstance(r,int) and isinstance(c,int): return (r,c)
    except Exception: pass
    return None

def sanitize_inputs(grid, pac, foods, pies, ghosts, exit_pos):
    pac_t = _to_pos(pac) if pac is not None else None
    if pac_t is None: pac_t = (0,0)
    exit_t = _to_pos(exit_pos) if exit_pos is not None else None
    if exit_t is None: exit_t = (0,0)

    foods_set=set()
    try:
        for p in list(foods):
            pt = _to_pos(p)
            if pt is not None: foods_set.add(pt)
    except Exception: foods_set=set()

    pies_set=set()
    try:
        for p in list(pies):
            pt=_to_pos(p)
            if pt is not None: pies_set.add(pt)
    except Exception: pies_set=set()

    ghosts_list=[]
    try:
        for g in list(ghosts):
            pos=None; d=None
            if isinstance(g, dict):
                pos=_to_pos(g.get("pos")); d=g.get("dir", +1)
            else:
                if isinstance(g,(list,tuple)) and len(g)==2:
                    pos=_to_pos(g[0]); d=g[1]
            if pos is None: continue
            d=+1 if d not in (-1,+1) else d
            ghosts_list.append([pos,d])
    except Exception: ghosts_list=[]

    return pac_t, foods_set, pies_set, ghosts_list, exit_t

class PlanService:
    """Gói toàn bộ logic lập kế hoạch (one-goal + full)."""
    def plan_full(self, grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod):
        try:
            pac, foods, pies, ghosts, exit_pos = sanitize_inputs(grid, pac, foods, pies, ghosts, exit_pos)

            cur_grid   = list(grid)
            cur_pac    = tuple(pac)
            cur_foods  = sorted(list(foods))
            cur_pies   = sorted(list(pies))
            cur_ghosts = [(tuple(pos), d) for (pos, d) in ghosts]
            cur_exit   = exit_pos
            cur_ttl    = int(ttl) if isinstance(ttl, int) else 0
            cur_step   = int(step_mod) % 30 if isinstance(step_mod, int) else 0

            total_actions,total_coords,total_cost = [],[],0.0

            while True:
                if len(cur_foods) == 0:
                    prob = PacmanProblem(cur_grid, cur_pac, cur_foods, cur_exit,
                                         pies=cur_pies, ghosts=cur_ghosts,
                                         ttl0=cur_ttl, steps_mod30_0=cur_step, rot_idx0=0)
                    hz = HeuristicPacmanMST(prob)
                    res = _run_astar_safe(prob, hz, goal_fn=None)

                    if not res or not res.get("solution"):
                        return total_actions, total_coords, total_cost

                    states, actions = res["solution"], res["actions"]
                    for s in states[1:]:
                        if s is not None: total_coords.append(s.pacman)
                    total_actions.extend(actions or [])
                    total_cost += float(res.get("cost", 0.0))
                    return total_actions, total_coords, total_cost

                best=None
                target_count_after = len(cur_foods)-1
                def goal_fn(s, target_count=target_count_after):
                    return (s is not None) and (len(s.foods) == target_count)

                for _ in list(cur_foods):
                    prob = PacmanProblem(cur_grid, cur_pac, cur_foods, cur_exit,
                                         pies=cur_pies, ghosts=cur_ghosts,
                                         ttl0=cur_ttl, steps_mod30_0=cur_step, rot_idx0=0)
                    hz = HeuristicPacmanMST(prob)
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
                    if s is not None: total_coords.append(s.pacman)
                total_actions.extend(actions or [])
                total_cost += float(res.get("cost", 0.0))

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
            print("[PLAN] Exception in plan_full:", e)
            return [], [], 0.0

    def plan_one_goal(self, grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod):
        try:
            pac, foods, pies, ghosts, exit_pos = sanitize_inputs(grid, pac, foods, pies, ghosts, exit_pos)

            cur_grid   = list(grid)
            cur_pac    = tuple(pac)
            cur_foods  = sorted(list(foods))
            cur_pies   = sorted(list(pies))
            cur_ghosts = [(tuple(pos), d) for (pos, d) in ghosts]
            cur_exit   = exit_pos
            cur_ttl    = int(ttl) if isinstance(ttl, int) else 0
            cur_step   = int(step_mod) % 30 if isinstance(step_mod, int) else 0

            if len(cur_foods) == 0:
                prob = PacmanProblem(cur_grid, cur_pac, cur_foods, cur_exit,
                                     pies=cur_pies, ghosts=cur_ghosts,
                                     ttl0=cur_ttl, steps_mod30_0=cur_step, rot_idx0=0)
                hz = HeuristicPacmanMST(prob)
                res = _run_astar_safe(prob, hz, goal_fn=None)
                if not res or not res.get("solution"): return [], [], 0.0
                states, actions = res["solution"], res["actions"]
                coords = [s.pacman for s in states[1:] if s is not None]
                return (actions or []), coords, float(res.get("cost", 0.0))

            target_count_after = len(cur_foods) - 1
            def goal_fn(s, target_count=target_count_after):
                return (s is not None) and (len(s.foods) == target_count)

            prob = PacmanProblem(cur_grid, cur_pac, cur_foods, cur_exit,
                                 pies=cur_pies, ghosts=cur_ghosts,
                                 ttl0=cur_ttl, steps_mod30_0=cur_step, rot_idx0=0)
            hz = HeuristicPacmanMST(prob)
            res = _run_astar_safe(prob, hz, goal_fn=goal_fn)
            if not res or not res.get("solution"): return [], [], 0.0
            states, actions = res["solution"], res["actions"]
            coords = [s.pacman for s in states[1:] if s is not None]
            return (actions or []), coords, float(res.get("cost", 0.0))

        except Exception as e:
            print("[PLAN-ONE] Exception:", e)
            return [], [], 0.0
