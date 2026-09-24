# Workday Planner & Break Calculator

A powerful command-line tool to optimize your workday schedule with intelligent break placement, commute time calculation, and legal compliance validation. Perfect for professionals who need to balance work, breaks, commute times, and medical appointments.

**Optimized for:** Android PyDroid3 and desktop command-line execution

## Features

- 📅 **Multiple Day Profiles**: Support for normal workdays (taxi/train), doctor appointments (morning/evening), and custom schedules
- ⏰ **Intelligent Break Placement**: Automatically calculates optimal break times with preference for full-hour boundaries
- 🚗 **Commute Management**: Tracks walking, taxi, and train travel times with realistic schedules
- 🚆 **Smart Train Dispatch**: Finds the best train departure to meet arrival targets
- ⚖️ **Legal Compliance**: Validates work hours, break requirements, and mandatory rest periods
- 📊 **Comprehensive Statistics**: Detailed reports on work time, commute duration, and rest periods
- ⚠️ **Warnings & Recommendations**: Identifies violations and suggests schedule optimizations

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/workday-planner.git
cd workday-planner

# No external dependencies required - uses only Python stdlib
python3 workday_planner.py --help
```

## Quick Start

```bash
# Plan a normal taxi-based workday
python3 workday_planner.py -d normal_taxi

# Plan a train-based commute with custom times
python3 workday_planner.py -d normal_train -s 07:30 -f 17:00

# Plan a day with a morning doctor appointment
python3 workday_planner.py -d doctor_morning -D 09:00 -F 09:30

# Check compliance for a Friday (with Saturday as next day)
python3 workday_planner.py -c Friday -N Saturday -w saturday
```

## Usage

```bash
python3 workday_planner.py [OPTIONS]

Options:
  -d, --day-type {normal_taxi,normal_train,doctor_morning,doctor_evening,custom}
                        Day profile (default: normal_taxi)
  -s, --start1 HH:MM    Work start time
  -f, --finish2 HH:MM   Work finish time
  -D, --doctor-start HH:MM     Doctor appointment start
  -F, --doctor-finish HH:MM    Doctor appointment end
  -c, --current-day TEXT        Current day name (default: Monday)
  -N, --next-day TEXT           Next working day (default: Tuesday)
  -n, --next-day-start HH:MM   Next day start time (default: 07:10)
  -r, --required-rest HH:MM    Required rest duration (default: 10:00)
  -w, --weekday-type {weekday,saturday}  Day category (default: weekday)
```

## Core Functions

### Time Utilities

- **`parse_hm(time_str: str) -> int`**
  - Converts time string (HH:MM format) to total minutes from midnight
  - Example: "14:30" → 870 minutes

- **`format_hm(total_minutes: int) -> str`**
  - Converts minutes since midnight back to HH:MM format
  - Example: 870 → "14:30"

- **`format_duration(total_minutes: int) -> str`**
  - Formats duration without day wrapping (for displaying work durations)
  - Example: 630 → "10:30" (10 hours 30 minutes)

- **`to_decimal_hours(minutes: int) -> float`**
  - Converts minutes to decimal hours for reporting
  - Example: 630 → 10.5

### Schedule Generation

- **`generate_schedule(args: argparse.Namespace) -> Dict`**
  - Main schedule generator that creates a complete timeline based on the selected day profile
  - Returns dictionary with timeline, statistics, and commute breakdowns
  - Supports 5 profiles: normal_taxi, normal_train, doctor_morning, doctor_evening, custom

- **`place_break(work_start_min: int, work_end_min: int) -> Tuple[int, int, int]`**
  - Intelligently places breaks near the middle of the workday
  - Prefers full-hour boundaries for break start/end times
  - Ensures first work block is between 2-6 hours
  - Returns: (break_start, break_end, break_duration)

- **`calculate_required_break(pure_work_target_minutes: int) -> int`**
  - Determines legally required break duration
  - 45 minutes for workdays ≥ 9 hours
  - 30 minutes for shorter workdays

### Train Scheduling

- **`find_next_train(arrival_min: int, timetable: List[str]) -> Tuple[int, int]`**
  - Finds the next available train after arrival time
  - Returns: (departure_time, waiting_duration)
  - Used for flexible train scheduling

- **`find_train_for_arrival(target_arrival_at_work: int) -> Tuple[int, int, int]`**
  - Finds the optimal train to arrive at work by target time
  - Selects the latest train that still meets the deadline
  - Returns: (train_departure, train_arrival, actual_work_start)

### Validation & Reporting

- **`generate_warnings(data: Dict, weekday_type: str, free_time_min: int, req_rest_min: int) -> List[str]`**
  - Validates schedule against legal requirements:
    - Earliest work start: 06:00
    - Latest finish (weekday): 18:30
    - Latest finish (Saturday): 14:30
    - Maximum pure work per day: 10 hours
    - Doctor day limit: 8 hours (work + doctor)
    - Minimum rest between shifts: 10 hours

- **`generate_recommendations(pure_work_min: int) -> List[str]`**
  - Provides optimization suggestions based on work duration
  - Highlights efficiency thresholds (e.g., break duration changes at 9:00)

- **`calculate_free_time(current_day: str, finish_time_min: int, next_day: str, next_start_min: int) -> int`**
  - Calculates rest duration between shifts
  - Handles multi-day gaps correctly
  - Returns total rest in minutes

- **`print_report(data: Dict, args: argparse.Namespace) -> None`**
  - Generates comprehensive formatted report with:
    - Timeline visualization
    - Work, break, and commute statistics
    - Rest period validation
    - Warnings and recommendations

## Example Output

```
==================================================
       WORKDAY PLANNER & BREAK CALCULATOR
==================================================
Profile: normal_train
--------------------------------------------------
SCHEDULE TIMELINE:
  06:25 - 06:35  Preparation
  06:35 - 06:45  Walk to station A
  06:45 - 06:55  Waiting at station A
  06:55 - 07:25  Train A -> E (RB20)
  07:25 - 07:50  Walk E -> Work
  07:50 - 12:00  Work (Block 1)
  12:00 - 12:45  Lunch Break (45 min)
  12:45 - 17:30  Work (Block 2)
  17:30 - 18:05  Walk Work -> E
  18:05 - 18:31  Waiting at station E
  18:31 - 19:01  Train E -> A (RB20)
  19:01 - 19:11  Walk station A -> Home
==================================================
STATISTICS
==================================================

Work Statistics:
  Presence:         09:40
  Break:            00:45
  Pure Work:        08:55
  Decimal Hours:    8.92 h

Commute Statistics:
  Train Waiting:    00:36
  Train Ride:       01:00
  Walk Time:        02:00
  Total Commute:    03:36

...rest of report...
```

## Configuration Constants

The tool uses realistic travel times and schedules:

- **Taxi routes**: Coordinated pickup (06:50-07:10) and dropoff (15:40-16:00)
- **Train schedule (RB20)**: Early morning departures (05:07-08:07) and evening returns (16:01-19:01)
- **Walking times**: 
  - Home to meeting point: 10 min
  - Train station to work: 25 min
  - Work back to station: 35 min
- **Minimum breaks**: 30 min (short) / 45 min (long, if work > 9 hours)

## Legal Compliance

This tool enforces realistic working hour regulations:

| Rule | Value |
|------|-------|
| Earliest work start | 06:00 |
| Latest finish (weekday) | 18:30 |
| Latest finish (Saturday) | 14:30 |
| Maximum pure work per day | 10:00 |
| Minimum rest between shifts | 10:00 |
| Doctor day work + appointment limit | 08:00 |
| Break threshold | 09:00 of pure work |

## Use Cases

- **Shift Workers**: Plan multiple shifts and validate rest periods
- **Flexible Schedules**: Experiment with different work times and commute methods
- **Medical Appointments**: Incorporate doctor visits while maintaining legal work limits
- **Commute Optimization**: Compare taxi vs. train routes and travel times
- **Compliance Auditing**: Check if schedules meet legal requirements

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Areas for enhancement:

- Additional transportation modes (car, bike)
- Customizable location-based commute times
- Export to calendar formats (ICS)
- GUI interface
- Multi-day schedule planning

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
