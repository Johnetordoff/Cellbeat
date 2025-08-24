import audio
import numpy as np

# Agent types
EMPTY, VERTICAL_REFLECT, HORIZONTAL_REFLECT = 0, 1, 2
ROBOT, CLOCKWISE_ROTATOR, COUNTERCLOCKWISE_ROTATOR = 3, 4, 6
BELL_0 = 10
DJ = 20
DOWNSTAIRS = 30
UPSTAIRS = 31

DIRECTIONS = {
    "UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)
}

STATIC_AGENTS = {
    EMPTY,
    VERTICAL_REFLECT, HORIZONTAL_REFLECT,
    CLOCKWISE_ROTATOR, COUNTERCLOCKWISE_ROTATOR,
    BELL_0,
    DOWNSTAIRS, UPSTAIRS
}


class BaseAgent:
    def apply_rules(self, static_grid, dynamic_grid):
        raise NotImplementedError


class MovingAgent(BaseAgent):
    def __init__(self, agent_type):
        self.agent_type = agent_type
        self.directions = {}
        self.speeds = {}
        self.counters = {}

    def apply_rules(self, static_grid, dynamic_grid, cell_attributes):
        rows, cols = static_grid.shape

        def apply_static(dir_vec, cell_val):
            if cell_val == VERTICAL_REFLECT:
                return (dir_vec[0], -dir_vec[1])
            if cell_val == HORIZONTAL_REFLECT:
                return (-dir_vec[0], dir_vec[1])
            if cell_val == CLOCKWISE_ROTATOR:
                return (-dir_vec[1], dir_vec[0])
            if cell_val == COUNTERCLOCKWISE_ROTATOR:
                return (dir_vec[1], -dir_vec[0])
            return dir_vec

        # Only move cells of this agent type (works for RobotAgent & DJAgent)
        positions = [(int(r), int(c)) for r, c in np.argwhere(dynamic_grid == self.agent_type)]

        # -------- Phase 1: intentions --------
        intents = []
        for r, c in positions:
            speed = int(self.speeds.get((r, c), 1))
            counter = int(self.counters.get((r, c), 0))
            old_dir = self.directions.get((r, c), DIRECTIONS["RIGHT"])

            next_counter = (counter + 1) % max(1, speed)
            will_step = (next_counter == 0)

            if will_step:
                # Peek next cell using current heading to compute transform for the *candidate* step
                nr, nc = (r + old_dir[0]) % rows, (c + old_dir[1]) % cols
                new_dir = apply_static(old_dir, static_grid[nr, nc])
                tr, tc = (r + new_dir[0]) % rows, (c + new_dir[1]) % cols
                intents.append({
                    'from': (r, c),
                    'to': (tr, tc),
                    'will_step': True,
                    'old_dir': old_dir,
                    'new_dir': new_dir,
                    'speed': speed,
                    'next_counter': 0,
                })
            else:
                intents.append({
                    'from': (r, c),
                    'to': None,
                    'will_step': False,
                    'old_dir': old_dir,
                    'new_dir': None,
                    'speed': speed,
                    'next_counter': next_counter,
                })

        # Helpers
        want_to = {}
        mover_from = {}
        for it in intents:
            if it['will_step']:
                want_to.setdefault(it['to'], []).append(it)
                mover_from[it['from']] = it

        def is_swap(it):
            other = mover_from.get(it['to'])
            return bool(other and other['to'] == it['from'])

        def occupant_is_vacating(cell):
            return cell in mover_from

        # -------- Pre-compute pass-throughs --------
        # Map: origin -> {'exit': (r,c), 'final_dir': (dr,dc), 'tone_cells': [(r,c), ...]}
        passthrough = {}

        # (A) Head-on meet-in-the-middle pass-through (two claim same middle from opposite dirs)
        for target, claims in want_to.items():
            if len(claims) == 2:
                a, b = claims
                va, vb = a['new_dir'], b['new_dir']
                if va[0] == -vb[0] and va[1] == -vb[1]:
                    ea = ((target[0] + va[0]) % rows, (target[1] + va[1]) % cols)
                    eb = ((target[0] + vb[0]) % rows, (target[1] + vb[1]) % cols)

                    def exit_ok(cell):
                        r, c = cell
                        if dynamic_grid[r, c] == self.agent_type:
                            return occupant_is_vacating(cell)
                        return True

                    # Require distinct viable exits
                    if ea != eb and exit_ok(ea) and exit_ok(eb):
                        passthrough[a['from']] = {
                            'exit': ea,
                            'final_dir': apply_static(va, static_grid[ea]),
                            'tone_cells': [target],  # stepped through the middle
                        }
                        passthrough[b['from']] = {
                            'exit': eb,
                            'final_dir': apply_static(vb, static_grid[eb]),
                            'tone_cells': [target],
                        }

        # (B) Same-direction overtake:
        # Faster mover intends to step into a cell occupied by a *non-vacating* robot
        # that faces the same direction; the faster skips ahead one more cell.
        for it in intents:
            if not it['will_step']:
                continue
            tr, tc = it['to']
            # target currently occupied by same agent type and *not* vacating
            if dynamic_grid[tr, tc] == self.agent_type and not occupant_is_vacating((tr, tc)):
                # aligned headings?
                lead_dir = self.directions.get((tr, tc), DIRECTIONS["RIGHT"])
                # Require no transform at the meeting cell (keeps "same direction" literal)
                if it['old_dir'] == lead_dir and it['new_dir'] == it['old_dir']:
                    # candidate exit one more step forward
                    er, ec = ((tr + it['new_dir'][0]) % rows, (tc + it['new_dir'][1]) % cols)

                    # Exit must be free or vacating, and nobody else should also be claiming it
                    occupied = (dynamic_grid[er, ec] == self.agent_type) and not occupant_is_vacating((er, ec))
                    contested = len(want_to.get((er, ec), [])) > 0
                    if not occupied and not contested:
                        passthrough[it['from']] = {
                            'exit': (er, ec),
                            'final_dir': apply_static(it['new_dir'], static_grid[er, ec]),
                            'tone_cells': [(tr, tc)],  # touched the lead robot's cell
                        }

        # -------- Phase 2: commit --------
        new_dynamic = np.zeros_like(dynamic_grid)
        new_dirs, new_speeds, new_counters = {}, {}, {}

        for it in intents:
            r, c = it['from']
            speed = it['speed']

            if it['will_step']:
                # Any pre-approved pass-through (head-on or overtake) takes precedence
                if (r, c) in passthrough:
                    er, ec = passthrough[(r, c)]['exit']
                    fdir = passthrough[(r, c)]['final_dir']
                    new_dynamic[er, ec] = self.agent_type
                    new_dirs[(er, ec)] = fdir
                    new_speeds[(er, ec)] = speed
                    new_counters[(er, ec)] = 0
                    for pr, pc in passthrough[(r, c)]['tone_cells']:
                        if static_grid[pr, pc]:
                            self.play_tone(pr, pc, cell_attributes)
                    # (Optional) also play tone on the exit cell if desired:
                    # if static_grid[er, ec]: self.play_tone(er, ec, cell_attributes)
                    continue

                tr, tc = it['to']
                claimants = want_to.get((tr, tc), [])
                allow_move = False

                if is_swap(it):
                    allow_move = True
                elif len(claimants) == 1:
                    if dynamic_grid[tr, tc] == self.agent_type:
                        allow_move = occupant_is_vacating((tr, tc))
                    else:
                        allow_move = True
                else:
                    allow_move = False

                if allow_move:
                    new_dynamic[tr, tc] = self.agent_type
                    new_dirs[(tr, tc)] = it['new_dir']
                    new_speeds[(tr, tc)] = speed
                    new_counters[(tr, tc)] = 0
                    if static_grid[tr, tc]:
                        self.play_tone(tr, tc, cell_attributes)
                    continue

            # Stay put (cadence wait or unresolved conflict)
            new_dynamic[r, c] = self.agent_type
            new_dirs[(r, c)] = it['old_dir']
            new_speeds[(r, c)] = speed
            new_counters[(r, c)] = it['next_counter']

        self.directions, self.speeds, self.counters = new_dirs, new_speeds, new_counters
        return new_dynamic

        def is_swap(it):
            """Two-way swap: A.to == B.from and B.to == A.from."""
            other = mover_from.get(it['to'])
            return bool(other and other['to'] == it['from'])

        def occupant_is_vacating(cell):
            """Cell's current occupant is moving out this tick."""
            return cell in mover_from

        # -------- Phase 2: commit --------
        new_dynamic = np.zeros_like(dynamic_grid)
        new_dirs, new_speeds, new_counters = {}, {}, {}

        for it in intents:
            r, c = it['from']
            speed = it['speed']

            if it['will_step']:
                tr, tc = it['to']
                claimants = want_to.get((tr, tc), [])

                allow_move = False

                if is_swap(it):
                    # explicit pass-through: allow both legs of the swap
                    allow_move = True
                elif len(claimants) == 1:
                    # no multi-claim conflict; if target was occupied, allow only if occupant vacates
                    if dynamic_grid[tr, tc] == ROBOT:
                        allow_move = occupant_is_vacating((tr, tc))
                    else:
                        allow_move = True
                else:
                    # multiple claimants to same target (not a swap): can't represent >1 in a cell
                    allow_move = False

                if allow_move:
                    # Successful move (direction updates only on success)
                    new_dynamic[tr, tc] = ROBOT
                    new_dirs[(tr, tc)] = it['new_dir']
                    new_speeds[(tr, tc)] = speed
                    new_counters[(tr, tc)] = 0
                    if static_grid[tr, tc]:
                        self.play_tone(tr, tc, cell_attributes)
                    continue  # next robot

            # Stay put (waiting due to cadence, or blocked by multi-claim / non-vacating occupant)
            new_dynamic[r, c] = ROBOT
            new_dirs[(r, c)] = it['old_dir']  # keep heading if we didn't move
            new_speeds[(r, c)] = speed
            new_counters[(r, c)] = it['next_counter']  # cadence keeps advancing

        # Publish new per-robot state (still keyed by position for compatibility)
        self.directions, self.speeds, self.counters = new_dirs, new_speeds, new_counters
        return new_dynamic

    def play_tone(self, r, c, cell_attributes):
        # Per-cell params
        attr = cell_attributes.get((r, c), {'pitch': 440.0, 'duration': 0.5, 'velocity': 100})
        # Grid meta (sentinel)
        meta = cell_attributes.get((-1, -1), {})
        vol = float(meta.get('grid_volume', 1.0))
        # Scale velocity and channel gain by grid volume (clamped velocity)
        eff_vel = max(0, min(127, int(attr.get('velocity', 100) * vol)))
        audio.play_tone(attr['pitch'], attr['duration'], eff_vel, [vol])


class RobotAgent(MovingAgent):
    def __init__(self):
        super().__init__(ROBOT)


class DJAgent(MovingAgent):
    def __init__(self):
        super().__init__(DJ)


class StaticAgent(BaseAgent):
    def apply_rules(self, static_grid, dynamic_grid):
        return static_grid


AGENTS = [RobotAgent(), DJAgent(), StaticAgent()]
