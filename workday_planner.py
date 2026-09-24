#!/usr/bin/env python3
"""
Workday Planner & Break Calculator
Optimized for Android PyDroid3 and desktop command-line execution.
"""

import argparse
import sys
from typing import Dict, List, Optional, Tuple

# ==========================================
# CONSTANTS & BUSINESS RULES
# ==========================================

EARLIEST_WORK_START = "06:00"
LATEST_WORK_FINISH_WEEKDAY = "18:30"
LATEST_WORK_FINISH_SATURDAY = "14:30"

MIN_BREAK_SHORT = 30
MIN_BREAK_LONG = 45

LONG_BREAK_THRESHOLD_MINUTES = 9 * 60  # 540 min
MAX_PURE_WORK_MINUTES = 10 * 60        # 600 min
MAX_DOCTOR_DAY_COMBINED_MINUTES = 8 * 60  # 480 min

MIN_LEGAL_REST = "10:00"

PREPARATION_MINUTES_TAXI = 30
PREPARATION_MINUTES_TRAIN = 30

WALK_HOME_TO_MEETING_POINT_MINUTES = 10
TAXI_WAITING_MINUTES = 10
TAXI_RIDE_1_MINUTES = 20
TAXI_RIDE_2_MINUTES = 20
WALK_MEETING_POINT_TO_HOME_MINUTES = 10

TAXI_START_1 = "06:50"
TAXI_FINISH_1 = "07:10"
TAXI_START_2 = "15:40"
TAXI_FINISH_2 = "16:00"

WALK_HOME_TO_A_MINUTES = 10
WALK_E_TO_WORK_MINUTES = 25
WALK_WORK_TO_E_MINUTES = 35
WALK_A_TO_HOME_MINUTES = 10
DOCTOR_TO_A_MINUTES = 30

RB20_TRAVEL_MINUTES = 30

# RB20 timetable (extended early mornings to accommodate early arrivals)
RB20_TO_WORK = [
    "05:07",
    "05:37",
    "06:07",
    "06:37",
    "07:07",
    "07:37",
    "08:07",
]

RB20_TO_HOME = [
    "16:01",
    "16:31",
    "17:01",
    "17:31",
    "18:01",
    "18:31",
    "19:01",
]

DAYS_OF_WEEK = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

# ==========================================
# TIME HELPER FUNCTIONS
# ==========================================

def parse_hm(time_str: str) -> int:
    """Convert HH:MM to total minutes from midnight."""
    h, m = map(int, time_str.strip().split(":"))
    return h * 60 + m


def format_hm(total_minutes: int) -> str:
    """Format total minutes from midnight to HH:MM."""
    total_minutes = int(round(total_minutes))
    h = (total_minutes // 60) % 24
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}"


def format_duration(total_minutes: int) -> str:
    """Format duration in minutes to HH:MM (without modulo 24)."""
    total_minutes = int(round(total_minutes))
    h = total_minutes // 60
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}"


def to_decimal_hours(minutes: int) -> float:
    """Convert minutes to decimal hours."""
    return round(minutes / 60.0, 2)


# ==========================================
# TRAIN DISPATCH LOGIC
# ==========================================

def find_next_train(arrival_min: int, timetable: List[str]) -> Tuple[int, int]:
    """Find next departure and waiting time. Returns (departure_min, wait_min)."""
    for departure_str in timetable:
        dep_min = parse_hm(departure_str)
        if dep_min >= arrival_min:
            return dep_min, dep_min - arrival_min
    last_train = parse_hm(timetable[-1])
    return last_train, max(0, last_train - arrival_min)


def find_train_for_arrival(target_arrival_at_work: int) -> Tuple[int, int, int]:
    """
    Finds the best train departure to reach work by target_arrival_at_work.
    Returns: (train_dep_min, train_arr_min, actual_work_start_min)
    """
    latest_arr_at_e = target_arrival_at_work - WALK_E_TO_WORK_MINUTES
    latest_dep_from_a = latest_arr_at_e - RB20_TRAVEL_MINUTES

    # Filter trains that depart at or before the deadline
    suitable = [parse_hm(t) for t in RB20_TO_WORK if parse_hm(t) <= latest_dep_from_a]
    if suitable:
        best_dep = suitable[-1]  # Latest train that still arrives on time
        best_arr = best_dep + RB20_TRAVEL_MINUTES
        return best_dep, best_arr, target_arrival_at_work
    else:
        # If earlier than any schedule, use the earliest known train
        first_dep = parse_hm(RB20_TO_WORK[0])
        first_arr = first_dep + RB20_TRAVEL_MINUTES
        earliest_work_start = first_arr + WALK_E_TO_WORK_MINUTES
        return first_dep, first_arr, max(target_arrival_at_work, earliest_work_start)


# ==========================================
# BREAK PLACEMENT ALGORITHM
# ==========================================

def calculate_required_break(pure_work_target_minutes: int) -> int:
    """Determine legally required break duration based on work duration."""
    if pure_work_target_minutes >= LONG_BREAK_THRESHOLD_MINUTES:
        return MIN_BREAK_LONG
    return MIN_BREAK_SHORT


def place_break(work_start_min: int, work_end_min: int) -> Tuple[int, int, int]:
    """
    Places break near the middle, preferring full-hour boundaries
    while keeping the first block between 2h and 6h.
    Returns (break_start_min, break_end_min, break_duration).
    """
    presence = work_end_min - work_start_min
    break_dur = MIN_BREAK_LONG if (presence - MIN_BREAK_LONG) >= LONG_BREAK_THRESHOLD_MINUTES else MIN_BREAK_SHORT
    pure_work = presence - break_dur
    break_dur = calculate_required_break(pure_work)

    midpoint = work_start_min + presence // 2

    candidates = []
    floor_hour = (midpoint // 60) * 60
    ceil_hour = floor_hour + 60

    # Start on full hour
    for cand_start in [floor_hour, ceil_hour]:
        cand_end = cand_start + break_dur
        candidates.append((cand_start, cand_end))

    # End on full hour
    for cand_end in [floor_hour, ceil_hour]:
        cand_start = cand_end - break_dur
        candidates.append((cand_start, cand_end))

    # Middle candidate
    middle_start = midpoint - (break_dur // 2)
    candidates.append((middle_start, middle_start + break_dur))

    best_break = None
    lowest_penalty = float("inf")
    min_block = 2 * 60
    max_block = 6 * 60

    for b_start, b_end in candidates:
        first_block = b_start - work_start_min
        second_block = work_end_min - b_end

        if first_block < min_block or second_block <= 0:
            continue
        if first_block > max_block:
            continue

        distance_from_mid = abs(b_start - (midpoint - break_dur // 2))
        hour_bonus = 0
        if b_start % 60 == 0:
            hour_bonus -= 15
        if b_end % 60 == 0:
            hour_bonus -= 15

        penalty = distance_from_mid + hour_bonus
        if penalty < lowest_penalty:
            lowest_penalty = penalty
            best_break = (b_start, b_end)

    if best_break is None:
        fallback_start = max(work_start_min + min_block, midpoint - (break_dur // 2))
        best_break = (fallback_start, fallback_start + break_dur)

    return best_break[0], best_break[1], break_dur


# ==========================================
# SCHEDULE GENERATOR
# ==========================================

def generate_schedule(args: argparse.Namespace) -> Dict:
    profile = args.day_type
    timeline: List[Tuple[str, str, str]] = []

    walk_commute_min = 0
    taxi_commute_min = 0
    train_waiting_min = 0
    train_ride_min = 0
    doctor_minutes = 0

    if profile == "normal_taxi":
        t_taxi1_s = parse_hm(TAXI_START_1)
        t_wait_s = t_taxi1_s - TAXI_WAITING_MINUTES
        t_walk1_s = t_wait_s - WALK_HOME_TO_MEETING_POINT_MINUTES
        t_prep_s = t_walk1_s - PREPARATION_MINUTES_TAXI

        timeline.append((format_hm(t_prep_s), format_hm(t_walk1_s), "Preparation"))
        timeline.append((format_hm(t_walk1_s), format_hm(t_wait_s), "Walk to meeting point"))
        timeline.append((format_hm(t_wait_s), format_hm(t_taxi1_s), "Waiting"))
        timeline.append((TAXI_START_1, TAXI_FINISH_1, "Taxi ride"))

        work_start = parse_hm(args.start1 if args.start1 else TAXI_FINISH_1)
        work_end = parse_hm(args.finish2 if args.finish2 else TAXI_START_2)

        b_start, b_end, b_dur = place_break(work_start, work_end)
        timeline.append((format_hm(work_start), format_hm(b_start), "Work (Block 1)"))
        timeline.append((format_hm(b_start), format_hm(b_end), f"Lunch Break ({b_dur} min)"))
        timeline.append((format_hm(b_end), format_hm(work_end), "Work (Block 2)"))

        taxi_end2 = work_end + TAXI_RIDE_2_MINUTES
        home_arrival = taxi_end2 + WALK_MEETING_POINT_TO_HOME_MINUTES
        timeline.append((format_hm(work_end), format_hm(taxi_end2), "Taxi ride"))
        timeline.append((format_hm(taxi_end2), format_hm(home_arrival), "Walk home"))

        leave_home = t_walk1_s
        arrive_home = home_arrival
        walk_commute_min = WALK_HOME_TO_MEETING_POINT_MINUTES + WALK_MEETING_POINT_TO_HOME_MINUTES
        taxi_commute_min = (parse_hm(TAXI_FINISH_1) - t_taxi1_s) + TAXI_RIDE_2_MINUTES

    elif profile == "normal_train":
        if args.start1:
            target_start = parse_hm(args.start1)
            train_dep, train_arr, work_start = find_train_for_arrival(target_start)
        else:
            train_dep = parse_hm(RB20_TO_WORK[2])  # 06:07
            train_arr = train_dep + RB20_TRAVEL_MINUTES
            work_start = train_arr + WALK_E_TO_WORK_MINUTES

        station_a_arr = train_dep - 10
        walk_start = station_a_arr - WALK_HOME_TO_A_MINUTES
        prep_start = walk_start - PREPARATION_MINUTES_TRAIN

        timeline.append((format_hm(prep_start), format_hm(walk_start), "Preparation"))
        timeline.append((format_hm(walk_start), format_hm(station_a_arr), "Walk to station A"))
        timeline.append((format_hm(station_a_arr), format_hm(train_dep), "Waiting at station A"))
        timeline.append((format_hm(train_dep), format_hm(train_arr), "Train A -> E (RB20)"))
        
        walk_to_work_end = train_arr + WALK_E_TO_WORK_MINUTES
        timeline.append((format_hm(train_arr), format_hm(walk_to_work_end), "Walk E -> Work"))

        if work_start > walk_to_work_end:
            timeline.append((format_hm(walk_to_work_end), format_hm(work_start), "Buffer / Pre-shift waiting"))

        work_end = parse_hm(args.finish2 if args.finish2 else "16:00")
        b_start, b_end, b_dur = place_break(work_start, work_end)
        timeline.append((format_hm(work_start), format_hm(b_start), "Work (Block 1)"))
        timeline.append((format_hm(b_start), format_hm(b_end), f"Lunch Break ({b_dur} min)"))
        timeline.append((format_hm(b_end), format_hm(work_end), "Work (Block 2)"))

        station_e_arr = work_end + WALK_WORK_TO_E_MINUTES
        timeline.append((format_hm(work_end), format_hm(station_e_arr), "Walk Work -> E"))
        dep_home, wait_home = find_next_train(station_e_arr, RB20_TO_HOME)
        if wait_home > 0:
            timeline.append((format_hm(station_e_arr), format_hm(dep_home), "Waiting at station E"))
        train_home_arr = dep_home + RB20_TRAVEL_MINUTES
        timeline.append((format_hm(dep_home), format_hm(train_home_arr), "Train E -> A (RB20)"))
        arrive_home = train_home_arr + WALK_A_TO_HOME_MINUTES
        timeline.append((format_hm(train_home_arr), format_hm(arrive_home), "Walk station A -> Home"))

        leave_home = walk_start
        walk_commute_min = WALK_HOME_TO_A_MINUTES + WALK_E_TO_WORK_MINUTES + WALK_WORK_TO_E_MINUTES + WALK_A_TO_HOME_MINUTES
        train_ride_min = RB20_TRAVEL_MINUTES * 2
        train_waiting_min = 10 + wait_home

    elif profile == "doctor_morning":
        doc_start = parse_hm(args.doctor_start if args.doctor_start else "09:00")
        doc_end = parse_hm(args.doctor_finish if args.doctor_finish else "09:30")
        doctor_minutes = doc_end - doc_start

        timeline.append((format_hm(doc_start), format_hm(doc_end), "Doctor appointment"))
        station_a_arr = doc_end + DOCTOR_TO_A_MINUTES
        timeline.append((format_hm(doc_end), format_hm(station_a_arr), "Travel to station A"))

        dep_work, wait_work = find_next_train(station_a_arr, RB20_TO_WORK)
        if wait_work > 0:
            timeline.append((format_hm(station_a_arr), format_hm(dep_work), "Waiting at station A"))
        arr_e = dep_work + RB20_TRAVEL_MINUTES
        timeline.append((format_hm(dep_work), format_hm(arr_e), "Train A -> E (RB20)"))
        
        calculated_work_start = arr_e + WALK_E_TO_WORK_MINUTES
        work_start = parse_hm(args.start1) if args.start1 else calculated_work_start
        timeline.append((format_hm(arr_e), format_hm(work_start), "Walk E -> Work"))

        work_end = parse_hm(args.finish2 if args.finish2 else "17:30")
        b_start, b_end, b_dur = place_break(work_start, work_end)
        timeline.append((format_hm(work_start), format_hm(b_start), "Work (Block 1)"))
        timeline.append((format_hm(b_start), format_hm(b_end), f"Lunch Break ({b_dur} min)"))
        timeline.append((format_hm(b_end), format_hm(work_end), "Work (Block 2)"))

        station_e_arr = work_end + WALK_WORK_TO_E_MINUTES
        timeline.append((format_hm(work_end), format_hm(station_e_arr), "Walk Work -> E"))
        dep_home, wait_home = find_next_train(station_e_arr, RB20_TO_HOME)
        if wait_home > 0:
            timeline.append((format_hm(station_e_arr), format_hm(dep_home), "Waiting at station E"))
        train_home_arr = dep_home + RB20_TRAVEL_MINUTES
        timeline.append((format_hm(dep_home), format_hm(train_home_arr), "Train E -> A (RB20)"))
        arrive_home = train_home_arr + WALK_A_TO_HOME_MINUTES
        timeline.append((format_hm(train_home_arr), format_hm(arrive_home), "Walk station A -> Home"))

        leave_home = doc_start
        walk_commute_min = DOCTOR_TO_A_MINUTES + WALK_E_TO_WORK_MINUTES + WALK_WORK_TO_E_MINUTES + WALK_A_TO_HOME_MINUTES
        train_ride_min = RB20_TRAVEL_MINUTES * 2
        train_waiting_min = wait_work + wait_home

    elif profile == "doctor_evening":
        work_start = parse_hm(args.start1 if args.start1 else "07:10")
        work_end = parse_hm(args.finish2 if args.finish2 else "15:00")
        b_start, b_end, b_dur = place_break(work_start, work_end)

        timeline.append((format_hm(work_start), format_hm(b_start), "Work (Block 1)"))
        timeline.append((format_hm(b_start), format_hm(b_end), f"Lunch Break ({b_dur} min)"))
        timeline.append((format_hm(b_end), format_hm(work_end), "Work (Block 2)"))

        doc_start = parse_hm(args.doctor_start if args.doctor_start else "16:00")
        doc_end = parse_hm(args.doctor_finish if args.doctor_finish else "16:30")
        doctor_minutes = doc_end - doc_start
        timeline.append((format_hm(doc_start), format_hm(doc_end), "Doctor appointment"))

        leave_home = work_start - 30
        arrive_home = doc_end + 30
        walk_commute_min = 60

    else:  # custom
        work_start = parse_hm(args.start1 if args.start1 else "07:10")
        work_end = parse_hm(args.finish2 if args.finish2 else "15:40")
        b_start, b_end, b_dur = place_break(work_start, work_end)

        timeline.append((format_hm(work_start), format_hm(b_start), "Work (Block 1)"))
        timeline.append((format_hm(b_start), format_hm(b_end), f"Lunch Break ({b_dur} min)"))
        timeline.append((format_hm(b_end), format_hm(work_end), "Work (Block 2)"))

        leave_home = work_start - 30
        arrive_home = work_end + 30
        walk_commute_min = 60

    presence_min = work_end - work_start
    pure_work_min = presence_min - b_dur
    away_from_home_min = arrive_home - leave_home
    total_commute_min = walk_commute_min + taxi_commute_min + train_waiting_min + train_ride_min

    return {
        "profile": profile,
        "timeline": timeline,
        "work_start": work_start,
        "work_end": work_end,
        "presence_min": presence_min,
        "break_min": b_dur,
        "pure_work_min": pure_work_min,
        "doctor_min": doctor_minutes,
        "leave_home": leave_home,
        "arrive_home": arrive_home,
        "away_from_home_min": away_from_home_min,
        "commute": {
            "walk": walk_commute_min,
            "taxi": taxi_commute_min,
            "train_waiting": train_waiting_min,
            "train_ride": train_ride_min,
            "total": total_commute_min,
        },
    }


# ==========================================
# REST TIME CALCULATION
# ==========================================

def calculate_free_time(current_day: str, finish_time_min: int, next_day: str, next_start_min: int) -> int:
    """Calculates rest duration in minutes between shifts across multiple days."""
    try:
        curr_idx = DAYS_OF_WEEK.index(current_day.capitalize())
        next_idx = DAYS_OF_WEEK.index(next_day.capitalize())
    except ValueError:
        curr_idx, next_idx = 0, 1

    days_diff = (next_idx - curr_idx) % 7
    if days_diff == 0 and next_start_min <= finish_time_min:
        days_diff = 7

    total_rest_minutes = (days_diff * 24 * 60) + (next_start_min - finish_time_min)
    return total_rest_minutes


# ==========================================
# AUDIT & RECOMMENDATIONS
# ==========================================

def generate_warnings(data: Dict, weekday_type: str, free_time_min: int, req_rest_min: int) -> List[str]:
    warnings = []
    w_start = data["work_start"]
    w_end = data["work_end"]
    pure_work = data["pure_work_min"]
    doc_time = data["doctor_min"]

    if w_start < parse_hm(EARLIEST_WORK_START):
        warnings.append(f"Work starts too early ({format_hm(w_start)} < {EARLIEST_WORK_START})")

    if weekday_type.lower() == "saturday":
        if w_end > parse_hm(LATEST_WORK_FINISH_SATURDAY):
            warnings.append(f"Saturday finish violation ({format_hm(w_end)} > {LATEST_WORK_FINISH_SATURDAY})")
    else:
        if w_end > parse_hm(LATEST_WORK_FINISH_WEEKDAY):
            warnings.append(f"Work finishes too late ({format_hm(w_end)} > {LATEST_WORK_FINISH_WEEKDAY})")

    if pure_work > MAX_PURE_WORK_MINUTES:
        warnings.append(f"More than 10h pure work ({format_duration(pure_work)} > 10:00) - ILLEGAL")

    if doc_time > 0 and (pure_work + doc_time) > MAX_DOCTOR_DAY_COMBINED_MINUTES:
        warnings.append(
            f"Doctor day limit exceeded: pure work ({format_duration(pure_work)}) + "
            f"doctor ({format_duration(doc_time)}) > 08:00"
        )

    if free_time_min < req_rest_min:
        warnings.append(
            f"Legal rest violation: free time ({format_duration(free_time_min)}) "
            f"< required rest ({format_duration(req_rest_min)})"
        )

    return warnings


def generate_recommendations(pure_work_min: int) -> List[str]:
    recs = []
    if 535 <= pure_work_min < 540:
        recs.append(
            "Working up to 08:59 requires only a 30-minute break. "
            "Staying just below 09:00 optimizes your workday efficiency."
        )
    elif 540 <= pure_work_min <= 555:
        recs.append(
            "At 09:00 pure work the required break changes from 30 minutes to 45 minutes. Additional gain: +{pure_work_min - 539} minutes work. Additional cost: +15 minutes break"
            "  Recommendation: Not beneficial unless necessary."
        )
    return recs


# ==========================================
# REPORT FORMATTER
# ==========================================

def print_report(data: Dict, args: argparse.Namespace) -> None:
    req_rest_min = parse_hm(args.required_rest)
    next_start_min = parse_hm(args.next_day_start)
    free_time_min = calculate_free_time(args.current_day, data["work_end"], args.next_day, next_start_min)

    print("=" * 50)
    print("       WORKDAY PLANNER & BREAK CALCULATOR")
    print("=" * 50)
    print(f"Profile: {data['profile']}")
    print("-" * 50)
    print("SCHEDULE TIMELINE:")
    for start, finish, task in data["timeline"]:
        print(f"  {start} - {finish}  {task}")

    print("" + "=" * 50)
    print("STATISTICS")
    print("=" * 50)

    print("Work Statistics:")
    print(f"  Presence:         {format_duration(data['presence_min'])}")
    print(f"  Break:            {format_duration(data['break_min'])}")
    print(f"  Pure Work:        {format_duration(data['pure_work_min'])}")
    print(f"  Decimal Hours:    {to_decimal_hours(data['pure_work_min'])} h")
    if data["doctor_min"] > 0:
        print(f"  Doctor Time:      {format_duration(data['doctor_min'])}")
        combined = data["pure_work_min"] + data["doctor_min"]
        status = "PASS" if combined <= MAX_DOCTOR_DAY_COMBINED_MINUTES else "FAIL"
        print(f"  Combined Time:    {format_duration(combined)} [{status}]")

    print("Commute Statistics:")
    if data["commute"]["taxi"] > 0:
        print(f"  Taxi Commute:     {format_duration(data['commute']['taxi'])}")
    if data["commute"]["train_waiting"] > 0:
        print(f"  Train Waiting:    {format_duration(data['commute']['train_waiting'])}")
    if data["commute"]["train_ride"] > 0:
        print(f"  Train Ride:       {format_duration(data['commute']['train_ride'])}")
    print(f"  Walk Time:        {format_duration(data['commute']['walk'])}")
    print(f"  Total Commute:    {format_duration(data['commute']['total'])}")

    print("Home Statistics:")
    print(f"  Leave Home:       {format_hm(data['leave_home'])}")
    print(f"  Arrive Home:      {format_hm(data['arrive_home'])}")
    print(f"  Away From Home:   {format_duration(data['away_from_home_min'])}")

    print("Rest Statistics:")
    print(f"  Current Day:      {args.current_day} ({format_hm(data['work_end'])})")
    print(f"  Next Day:         {args.next_day} ({format_hm(next_start_min)})")
    print(f"  Free Time:        {format_duration(free_time_min)}")
    print(f"  Required Rest:    {format_duration(req_rest_min)}")
    rest_status = "OK" if free_time_min >= req_rest_min else "VIOLATION"
    print(f"  Status:           {rest_status}")

    warnings = generate_warnings(data, args.weekday_type, free_time_min, req_rest_min)
    if warnings:
        print("" + "!" * 50)
        print("WARNINGS:")
        for w in warnings:
            print(f"  [!] {w}")
        print("!" * 50)

    recommendations = generate_recommendations(data["pure_work_min"])
    if recommendations:
        print("" + "*" * 50)
        print("RECOMMENDATIONS:")
        for r in recommendations:
            print(f"  {r}")
        print("*" * 50)


# ==========================================
# CLI ENTRY POINT
# ==========================================

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Workday Planner & Break Calculator")
    parser.add_argument(
        "-d", "--day-type",
        choices=["normal_taxi", "normal_train", "doctor_morning", "doctor_evening", "custom"],
        default="normal_taxi",
        help="Day profile to plan"
    )
    parser.add_argument("-s", "--start1", type=str, default=None, help="Work start time (HH:MM)")
    parser.add_argument("-f", "--finish2", type=str, default=None, help="Work finish time (HH:MM)")
    parser.add_argument("-D", "--doctor-start", type=str, default=None, help="Doctor start time (HH:MM)")
    parser.add_argument("-F", "--doctor-finish", type=str, default=None, help="Doctor finish time (HH:MM)")
    parser.add_argument("-c", "--current-day", type=str, default="Monday", help="Current day name (e.g. Friday)")
    parser.add_argument("-N", "--next-day", type=str, default="Tuesday", help="Next working day (e.g. Monday)")
    parser.add_argument("-n", "--next-day-start", type=str, default="07:10", help="Next day start time (HH:MM)")
    parser.add_argument("-r", "--required-rest", type=str, default=MIN_LEGAL_REST, help="Required rest (HH:MM)")
    parser.add_argument("-w", "--weekday-type", type=str, default="weekday", choices=["weekday", "saturday"], help="Day category")

    return parser.parse_args()


def main():
    args = parse_arguments()
    schedule_data = generate_schedule(args)
    print_report(schedule_data, args)


if __name__ == "__main__":
    main()
