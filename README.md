*This project has been created as part of the 42 curriculum by asylla.*

# Fly-In-2

## Description

Fly-In-2 is a drone delivery routing simulator. Given a map made of named
"zones" (hubs) connected to one another, and a fleet of drones starting at a
common start hub, the program plans a route for every drone to the end hub,
then runs a turn-based simulation that moves the drones along their planned
routes while respecting per-zone capacity limits and per-connection link
capacity limits. The result is printed as a turn-by-turn move log and, unless
disabled, replayed visually in a 2D pygame window.

The goal of the project is to combine:
- a **sampling-based motion planner** (RRT*, adapted to a discrete zone
  graph instead of continuous space) to compute a path for each drone,
- a **discrete-event simulation** layer that resolves conflicts between
  drones competing for the same zone or connection at the same time, and
- a **visualizer** that makes the resulting traffic pattern easy to inspect
  and debug.

## Instructions

### Requirements

- Python 3.12+
- A virtual environment (recommended)
- Dependencies listed in `requirements.txt` (notably `pygame`)

### Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running

```bash
make run maps/<difficulty>/<map_name>.txt
```

which is equivalent to:

```bash
python3 -m src.main maps/<difficulty>/<map_name>.txt
```

Useful flags:

| Flag | Description |
|---|---|
| `--no-pygame` | Run the simulation and print the move log only, without opening the visualizer window |
| `--drone-image PATH` | Use a custom sprite for the drone icon (default: `assets/drones.png`) |
| `--seed N` | Seed the RRT* planner's random generator, for reproducible runs |

Example maps are provided under `maps/`, organized by difficulty
(`easy/`, `medium/`, `hard/`, `challenger/`).

### Linting / type-checking

```bash
make lint
```

Runs `flake8` and `mypy` (with `--disallow-untyped-defs`,
`--check-untyped-defs`, `--warn-return-any`, `--warn-unused-ignores`,
`--ignore-missing-imports`) over `src/` and `tests/`.

### Visualizer controls

| Key / action | Effect |
|---|---|
| `ESC` | Quit |
| `SPACE` | Advance one turn manually |
| `P` | Toggle auto-play on/off |
| `+` / `=` | Speed up auto-play |
| `-` | Slow down auto-play |
| Mouse wheel | Zoom in/out |
| Left-click drag | Pan the camera |

## Algorithm choices and implementation strategy

### Map format

A map file declares, in order: the number of drones (`nb_drones:`), one
`start_hub:` zone, one `end_hub:` zone, any number of `hub:` zones, and any
number of `connection:` lines linking two zones by name. Zones carry
optional metadata in brackets — `color`, `zone` (type: `normal`,
`restricted`, `priority`, or `blocked`), and `max_drones` (occupancy cap).
Connections carry an optional `max_link_capacity` (how many drones may use
that edge simultaneously). The parser (`src/parser.py`) validates the file
line by line and rejects malformed syntax, undefined zones in connections,
and duplicate connections between the same pair of zones.

### Path planning — RRT*

`src/planner_rrt_star.py` implements a graph-adapted RRT* (Rapidly-exploring
Random Tree, with rewiring for asymptotic optimality):

1. **Sampling** — each iteration picks a random zone name, biased 15% of the
   time toward the goal zone to accelerate convergence.
2. **Nearest node** — the tree node geometrically closest (Euclidean
   distance over zone `(x, y)` coordinates) to the sample is selected as the
   expansion point.
3. **Extension** — among that node's *unvisited* graph neighbors, the one
   closest to the sample is added to the tree. Restricting the candidate set
   to unvisited neighbors was a deliberate fix: picking the nearest neighbor
   regardless of visited status can strand the search behind a node whose
   only useful edge is not the geometrically closest one, which showed up in
   practice on maps with narrow bottlenecks.
4. **Parent selection & cost model** — the new node's parent is chosen from
   nearby tree nodes to minimize accumulated cost, where the cost of
   entering a zone depends on its type: `blocked` zones are effectively
   unreachable (very high cost), `restricted` zones cost more (and take two
   simulation turns to cross), `priority` zones cost slightly less, and
   `normal` zones cost a flat baseline.
5. **Rewiring** — existing nearby nodes are re-parented through the new node
   whenever that lowers their accumulated cost, which is what gives RRT* its
   optimality guarantee over plain RRT.
6. **Goal connection** — whenever a newly added node is adjacent to the goal,
   the goal is (re-)attached to the tree if the resulting path is cheaper
   than any found so far.

Each drone currently gets its own independent planning call (with a shared
cost model and RNG), and a drone whose path is interrupted by a blocked zone
or persistent congestion is re-planned live via `Simulation._reroute`.

### Simulation — turn-based conflict resolution

`src/simulation.py` advances the world one discrete turn at a time:

1. Drones already mid-transit (crossing a `restricted`, two-turn zone) are
   advanced first.
2. Every drone still active declares an *intention* — the next zone on its
   planned path.
3. Zone occupancy is checked against `max_drones` (`_can_enter`), and edge
   usage is checked against `max_link_capacity`, so two drones can't
   over-fill a hub or over-saturate a link in the same turn.
4. Drones that are denied entry simply wait for a future turn; drones
   walking into a zone that has since become `blocked` are rerouted on the
   spot.
5. The simulation ends when every drone reaches the end hub, or raises an
   error if progress stalls for too many consecutive turns (deadlock
   detection) or exceeds a maximum turn count.

This capacity/edge-cap layer is what turns a single shortest-path
computation into an actual multi-agent traffic problem: on constrained maps
(narrow bottlenecks, single-capacity hubs), drones queue and interleave
rather than all taking the theoretically shortest route simultaneously.

## Visual representation

`src/visualizer.py` renders the live simulation with `pygame`:

- **Zones** are drawn as glowing circles, colored per their declared
  `color` (a special `rainbow` color cycles through the spectrum over
  time), with a black cross overlay marking `blocked` zones and the zone
  name labeled underneath.
- **Connections** are drawn as lines between zone centers, giving an
  immediate read of the graph's topology.
- **Drones** are rendered as sprite icons at their interpolated position —
  including mid-flight, where a drone crossing a two-turn `restricted` zone
  is drawn smoothly moving between its origin and destination rather than
  jumping instantly. Multiple drones occupying the same zone are fanned out
  in a small circle so they don't overlap.
- **HUD overlay** shows the current turn number, how many drones have been
  delivered out of the total, whether auto-play is on, the current playback
  speed, and the available keybindings.
- **Camera controls** (pan and zoom) let you inspect dense or large maps
  (e.g. the `challenger/` tier) at a comfortable scale.

Together, these make it possible to *see* congestion happen — a bottleneck
zone visibly accumulating drones queued behind it, or a rerouted drone
peeling off its original path — rather than only reading it out of the
textual move log.

## Example input and output

Given `maps/easy/01_linear_path.txt`:

```
# Easy Level 1: Simple linear path
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
```

Running:

```bash
make run maps/easy/01_linear_path.txt
```

produces a turn-by-turn move log such as:

```
D1-waypoint1
D1-waypoint2 D2-waypoint1
D2-waypoint2
D1-goal
D2-goal

Simulation complete.
 Drones delivered: 2
 Total turns: 5
```

(each `Dn-zone` entry records drone `n` arriving at `zone` on that turn),
followed by the pygame window opening to replay the same sequence visually,
unless `--no-pygame` was passed.

## Resources

### References on the topic

- Karaman, S. & Frazzoli, E., *Sampling-based Algorithms for Optimal Motion
  Planning* — the original RRT* paper.
- Steven M. LaValle, *Planning Algorithms* (Cambridge University Press) —
  background on rapidly-exploring random trees and sampling-based planning.
- [PythonRobotics](https://github.com/AtsushiSakai/PythonRobotics) — reference
  implementations of RRT/RRT* used to sanity-check the general shape of the
  algorithm.
- [pygame documentation](https://www.pygame.org/docs/) — used for the
  visualizer (surfaces, event loop, drawing primitives).
- Python `dataclasses`, `enum`, and `typing` documentation — used throughout
  the data model (`Zone`, `Drone`, `Connection`) and for satisfying `mypy`.

### AI usage

An AI assistant (Claude) was used throughout development, primarily as an
interactive debugging partner rather than as a code generator from scratch:

- **Debugging** — pinpointing the cause of runtime errors (missing
  dataclass fields, `==` vs `=` typos, name-mangled private attributes,
  wrong variable names in assignments, an inverted comparison producing
  cycles in the RRT* tree, a set-membership check performed after the
  element was already inserted, etc.) from tracebacks and, where the error
  message alone wasn't enough, by adding targeted `print` debugging and
  interpreting the output.
- **Algorithm review** — reviewing the RRT* implementation (`plan()`,
  nearest-neighbor selection, parent selection, rewiring, goal connection)
  against the standard algorithm and identifying where the implementation
  deviated from it, such as neighbor selection not excluding already-visited
  nodes, and the rewiring step missing its cost-improvement check.
- **Static analysis fixes** — resolving `mypy --disallow-untyped-defs
  --warn-return-any` and `flake8` findings (line-length violations, `Any`
  return types requiring `cast`, tuple-length narrowing after `sorted()`,
  redundant/unused `# type: ignore` comments).
- **Documentation** — drafting this README from the project's actual
  structure, behavior, and the debugging history of the conversation.

All core design decisions (map format, capacity/deadlock model, the choice
to use RRT* at all) and the original code were the author's own; AI
assistance was used to find and fix specific bugs and to review code
quality, not to design the project from a blank page.
