#!/usr/bin/env python3

from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any
from datetime import timedelta, date as date_cls
from datetime import date as date_cls

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
    monthly_bonus_awarded: List[str] = None  # Monthly Bonus

    @staticmethod
    def default() -> "GameState":
        return GameState(
            # This initializes stuff
            runs=[],
            weekly_bonus_awarded=[],
            monthly_bonus_awarded=[],
            total_xp=0,
            settings={
                # GameState.default().settings.

                "xp_per_km": 10,# Xp Per KM
                "xp_per_5min": 1,# XP Per 5/min

                "level_base_xp": 100, # Xp required Per level
                "level_growth": 1.25, # Xp growth per Level

                "weekly_runs_target": 3, # runs needed in a week
                "weekly_bonus_xp": 100, # XP awarded when goal is met
                
                "monthly_runs_target": 12, # runs needed in a month
                "monthly_bonus_xp": 300, # XP awarded when goal is met

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

    defaults = GameState.default().settings
    saved = raw.get("settings", {})
    settings = {**defaults, **saved}  # defaults first, then saved overrides

    awarded = raw.get("weekly_bonus_awarded", [])
    awarded_m = raw.get("monthly_bonus_awarded", [])
    return GameState(
        runs=runs,
        total_xp=total_xp,
        settings=settings,
        weekly_bonus_awarded=awarded,
        monthly_bonus_awarded=awarded_m,
    )

# Saves all relevant info into a JSON file
def save_state(state: GameState, path: str = DATA_PATH) -> None:
    payload = {
        "runs": [asdict(r) for r in state.runs],
        "total_xp": state.total_xp,
        "settings": state.settings | {"last_save": datetime.now().isoformat(timespec="seconds")},
        "weekly_bonus_awarded": state.weekly_bonus_awarded,
        "monthly_bonus_awarded": state.monthly_bonus_awarded,
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

def pause(msg: str = "\nPress Enter to continue...\n"):
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

# pace in MM:SS
def format_pace(distance_km: float, duration_min: float) -> str:
    if distance_km <= 0 or duration_min <= 0:
        return "--:--/km"
    pace_min_per_km = duration_min / distance_km
    total_seconds = int(round(pace_min_per_km * 60))
    mm, ss = divmod(total_seconds, 60)
    return f"{mm:02d}:{ss:02d}/km"

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

def month_id_from_datestr(datestr: str) -> str:
    y, m, _ = datestr.split("-")
    return f"{int(y):04d}-{int(m):02d}"

# Runs in Week counter
def runs_in_week(state: GameState, week_id: str) -> int:
    return sum(1 for r in state.runs if week_id_from_datestr(r.date) == week_id)

# Runs in Month counter
def runs_in_month(state: GameState, month_id: str) -> int:
    return sum(1 for r in state.runs if month_id_from_datestr(r.date) == month_id)

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

# Selector parser
def parse_selection(s: str, max_index: int) -> list[int]:
    s = s.strip().replace(" ", "")
    if not s:
        return []
    out = set()
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                a, b = int(a), int(b)
            except ValueError:
                continue
            if a > b:
                a, b = b, a
            for i in range(a, b + 1):
                if 1 <= i <= max_index:
                    out.add(i)
        else:
            try:
                i = int(part)
            except ValueError:
                continue
            if 1 <= i <= max_index:
                out.add(i)
    return sorted(out)

# Recompute Function
def recompute_totals(state: GameState) -> None:
    # Base XP = sum of per-run awarded XP (as stored at entry time)
    base_xp = sum(r.xp_awarded for r in state.runs)

    # Rebuild weekly bonuses
    target = int(state.settings.get("weekly_runs_target", 3))
    bonus  = int(state.settings.get("weekly_bonus_xp", 100))
    # Count runs by week
    week_counts = {}
    for r in state.runs:
        wid = week_id_from_datestr(r.date)  # your Sun–Sat helper
        week_counts[wid] = week_counts.get(wid, 0) + 1
    awarded_weeks = [wid for wid, cnt in week_counts.items() if cnt >= target]
    bonuses_total = bonus * len(awarded_weeks)

    # Monthly
    m_target = int(state.settings.get("monthly_runs_target", 12))
    m_bonus  = int(state.settings.get("monthly_bonus_xp", 300))
    month_counts = {}
    for r in state.runs:
        mid = month_id_from_datestr(r.date)
        month_counts[mid] = month_counts.get(mid, 0) + 1
    months_awarded = [mid for mid, cnt in month_counts.items() if cnt >= m_target]
    monthly_total = m_bonus * len(months_awarded)

    state.weekly_bonus_awarded = sorted(awarded_weeks)
    state.monthly_bonus_awarded = sorted(months_awarded)
    state.total_xp = int(base_xp + weekly_total + monthly_total)



# ---------- Menu actions ----------

# This is a Test Line

# List Runs
def action_list_runs(state: GameState):
    clear_screen()
    print_header("All Runs")
    if not state.runs:
        print("No runs logged yet.")
        pause()
        return

    # Build rows first (so we can size columns dynamically)
    rows = []
    for r in state.runs:
        date_str = r.date
        dist_str = f"{r.distance_km:.2f}"
        dur_str  = format_duration(r.duration_min)
        pace_str = format_pace(r.distance_km, r.duration_min)
        xp_str   = f"+{r.xp_awarded}"
        note_str = r.notes or ""
        rows.append((date_str, dist_str, dur_str, pace_str, xp_str, note_str))

    # Column titles
    headers = ("Date", "Km", "Time", "Pace", "XP", "Notes")

    # Compute widths (min width = header length)
    w_date = max(len(headers[0]), max(len(r[0]) for r in rows))
    w_km   = max(len(headers[1]), max(len(r[1]) for r in rows))
    w_time = max(len(headers[2]), max(len(r[2]) for r in rows))
    w_pace = max(len(headers[3]), max(len(r[3]) for r in rows))
    w_xp   = max(len(headers[4]), max(len(r[4]) for r in rows))

    # Print header
    index_w = len(str(len(rows)))  # width for row numbers
    header_line = (
        f"{'#':>{index_w}}  "
        f"{headers[0]:<{w_date}} | "
        f"{headers[1]:>{w_km}} | "
        f"{headers[2]:>{w_time}} | "
        f"{headers[3]:>{w_pace}} | "
        f"{headers[4]:>{w_xp}}  "
        f"{headers[5]}"
    )
    print(header_line)
    print("-" * len(header_line))

    # Print rows
    for i, (date_str, dist_str, dur_str, pace_str, xp_str, note_str) in enumerate(rows, 1):
        line = (
            f"{i:>{index_w}}. "
            f"{date_str:<{w_date}} | "
            f"{dist_str:>{w_km}} | "
            f"{dur_str:>{w_time}} | "
            f"{pace_str:>{w_pace}} | "
            f"{xp_str:>{w_xp}}  "
            f"{note_str}"
        )
        print(line)

    # Totals line
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
        print(f"Pace:     {format_pace(r.distance_km, r.duration_min)}")
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

    # Week calc
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

    # Monthly calc
    month_id = month_id_from_datestr(date)
    m_target = int(state.settings.get("monthly_runs_target", 12))
    m_bonus  = int(state.settings.get("monthly_bonus_xp", 300))
    already_awarded_m = month_id in state.monthly_bonus_awarded
    count_month_now = runs_in_month(state, month_id)

    monthly_bonus_awarded_now = False
    if not already_awarded_m and count_month_now >= m_target:
        state.total_xp += m_bonus
        state.monthly_bonus_awarded.append(month_id)
        monthly_bonus_awarded_now = True
       
    save_state(state)

    after_level, xp_into, xp_need = level_from_xp(state.total_xp, state.settings)

    # existing prints
    if bonus_awarded_now:
        print(f"Weekly goal hit ({count_now}/{target}). Bonus +{bonus} XP!")

    if monthly_bonus_awarded_now:
        print(f" Monthly goal hit ({count_month_now}/{m_target}). Bonus +{m_bonus} XP!")

    print(f"\nRun saved. Gained +{xp} XP! Total XP: {state.total_xp}\n")
    if after_level > before_level:
        print(f"LEVEL UP! You reached Level {after_level}.")
        print(f"XP {progress_bar(xp_into, xp_need)}")
    else:
        print(f"Progress to next level: {xp_into}/{xp_need} XP {progress_bar(xp_into, xp_need)}")
    pause()

# Options
def action_options(state: GameState):
    clear_screen()
    print_header("Options")

    print("Current XP settings:")
    print(f"  xp_per_km           = {state.settings.get('xp_per_km')}")
    print(f"  xp_per_5min         = {state.settings.get('xp_per_5min')}")
    print(f"  level_base_xp       = {state.settings.get('level_base_xp')}")
    print(f"  level_growth        = {state.settings.get('level_growth')}")
    print(f"  weekly_runs_target  = {state.settings.get('weekly_runs_target')}")
    print(f"  weekly_bonus_xp     = {state.settings.get('weekly_bonus_xp')}")
    print(f"  monthly_runs_target = {state.settings.get('monthly_runs_target')}")
    print(f"  monthly_bonus_xp    = {state.settings.get('monthly_bonus_xp')}")
    print("\nChoose:")
    print("  1) Change XP settings")
    print("  2) Change level curve")
    print("  3) Change weekly bonus settings")
    print("  D) Delete runs")
    print("  Q) Back")

    choice = input("\nOption: ").strip().lower()

    if choice == "1":
        try:
            new_per_km = input("xp_per_km (blank=skip): ").strip()
            if new_per_km:
                state.settings["xp_per_km"] = int(new_per_km)
            new_per_5 = input("xp_per_5min (blank=skip): ").strip()
            if new_per_5:
                state.settings["xp_per_5min"] = int(new_per_5)
            save_state(state)
            print("\nSettings updated.")
        except ValueError:
            print("Invalid value; settings unchanged.")
        pause()
        return

    if choice == "2":
        try:
            new_base = input("level_base_xp (blank=skip): ").strip()
            if new_base:
                state.settings["level_base_xp"] = int(new_base)
            new_growth = input("level_growth (e.g., 1.25) (blank=skip): ").strip()
            if new_growth:
                state.settings["level_growth"] = float(new_growth)
            save_state(state)
            print("\nLevel curve updated.")
        except ValueError:
            print("Invalid value; level settings unchanged.")
        pause()
        return

    if choice == "3":
        try:
            new_target = input("weekly_runs_target (blank=skip): ").strip()
            if new_target:
                state.settings["weekly_runs_target"] = int(new_target)
            new_bonus = input("weekly_bonus_xp (blank=skip): ").strip()
            if new_bonus:
                state.settings["weekly_bonus_xp"] = int(new_bonus)
            # Recompute totals because weekly settings changed
            recompute_totals(state)
            save_state(state)
            print("\nWeekly bonus settings updated and totals recomputed.")
        except ValueError:
            print("Invalid value; weekly settings unchanged.")
        pause()
        return

    if choice == "4":
        try:
            new_m_target = input("monthly_runs_target (blank=skip): ").strip()
            if new_m_target:
                state.settings["monthly_runs_target"] = int(new_m_target)

            new_m_bonus = input("monthly_bonus_xp (blank=skip): ").strip()
            if new_m_bonus:
                state.settings["monthly_bonus_xp"] = int(new_m_bonus)
            # Recompute totals because Monthly settings changed
            recompute_totals(state)
            save_state(state)
            print("\nMonthly bonus settings updated and totals recomputed.")
        except ValueError:
            print("Invalid value; monthly settings unchanged.")
        pause()
        return

    if choice == "d":
        import shutil
        # Backup
        backup_path = DATA_PATH + ".bak"
        shutil.copyfile(DATA_PATH, backup_path)

        # Show runs with 1-based indices
        clear_screen()
        print_header("Delete Runs")
        if not state.runs:
            print("No runs to delete.")
            pause()
            return
        
        for i, r in enumerate(state.runs, 1):
            print(f"{i:3d}. {r.date} | {r.distance_km:.2f} km | "
                  f"{format_duration(r.duration_min)} | +{r.xp_awarded} XP"
                  + (f" | {r.notes}" if r.notes else ""))
        
        print("\nType run numbers to delete (e.g., 2 or 2,5,7-9). Leave blank to cancel.")
        sel = input("Delete which: ").strip()
        picks = parse_selection(sel, len(state.runs))
        if not picks:
            print("No selection; nothing deleted.")
            pause()
            return

        # Confirm
        print(f"You selected {len(picks)} run(s): {picks}")
        confirm = input("Type 'y' to confirm delete: ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            pause()
            return

        # Delete from highest index to lowest to avoid reindexing issues
        for idx in sorted(picks, reverse=True):
            del state.runs[idx - 1]

        # Recompute totals & bonuses to keep consistent
        recompute_totals(state)
        save_state(state)
        print(f"Deleted {len(picks)} run(s). Totals recomputed. New Total XP: {state.total_xp}")
        pause()
        return

    # default: back


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
        this_month = month_id_from_datestr(today_str)
        cm = runs_in_month(state, this_month)
        target = int(state.settings.get("weekly_runs_target", 3))
        mt = int(state.settings.get("monthly_runs_target", 12))
        got_bonus = "Yes" if today_week in state.weekly_bonus_awarded else "No"
        got_m = "Yes" if this_month in state.monthly_bonus_awarded else "No"

        clear_screen()

        print_header("RunRPG")
        print(f"Level: {level}   {bar}  ({xp_into}/{xp_need} XP to next)")
        print(f"Total XP: {state.total_xp}   |   Runs logged: {len(state.runs)}")
        print(f"Week {today_week}: {count_week}/{target} runs  |  Bonus awarded: {got_bonus}")
        print(f"Month {this_month}: {cm}/{mt} runs  |  Monthly bonus awarded: {got_m}")
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