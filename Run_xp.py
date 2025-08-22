#!/usr/bin/env python3

from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any
from datetime import timedelta, date as date_cls

DATA_PATH = "run_rpg_data.json"
DATE_FMT = "%Y-%m-%d"  # keep it simple for v1

@dataclass
class Run:
    date: str           # "YYYY-MM-DD"
    distance_km: float  # e.g., 5.0
    duration_min: int   # e.g., 30
    notes: str = ""
    xp_awarded: int = 0 # computed when added

@dataclass
# Basic Xp Settings
class GameState:
    runs: List[Run]
    total_xp: int
    settings: Dict[str, Any]
    weekly_bonus_awarded: List[str] = None # Weekly Bonus

    @staticmethod
    def default() -> "GameState":
        return GameState(
            # This initializes stuff
            runs=[],
            weekly_bonus_awarded=[],
            total_xp=0,
            settings={
                # Variables Of Sorts, my Settings.
                "xp_per_km": 10,# Xp Per KM
                "xp_per_5min": 1,# XP Per 5/min
                "level_base_xp": 100, # Xp required Per level
                "level_growth": 1.25, # Xp growth per Level
                "last_save": None,
                # future ideas:
                # "streak_bonus": {...},
                # "penalties": {...},
            },
        )

# ---------- Persistence ----------

# Save and Load JSON File
def load_state(path: str = DATA_PATH) -> GameState:
    if not os.path.exists(path):
        return GameState.default()
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    # loads all variables from json, then returns them to program
    runs = [Run(**r) for r in raw.get("runs", [])]
    total_xp = int(raw.get("total_xp", 0))
    settings = raw.get("settings", GameState.default().settings)
    awarded = raw.get("weekly_bonus_awarded", [])
    return GameState(runs=runs, total_xp=total_xp, settings=settings,weekly_bonus_awarded=awarded)

# Saves all relevant info into a JSON file
def save_state(state: GameState, path: str = DATA_PATH) -> None:
    payload = {
        "runs": [asdict(r) for r in state.runs],
        "total_xp": state.total_xp,
        "settings": state.settings | {"last_save": datetime.now().isoformat(timespec="seconds")},
        "weekly_bonus_awarded": state.weekly_bonus_awarded,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

# ---------- XP logic (v1 placeholder) ----------

# Calculate Xp
def compute_run_xp(distance_km: float, duration_min: float, settings: Dict[str, Any]) -> int:
    per_km = settings.get("xp_per_km", 10) #Xp Per KM
    per_5 = settings.get("xp_per_5min", 1) #Xp Per 5min Running
    xp = distance_km * per_km + int(duration_min // 5) * per_5
    return int(round(xp))

# ---------- UI helpers ----------

def clear_screen():
    # portable enough for now
    os.system("cls" if os.name == "nt" else "clear")

def pause(msg: str = "Press Enter to continue..."):
    input(msg)

def print_header(title: str):
    print("=" * 50)
    print(title.upper().center(50))
    print("=" * 50)

# ---------- Functions ----------

# Convert stored time to MM:SS
def format_duration(minutes_float: float) -> str:
    total_seconds = int(round(minutes_float * 60))
    mm, ss = divmod(total_seconds, 60)
    return f"{mm:02d}:{ss:02d}"

# Weekly bonuses - Start sunday
def week_id_from_datestr(datestr: str) -> str:
    y, m, d = map(int, datestr.split("-"))
    day = date_cls(y, m, d)

    offset = (day.weekday() + 1) % 7  # 0 if Sunday, 1 if Monday, etc.
    sunday = day - timedelta(days=offset)

    year = sunday.year
    # Count weeks since the first Sunday of the year
    first_sunday = date_cls(year, 1, 1)
    if first_sunday.weekday() != 6:  # not already Sunday
        first_sunday += timedelta(days=(6 - first_sunday.weekday()))
    week_num = ((sunday - first_sunday).days // 7) + 1
    return f"{year}-W{week_num:02d}"

# Level logic
def level_from_xp(total_xp: int, settings: Dict[str, Any]) -> tuple[int, int, int]:
    base = int(settings.get("level_base_xp", 100))
    growth = float(settings.get("level_growth", 1.25))

    level = 1
    need = max(1, base)  # safety
    remaining = max(0, int(total_xp))

    while remaining >= need:
        remaining -= need
        level += 1
        need = max(1, int(round(need * growth)))

    # remaining is how much XP you have into the current level
    return level, remaining, need

# Level progress bar
def progress_bar(current: int, total: int, width: int = 20) -> str:
    if total <= 0:
        return f"[{'-'*width}] 0%"
    ratio = min(1.0, max(0.0, current / total))
    filled = int(round(width * ratio))
    return f"[{'#'*filled}{'-'*(width-filled)}] {int(ratio*100)}%"

from datetime import date as date_cls

# ---------- Menu actions ----------

# This is a Test Line

# List Runs
def action_list_runs(state: GameState):
    clear_screen()
    print_header("All Runs")
    if not state.runs:
        print("No runs logged yet.")
    else:
        for i, r in enumerate(state.runs, 1):
            print(f"{i:2d}. {r.date} | {r.distance_km:.2f} km | {format_duration(r.duration_min)} | +{r.xp_awarded} XP"
                  + (f" | {r.notes}" if r.notes else ""))
    print("\nTotal XP:", state.total_xp)
    pause()

# Last Run
def action_last_run(state: GameState):
    clear_screen()
    print_header("Last Run")
    if not state.runs:
        print("No runs logged yet.")
    else:
        r = state.runs[-1]
        print(f"Date: {r.date}")
        print(f"Distance: {r.distance_km:.2f} km")
        print(f"Duration: {format_duration(r.duration_min)}")
        print(f"XP Awarded: {r.xp_awarded}")
        if r.notes:
            print(f"Notes: {r.notes}")
    pause()

# Input New Run
def action_add_run(state: GameState):
    clear_screen()
    print_header("Add Run")
    # date default = today
    today = datetime.now().strftime(DATE_FMT)
    date = input(f"Date [{today}]: ").strip() or today

    # validate date format
    try:
        datetime.strptime(date, DATE_FMT)
    except ValueError:
        print("Invalid date. Use YYYY-MM-DD.")
        pause()
        return

    try:
        distance_km = float(input("Distance (km): ").strip())
        #duration_min = int(input("Duration (minutes): ").strip())
        duration_min = input("Duration (MM or MM:SS): ").strip()

        try:
            if ":" in duration_min:
                mm, ss = duration_min.split(":")
                minutes = int(mm)
                seconds = int(ss)
                duration_min = minutes + seconds / 60
        except ValueError:
            print("Invalid duration format. Use MM or MM:SS.")
            pause()
            return

    except ValueError:
        print("Invalid number entered.")
        pause()
        return

    notes = input("Notes (optional): ").strip()
    before_level, _, _ = level_from_xp(state.total_xp, state.settings)

    # Logic after input
    xp = compute_run_xp(distance_km, duration_min, state.settings)
    run = Run(date=date, distance_km=distance_km, duration_min=duration_min, notes=notes, xp_awarded=xp)
    state.runs.append(run)
    state.total_xp += xp

    week_id = week_id_from_datestr(date)
    target = int(state.settings.get("weekly_runs_target", 3))
    bonus  = int(state.settings.get("weekly_bonus_xp", 100))

    already_awarded = week_id in state.weekly_bonus_awarded
    count_now = runs_in_week(state, week_id)

    bonus_awarded_now = False
    if not already_awarded and count_now >= target:
        state.total_xp += bonus
        state.weekly_bonus_awarded.append(week_id)
        bonus_awarded_now = True

    save_state(state)

    after_level, xp_into, xp_need = level_from_xp(state.total_xp, state.settings)

    # existing prints
    if bonus_awarded_now:
        print(f"Weekly goal hit ({count_now}/{target}). Bonus +{bonus} XP!")
    print(f"\nRun saved. Gained +{xp} XP! Total XP: {state.total_xp}")
    if after_level > before_level:
        print(f"LEVEL UP! You reached Level {after_level}.")
        print(f"XP {progress_bar(xp_into, xp_need)}")
    else:
        print(f"Progress to next level: {xp_into}/{xp_need} XP {progress_bar(xp_into, xp_need)}")
    pause()

# Options
def action_options(state: GameState):
    clear_screen()
    print_header("Options (v1)")
    print("Current XP settings:")
    print(f"  xp_per_km    = {state.settings.get('xp_per_km')}")
    print(f"  xp_per_5min  = {state.settings.get('xp_per_5min')}")
    print(f"  level_base_xp = {state.settings.get('level_base_xp')}")
    print(f"  level_growth  = {state.settings.get('level_growth')}")
    print("\nChange a setting? (leave blank to skip)")
    try:
        new_per_km = input("xp_per_km: ").strip()
        if new_per_km:
            state.settings["xp_per_km"] = int(new_per_km)

        new_per_5 = input("xp_per_5min: ").strip()
        if new_per_5:
            state.settings["xp_per_5min"] = int(new_per_5)

        new_base = input("level_base_xp: ").strip()
        if new_base:
            state.settings["level_base_xp"] = int(new_base)

        new_growth = input("level_growth (e.g., 1.25): ").strip()
        if new_growth:
            state.settings["level_growth"] = float(new_growth)

        save_state(state)
        print("\nSettings updated.")
    except ValueError:
        print("Invalid value; settings unchanged.")
    pause()

# ---------- Main loop ----------

def main():
    state = load_state()

    while True:
        # Main screen arugs
        
        # Main Xp
        level, xp_into, xp_need = level_from_xp(state.total_xp, state.settings)
        # Xp bar
        bar = progress_bar(xp_into, xp_need)
        # Weekly progress
        today_str = datetime.now().strftime(DATE_FMT)
        today_week = week_id_from_datestr(today_str)
        count_week = runs_in_week(state, today_week)
        target = int(state.settings.get("weekly_runs_target", 3))
        got_bonus = "Yes" if today_week in state.weekly_bonus_awarded else "No"

        clear_screen()

        print_header("RunRPG")
        print(f"Level: {level}   {bar}  ({xp_into}/{xp_need} XP to next)")
        print(f"Total XP: {state.total_xp}   |   Runs logged: {len(state.runs)}")
        print(f"Week {today_week}: {count_week}/{target} runs  |  Bonus awarded: {got_bonus}")
        print("-" * 50)
        print("1) List all runs")
        print("2) Show last run")
        print("3) Add a run")
        print("4) Options")
        print("5) Save & Exit")
        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            action_list_runs(state)
        elif choice == "2":
            action_last_run(state)
        elif choice == "3":
            action_add_run(state)
        elif choice == "4":
            action_options(state)
        elif choice == "5":
            save_state(state)
            clear_screen()
            print("Game saved. See you next run!")
            break
        else:
            print("Invalid choice.")
            pause()

if __name__ == "__main__":
    main()