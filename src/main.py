from __future__ import annotations

import argparse
import sys

from .display import Display
from .parser import Parser
from .planner_rrt_star import RRTStarPlanner
from .simulation import Simulation
from .visualizer import PygameVisualizer


def main() -> int:
    ap = argparse.ArgumentParser(description="Fly-in drone routing")
    ap.add_argument("map_file", help="Path to map file")
    ap.add_argument(
        "--no-pygame",
        action="store_true",
        help="Disable pygame visualizer"
    )
    ap.add_argument(
        "--drone-image",
        default="assets/drones.png",
        help="Drone sprite PNG path"
    )
    ap.add_argument(
        "--seed",
        type=int, default=42,
        help="RRT* random seed"
    )
    args = ap.parse_args()

    try:
        parsed = Parser(args.map_file).parse()
    except Exception as exc:
        print(f"Error parsing map: {exc}")
        return 1

    planner = RRTStarPlanner(parsed.zones, parsed.connections, seed=args.seed)

    try:
        sim = Simulation(
            zones=parsed.zones,
            connections=parsed.connections,
            start_hub=parsed.start_hub,
            end_hub=parsed.end_hub,
            num_drones=parsed.num_drones,
            planner=planner,
        )
        turn_log = sim.run()
    except Exception as exc:
        print(f"Simulation error: {exc}")
        return 1

    Display.print_log(turn_log)
    Display.print_summary(parsed.num_drones, len(turn_log))

    if not args.no_pygame:
        vis_sim = Simulation(
            zones=parsed.zones,
            connections=parsed.connections,
            start_hub=parsed.start_hub,
            end_hub=parsed.end_hub,
            num_drones=parsed.num_drones,
            planner=planner,
        )
        vis = PygameVisualizer(vis_sim, drone_image_path=args.drone_image)
        vis.run(turn_log)

    return 0


if __name__ == "__main__":
    sys.exit(main())
