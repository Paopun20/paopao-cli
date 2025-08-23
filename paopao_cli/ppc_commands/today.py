import argparse
import calendar
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.theme import Theme

# กำหนดธีมสี custom
custom_theme = Theme({
    "weekday": "bold cyan",
    "weekend": "bold magenta",
    "today": "bold white on red",
    "month_title": "bold white on dark_blue",
    "border": "bright_blue",
    "sunday": "bold red",
})

console = Console(theme=custom_theme)

def get_today_text(fmt="long"):
    now = datetime.now()
    if fmt == "iso":
        return now.isoformat()
    elif fmt == "short":
        return now.strftime("%d/%m/%Y")
    else:
        return now.strftime("📅 %A, %d %B %Y %H:%M:%S")

def highlight_today_in_line(line, year, month, weekday_positions):
    """ไฮไลท์วันปัจจุบันและวันเสาร์-อาทิตย์"""
    today = datetime.now()
    today_day = today.day if (today.year == year and today.month == month) else None

    line_text = Text()
    idx = 0
    day_pos = 0

    while idx < len(line):
        ch = line[idx]
        if ch == " ":
            line_text.append(" ")
            idx += 1
            continue

        num_str = ""
        while idx < len(line) and line[idx].isdigit():
            num_str += line[idx]
            idx += 1

        if num_str:
            day_num = int(num_str)
            weekday = weekday_positions[day_pos]

            if day_num == today_day:
                line_text.append(num_str, style="today")
            elif weekday == 5:  # Saturday
                line_text.append(num_str, style="weekend")
            elif weekday == 6:  # Sunday
                line_text.append(num_str, style="sunday")
            else:
                line_text.append(num_str, style="weekday")

            day_pos += 1
        else:
            if idx < len(line):
                line_text.append(line[idx])
                idx += 1
    return line_text

def format_month_lines(year, month):
    """สร้าง list ของ Text เป็นบล็อกปฏิทิน 20 ตัวอักษรกว้าง"""
    month_name = calendar.month_name[month]
    header = f"{month_name} {year}".center(20)
    week_header = "Mo Tu We Th Fr Sa Su"

    weeks = calendar.monthcalendar(year, month)

    lines = [header, week_header]
    for week in weeks:
        line = ""
        for day in week:
            if day == 0:
                line += "   "
            else:
                line += f"{day:2d} "
        lines.append(line.rstrip())

    while len(lines) < 8:
        lines.append(" " * 20)

    # ไฮไลท์วันปัจจุบันและวันเสาร์-อาทิตย์
    for i, week in enumerate(weeks, start=2):
        weekday_positions = [idx for idx, d in enumerate(week) if d != 0]
        lines[i] = highlight_today_in_line(lines[i], year, month, weekday_positions)

    # แปลงทุกบรรทัดเป็น Text
    for i in range(len(lines)):
        if not isinstance(lines[i], Text):
            lines[i] = Text(lines[i])

    # ตั้ง style สำหรับ header และ week header
    lines[0].stylize("month_title")
    lines[1].stylize("month_title")

    return lines

def create_quarter_with_boxes(year, start_month, color):
    """สร้าง Columns ของ 3 เดือนต่อ quarter"""
    def create_month_panel(year, month):
        lines = format_month_lines(year, month)
        panel_text = Text("\n").join(lines)
        return Panel(panel_text, title=calendar.month_name[month], expand=False, style=color)

    month_panels = []
    for m in range(start_month, start_month + 3):
        if m > 12:
            break
        panel = create_month_panel(year, m)
        month_panels.append(panel)

    return Columns(month_panels, expand=False, padding=(1, 2))

def show_full_year_calendar(year=None):
    year = year or datetime.now().year
    quarter_colors = ["bold blue", "bold green", "bold yellow", "bold magenta"]

    quarter_panels = []
    for start_month, color in zip([1, 4, 7, 10], quarter_colors):
        quarter_column = create_quarter_with_boxes(year, start_month, color)
        quarter_column.border_style = color
        quarter_panels.append(quarter_column)

    console.print(Columns(quarter_panels, equal=True))

def show_calendar(year=None, month=None):
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    lines = format_month_lines(year, month)
    panel_text = Text("\n").join(lines)
    title = f"{calendar.month_name[month]} {year}"
    console.print(Panel(panel_text, title=title, style="cyan", expand=False))

def show_weekday():
    today = datetime.now()
    console.print(f"🗓️ Today is: [bold yellow]{today.strftime('%A')}[/bold yellow]")

def main(argv):
    parser = argparse.ArgumentParser(
        prog="today",
        description="📅 View date/time, calendar, weekday, and more.",
    )
    parser.add_argument("--now", action="store_true", help="Show current date and time (default)")
    parser.add_argument("--calendar", action="store_true", help="Show calendar for specific month")
    parser.add_argument("--full-year", action="store_true", help="Show full year calendar")
    parser.add_argument("--weekday", action="store_true", help="Show today's weekday")
    parser.add_argument("--format", choices=["long", "short", "iso"], default="long", help="Date format for --now")
    parser.add_argument("--year", type=int, help="Year for --calendar or --full-year")
    parser.add_argument("--month", type=int, choices=range(1,13), help="Month for --calendar (1-12)")

    args = parser.parse_args(argv)
    shown = False

    if args.full_year:
        show_full_year_calendar(year=args.year)
        shown = True
    if args.calendar:
        show_calendar(year=args.year, month=args.month)
        shown = True
    if args.weekday:
        show_weekday()
        shown = True
    if args.now or not shown:
        console.print(get_today_text(fmt=args.format))

if __name__ == "__main__":
    main()
