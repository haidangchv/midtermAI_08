import threading, pygame
from .config import (FPS, AUTO_STEP_COOLDOWN_FRAMES, SPRITE_SIZE, ASSETS_DIR,
                     COLOR_BG, CELL_LOGICAL, HUD_H, resolve_layout_path)
from .assets import AssetManager
from .render import Renderer
from .layout import load_layout_file, parse_grid, corner_anchors, is_at_anchor
from .planner import PlanService
from .action import ActionExecutor
from .io_output import write_outputs

class PacmanGame:
    def __init__(self, cli_layout=None):
        self.layout_path = resolve_layout_path(cli_layout)
        self.grid, self.pac, self.foods, self.exit_pos, self.pies, self.ghosts = None, None, None, None, None, None
        self.ttl = 0
        self.step_mod = 0
        self.steps_total = 0
        self.auto_mode = False
        self.auto_step_cooldown = 0
        self.auto_actions = []

        self.assets = AssetManager()
        self.renderer = Renderer(self.assets)
        self.exec = ActionExecutor(self.renderer)
        self.plan = PlanService()

        self.planning_busy = False
        self.plan_thread = None
        self.plan_done = False
        self.plan_result = []

        self.run_actions_history = []
        self.run_coords_history  = []
        self.game_complete = False

    def reset_game_state(self):
        self.grid = load_layout_file(self.layout_path)
        start, foods, exit_pos, pies, ghosts = parse_grid(self.grid)
        self.pac = list(start)
        self.foods = foods
        self.exit_pos = exit_pos
        self.pies = pies
        self.ghosts = ghosts
        self.ttl = 0
        self.step_mod = 0
        self.auto_mode = False
        self.auto_actions = []
        self.auto_step_cooldown = 0
        self.steps_total = 0
        self.run_actions_history.clear()
        self.run_coords_history.clear()
        self.game_complete = False
        self.renderer.new_surface(self.grid)

    def spawn_replan_background(self):
        if self.planning_busy: return
        self.planning_busy = True
        self.plan_done = False
        self.plan_result = []

        snap_grid   = list(self.grid)
        snap_pac    = tuple(self.pac)
        snap_foods  = set(self.foods)
        snap_pies   = set(self.pies)
        snap_ghosts = [(tuple(pos), d) for (pos, d) in self.ghosts]
        snap_exit   = self.exit_pos
        snap_ttl    = self.ttl
        snap_step   = self.step_mod

        def _worker():
            try:
                acts, _, _ = self.plan.plan_one_goal(
                    snap_grid, snap_pac, snap_foods, snap_pies, snap_ghosts, snap_exit, snap_ttl, snap_step
                )
            except Exception:
                acts = []
            self.plan_result = acts
            self.plan_done = True

        t = threading.Thread(target=_worker, daemon=True)
        self.plan_thread = t
        t.start()

    def run(self):
        pygame.init()
        info = pygame.display.Info()
        start_w = int(info.current_w * 0.9)
        start_h = int(info.current_h * 0.9)
        screen = pygame.display.set_mode((start_w, start_h), pygame.RESIZABLE)
        pygame.display.set_caption("Pacman – AUTO")
        clock = pygame.time.Clock()

        # assets
        self.assets.ensure_loaded()

        # init state
        self.reset_game_state()

        running = True
        print("Using map:", self.layout_path)

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type in (pygame.VIDEORESIZE, pygame.WINDOWSIZECHANGED):
                    pass

                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        running = False
                        continue

                    if self.game_complete and event.key == pygame.K_r:
                        self.reset_game_state()
                        continue

                    # toggle auto
                    if event.key == pygame.K_a:
                        self.auto_mode = not self.auto_mode
                        self.auto_step_cooldown = 0
                        self.auto_actions = []
                        self.run_actions_history.clear()
                        self.run_coords_history.clear()
                        if self.auto_mode:
                            try:
                                actions, coords, total_cost = self.plan.plan_one_goal(
                                    self.grid, self.pac, self.foods, self.pies, self.ghosts,
                                    self.exit_pos, self.ttl, self.step_mod
                                )
                                if not actions:
                                    print("[AUTO] No plan.")
                                    self.auto_mode = False
                                else:
                                    self.auto_actions = list(actions)
                                    print(f"[AUTO] Planned len={len(actions)} (one-goal)")
                            except Exception as e:
                                print("[AUTO] Planning error:", e)
                                self.auto_mode = False
                                self.auto_actions = []
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
                        if not is_at_anchor(self.grid, self.pac):
                            print("[Teleport] Not at a corner anchor -> ignored")
                        else:
                            before = tuple(self.pac)
                            target_action = {0:"TUL",1:"TUR",2:"TBL",3:"TBR"}[key2idx[event.key]]
                            (self.grid, self.pac, self.foods, self.pies, self.ghosts, self.exit_pos,
                             self.ttl, self.step_mod, died, rotated) = \
                                self.exec.apply_action_step(
                                    target_action, self.grid, self.pac, self.foods, self.pies,
                                    self.ghosts, self.exit_pos, self.ttl, self.step_mod, screen
                                )
                            if died:
                                self.reset_game_state()
                            else:
                                if tuple(self.pac) != before:
                                    self.steps_total += 1
                                if len(self.foods) == 0 and tuple(self.pac) == self.exit_pos:
                                    self.game_complete = True
                        continue

                    # Manual arrows
                    key_to_action = {
                        pygame.K_UP:"N", pygame.K_DOWN:"S", pygame.K_LEFT:"W", pygame.K_RIGHT:"E",
                    }
                    if event.key in key_to_action:
                        a = key_to_action[event.key]
                        before = tuple(self.pac)
                        (self.grid, self.pac, self.foods, self.pies, self.ghosts, self.exit_pos,
                         self.ttl, self.step_mod, died, rotated) = \
                            self.exec.apply_action_step(
                                a, self.grid, self.pac, self.foods, self.pies, self.ghosts,
                                self.exit_pos, self.ttl, self.step_mod, screen
                            )
                        if died:
                            self.reset_game_state()
                        else:
                            if tuple(self.pac) != before:
                                self.steps_total += 1
                            if len(self.foods) == 0 and tuple(self.pac) == self.exit_pos:
                                self.game_complete = True
                        continue

            # AUTO stepper
            if self.auto_mode and not self.game_complete:
                if self.planning_busy:
                    if self.plan_done:
                        self.auto_actions = list(self.plan_result)
                        self.planning_busy = False
                        self.plan_thread = None
                        self.plan_done = False
                        self.plan_result = []
                        self.auto_step_cooldown = AUTO_STEP_COOLDOWN_FRAMES
                else:
                    acts = self.auto_actions
                    if acts:
                        if self.auto_step_cooldown > 0:
                            self.auto_step_cooldown -= 1
                        else:
                            a = acts.pop(0)
                            before = tuple(self.pac)
                            (self.grid, self.pac, self.foods, self.pies, self.ghosts, self.exit_pos,
                             self.ttl, self.step_mod, died, rotated) = \
                                self.exec.apply_action_step(
                                    a, self.grid, self.pac, self.foods, self.pies, self.ghosts,
                                    self.exit_pos, self.ttl, self.step_mod, screen
                                )
                            if died:
                                self.auto_mode = False
                                self.auto_actions = []
                            else:
                                moved = (tuple(self.pac) != before)
                                if moved:
                                    self.steps_total += 1
                                    self.run_actions_history.append(a)
                                    self.run_coords_history.append(tuple(self.pac))
                                    if len(self.foods) == 0 and tuple(self.pac) == self.exit_pos:
                                        self.auto_mode = False
                                        self.auto_actions = []
                                        total_cost = float(len(self.run_actions_history))
                                        write_outputs(self.run_coords_history, self.run_actions_history, total_cost)
                                        print(f"[AUTO] Finished. Steps={len(self.run_actions_history)}. Files written to output/.")
                                        self.game_complete = True
                                else:
                                    # NO-OP: kế hoạch cũ không còn hợp lệ -> replan
                                    self.auto_actions = []
                                    if not self.planning_busy:
                                        self.spawn_replan_background()
                                self.auto_step_cooldown = AUTO_STEP_COOLDOWN_FRAMES

                        # queue rỗng: replan
                        if not self.auto_actions and not self.planning_busy and not self.game_complete and self.auto_mode:
                            self.spawn_replan_background()
                    else:
                        if not self.planning_busy:
                            self.spawn_replan_background()

            # render
            dt_ms = clock.get_time()
            self.renderer.update_anim(dt_ms)
            self.renderer.draw_grid(self.grid, tuple(self.pac), self.foods, self.exit_pos,
                                    self.pies, self.ghosts, self.ttl, self.step_mod,
                                    self.auto_mode, self.steps_total)

            if self.planning_busy:
                overlay = pygame.Surface(self.renderer.logical_surface.get_size(), pygame.SRCALPHA)
                font = pygame.font.SysFont(None, 22)
                msg = font.render("REPLANNING...", True, (80, 220, 180))
                pad_x, pad_y = 8, 4
                chip_w = msg.get_width() + pad_x * 2
                chip_h = msg.get_height() + pad_y * 2
                x = self.renderer.logical_surface.get_width() - chip_w - 10
                y = len(self.grid) * CELL_LOGICAL + 8
                chip = pygame.Surface((chip_w, chip_h), pygame.SRCALPHA)
                chip.fill((0, 0, 0, 160))
                overlay.blit(chip, (x, y))
                overlay.blit(msg, (x + pad_x, y + pad_y))
                self.renderer.logical_surface.blit(overlay, (0, 0))

            if self.game_complete:
                steps_text = f"steps: {self.steps_total}"
                self.renderer.draw_endgame_overlay(screen, steps_text)

            self.renderer.present(screen)
            pygame.display.flip()
            clock.tick(FPS)

        pygame.quit()
