from __future__ import annotations

 
class Display:
    @staticmethod
    def print_log(turn_log: list[str]) -> None:
        for line in turn_log:
            print(line)

    @staticmethod
    def print_summary(num_drones: int, turns: int) -> None:
        print("\nSimulation complete.")
        print(f" Drones delivered: {num_drones}")
        print(f" Total turns: {turns}")
