#!/usr/bin/env python3
"""
Enhanced Calendar and Date Tool
A comprehensive tool for displaying dates, calendars, and time information with rich formatting.
"""

import argparse
import calendar
import locale
import sys
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from zoneinfo import ZoneInfo
import re

from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.theme import Theme
from rich.table import Table
from rich.align import Align
from rich.layout import Layout

# Enhanced custom theme with more colors and styles
CUSTOM_THEME = Theme({
    "weekday": "bold cyan",
    "weekend": "bold magenta",  
    "today": "bold white on red",
    "month_title": "bold white on dark_blue",
    "border": "bright_blue",
    "sunday": "bold red",
    "saturday": "bold magenta",
    "holiday": "bold yellow on dark_red",
    "past_day": "dim white",
    "future_day": "white",
    "week_number": "dim blue",
    "season_spring": "bold green",
    "season_summer": "bold yellow", 
    "season_autumn": "bold orange1",
    "season_winter": "bold cyan",
    "moon_phase": "bold yellow",
    "time_info": "bold bright_blue",
})

console = Console(theme=CUSTOM_THEME)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration and Data Classes  
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DateInfo:
    """Comprehensive date information."""
    date: datetime
    day_of_year: int
    week_of_year: int
    days_until_new_year: int
    season: str
    zodiac_sign: str
    weekday_name: str
    month_name: str
    is_weekend: bool
    is_leap_year: bool

@dataclass
class Holiday:
    """Holiday information."""
    name: str
    date: date
    type: str  # "fixed", "floating", "lunar"

class HolidayCalculator:
    """Calculate various holidays and special dates."""
    
    @staticmethod
    def get_easter_date(year: int) -> date:
        """Calculate Easter date using the algorithm."""
        # Anonymous Gregorian algorithm
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        return date(year, month, day)
    
    @staticmethod
    def get_us_holidays(year: int) -> List[Holiday]:
        """Get US federal holidays for a given year."""
        holidays = []
        
        # Fixed date holidays
        holidays.append(Holiday("New Year's Day", date(year, 1, 1), "fixed"))
        holidays.append(Holiday("Independence Day", date(year, 7, 4), "fixed"))
        holidays.append(Holiday("Veterans Day", date(year, 11, 11), "fixed"))
        holidays.append(Holiday("Christmas Day", date(year, 12, 25), "fixed"))
        
        # Floating holidays
        # Martin Luther King Jr. Day (3rd Monday in January)
        jan_1 = date(year, 1, 1)
        days_to_monday = (7 - jan_1.weekday()) % 7
        first_monday = jan_1 + timedelta(days=days_to_monday)
        mlk_day = first_monday + timedelta(weeks=2)
        holidays.append(Holiday("Martin Luther King Jr. Day", mlk_day, "floating"))
        
        # Presidents Day (3rd Monday in February)
        feb_1 = date(year, 2, 1)
        days_to_monday = (7 - feb_1.weekday()) % 7
        first_monday = feb_1 + timedelta(days=days_to_monday)
        presidents_day = first_monday + timedelta(weeks=2)
        holidays.append(Holiday("Presidents Day", presidents_day, "floating"))
        
        # Memorial Day (last Monday in May)
        may_31 = date(year, 5, 31)
        days_to_last_monday = may_31.weekday()
        memorial_day = may_31 - timedelta(days=days_to_last_monday)
        holidays.append(Holiday("Memorial Day", memorial_day, "floating"))
        
        # Labor Day (1st Monday in September)
        sep_1 = date(year, 9, 1)
        days_to_monday = (7 - sep_1.weekday()) % 7
        labor_day = sep_1 + timedelta(days=days_to_monday)
        holidays.append(Holiday("Labor Day", labor_day, "floating"))
        
        # Columbus Day (2nd Monday in October)
        oct_1 = date(year, 10, 1)
        days_to_monday = (7 - oct_1.weekday()) % 7
        first_monday = oct_1 + timedelta(days=days_to_monday)
        columbus_day = first_monday + timedelta(weeks=1)
        holidays.append(Holiday("Columbus Day", columbus_day, "floating"))
        
        # Thanksgiving (4th Thursday in November)
        nov_1 = date(year, 11, 1)
        days_to_thursday = (3 - nov_1.weekday()) % 7
        first_thursday = nov_1 + timedelta(days=days_to_thursday)
        thanksgiving = first_thursday + timedelta(weeks=3)
        holidays.append(Holiday("Thanksgiving Day", thanksgiving, "floating"))
        
        # Easter-based holidays
        easter = HolidayCalculator.get_easter_date(year)
        holidays.append(Holiday("Easter Sunday", easter, "lunar"))
        holidays.append(Holiday("Good Friday", easter - timedelta(days=2), "lunar"))
        
        return holidays

def get_season(date_obj: datetime) -> str:
    """Determine the season for a given date."""
    month = date_obj.month
    day = date_obj.day
    
    if month == 12 and day >= 21 or month in [1, 2] or month == 3 and day < 20:
        return "winter"
    elif month == 3 and day >= 20 or month in [4, 5] or month == 6 and day < 21:
        return "spring"
    elif month == 6 and day >= 21 or month in [7, 8] or month == 9 and day < 23:
        return "summer"
    else:
        return "autumn"

def get_zodiac_sign(date_obj: datetime) -> str:
    """Get zodiac sign for a given date."""
    month = date_obj.month
    day = date_obj.day
    
    zodiac_dates = [
        (1, 20, "Capricorn"), (2, 19, "Aquarius"), (3, 21, "Pisces"),
        (4, 20, "Aries"), (5, 21, "Taurus"), (6, 21, "Gemini"),
        (7, 23, "Cancer"), (8, 23, "Leo"), (9, 23, "Virgo"),
        (10, 23, "Libra"), (11, 22, "Scorpio"), (12, 22, "Sagittarius")
    ]
    
    for i, (m, d, sign) in enumerate(zodiac_dates):
        if month < m or (month == m and day <= d):
            return sign
    return "Capricorn"

def get_moon_phase(date_obj: datetime) -> str:
    """Approximate moon phase calculation."""
    # This is a simplified calculation
    days_since_new = (date_obj - datetime(2000, 1, 6)).days % 29.53
    
    if days_since_new < 1:
        return "🌑 New Moon"
    elif days_since_new < 7:
        return "🌒 Waxing Crescent"
    elif days_since_new < 8:
        return "🌓 First Quarter"
    elif days_since_new < 15:
        return "🌔 Waxing Gibbous"
    elif days_since_new < 16:
        return "🌕 Full Moon"
    elif days_since_new < 22:
        return "🌖 Waning Gibbous"
    elif days_since_new < 23:
        return "🌗 Last Quarter"
    else:
        return "🌘 Waning Crescent"

# ─────────────────────────────────────────────────────────────────────────────
# Date and Time Formatting Functions
# ─────────────────────────────────────────────────────────────────────────────

def get_comprehensive_date_info(dt: Optional[datetime] = None, timezone: Optional[str] = None) -> DateInfo:
    """Get comprehensive information about a date."""
    if dt is None:
        dt = datetime.now()
    
    if timezone:
        try:
            tz = ZoneInfo(timezone)
            dt = dt.replace(tzinfo=tz)
        except Exception:
            console.print(f"[yellow]Warning: Invalid timezone '{timezone}', using local time[/]")
    
    year_start = datetime(dt.year, 1, 1)
    year_end = datetime(dt.year + 1, 1, 1)
    
    return DateInfo(
        date=dt,
        day_of_year=dt.timetuple().tm_yday,
        week_of_year=dt.isocalendar()[1],
        days_until_new_year=(year_end - dt).days,
        season=get_season(dt),
        zodiac_sign=get_zodiac_sign(dt),
        weekday_name=dt.strftime("%A"),
        month_name=dt.strftime("%B"),
        is_weekend=dt.weekday() >= 5,
        is_leap_year=calendar.isleap(dt.year)
    )

def format_date_output(fmt: str = "long", dt: Optional[datetime] = None, timezone: Optional[str] = None) -> str:
    """Format date output in various formats."""
    if dt is None:
        dt = datetime.now()
    
    if timezone:
        try:
            tz = ZoneInfo(timezone)
            dt = dt.replace(tzinfo=tz)
        except Exception:
            pass
    
    if fmt == "iso":
        return dt.isoformat()
    elif fmt == "short":
        return dt.strftime("%d/%m/%Y")
    elif fmt == "us":
        return dt.strftime("%m/%d/%Y")
    elif fmt == "european":
        return dt.strftime("%d.%m.%Y")
    elif fmt == "timestamp":
        return str(int(dt.timestamp()))
    elif fmt == "relative":
        now = datetime.now()
        diff = dt - now
        if abs(diff.days) == 0:
            return "Today"
        elif diff.days == 1:
            return "Tomorrow"
        elif diff.days == -1:
            return "Yesterday"
        elif diff.days > 0:
            return f"In {diff.days} days"
        else:
            return f"{abs(diff.days)} days ago"
    else:  # long format
        return dt.strftime("📅 %A, %d %B %Y %H:%M:%S")

def show_detailed_date_info(dt: Optional[datetime] = None, timezone: Optional[str] = None):
    """Show comprehensive date information in a nice table."""
    info = get_comprehensive_date_info(dt, timezone)
    
    table = Table(title="📅 Date Information", show_header=False, box=None)
    table.add_column("Label", style="bold cyan", width=20)
    table.add_column("Value", style="green")
    
    # Basic date info
    table.add_row("Date", info.date.strftime("%A, %B %d, %Y"))
    table.add_row("Time", info.date.strftime("%H:%M:%S"))
    if info.date.tzinfo:
        table.add_row("Timezone", str(info.date.tzinfo))
    
    # Calendar info
    table.add_row("Day of Year", f"{info.day_of_year}/365" + (" (leap)" if info.is_leap_year else ""))
    table.add_row("Week of Year", str(info.week_of_year))
    table.add_row("Days to New Year", str(info.days_until_new_year))
    
    # Seasonal and astronomical info
    season_style = f"season_{info.season}"
    table.add_row("Season", Text(info.season.title(), style=season_style))
    table.add_row("Zodiac Sign", f"♈ {info.zodiac_sign}")
    table.add_row("Moon Phase", get_moon_phase(info.date))
    
    # Weekend indicator
    weekend_text = "Yes 🎉" if info.is_weekend else "No 💼"
    table.add_row("Weekend", weekend_text)
    
    console.print(table)

# ─────────────────────────────────────────────────────────────────────────────
# Calendar Display Functions
# ─────────────────────────────────────────────────────────────────────────────

def highlight_calendar_day(day_num: int, weekday: int, year: int, month: int, 
                          holidays: Dict[date, Holiday]) -> Text:
    """Apply appropriate styling to a calendar day."""
    today = datetime.now()
    today_date = today.date() if today.year == year and today.month == month else None
    current_date = date(year, month, day_num)
    
    # Create base text
    day_text = Text(f"{day_num:2d}")
    
    # Apply styling based on various conditions
    if day_num == (today_date.day if today_date else -1):
        day_text.stylize("today")
    elif current_date in holidays:
        day_text.stylize("holiday")
    elif weekday == 5:  # Saturday
        day_text.stylize("saturday")
    elif weekday == 6:  # Sunday
        day_text.stylize("sunday")
    elif current_date < today.date():
        day_text.stylize("past_day")
    else:
        day_text.stylize("weekday")
    
    return day_text

def create_enhanced_month_calendar(year: int, month: int, show_week_numbers: bool = False,
                                 show_holidays: bool = True) -> Text:
    """Create an enhanced month calendar with various features."""
    month_name = calendar.month_name[month]
    
    # Get holidays for the year
    holidays = {}
    if show_holidays:
        holiday_list = HolidayCalculator.get_us_holidays(year)
        holidays = {h.date: h for h in holiday_list if h.date.month == month}
    
    # Create header
    header = Text(f"{month_name} {year}".center(20 if not show_week_numbers else 23), style="month_title")
    
    # Week header
    week_header = "Mo Tu We Th Fr Sa Su"
    if show_week_numbers:
        week_header = "Wk " + week_header
    week_header_text = Text(week_header, style="month_title")
    
    # Get calendar data
    weeks = calendar.monthcalendar(year, month)
    calendar_lines = [header, week_header_text]
    
    for week_index, week in enumerate(weeks):
        line_parts = []
        
        # Add week number if requested
        if show_week_numbers:
            week_num = date(year, month, max(d for d in week if d > 0)).isocalendar()[1]
            line_parts.append(Text(f"{week_num:2d} ", style="week_number"))
        
        # Add days
        for day_index, day in enumerate(week):
            if day == 0:
                line_parts.append(Text("   "))
            else:
                day_text = highlight_calendar_day(day, day_index, year, month, holidays)
                line_parts.append(day_text)
                line_parts.append(Text(" "))
        
        # Combine line parts
        line = Text()
        for part in line_parts:
            line.append_text(part)
        calendar_lines.append(line)
    
    # Add holiday information at the bottom
    if holidays:
        calendar_lines.append(Text())
        calendar_lines.append(Text("Holidays:", style="bold yellow"))
        for holiday in sorted(holidays.values(), key=lambda h: h.date.day):
            holiday_text = Text(f"  {holiday.date.day}: {holiday.name}", style="holiday")
            calendar_lines.append(holiday_text)
    
    # Combine all lines
    result = Text()
    for i, line in enumerate(calendar_lines):
        if i > 0:
            result.append("\n")
        result.append_text(line)
    
    return result

def show_calendar(year: Optional[int] = None, month: Optional[int] = None, 
                 show_week_numbers: bool = False, show_holidays: bool = True):
    """Display a single month calendar."""
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    
    calendar_text = create_enhanced_month_calendar(year, month, show_week_numbers, show_holidays)
    title = f"{calendar.month_name[month]} {year}"
    
    console.print(Panel(calendar_text, title=title, style="cyan", expand=False))

def show_full_year_calendar(year: Optional[int] = None, show_week_numbers: bool = False):
    """Display a full year calendar with quarters."""
    year = year or datetime.now().year
    quarter_colors = ["bold blue", "bold green", "bold yellow", "bold magenta"]
    quarter_names = ["Q1 (Winter/Spring)", "Q2 (Spring/Summer)", 
                    "Q3 (Summer/Autumn)", "Q4 (Autumn/Winter)"]
    
    # Create title
    console.print(Panel(
        Text(f"Calendar for {year}", justify="center", style="bold white on dark_blue"),
        style="bright_blue"
    ))
    
    quarter_columns = []
    
    for quarter, (start_month, color, q_name) in enumerate(zip([1, 4, 7, 10], quarter_colors, quarter_names)):
        month_panels = []
        
        for m in range(start_month, start_month + 3):
            if m > 12:
                break
            
            calendar_text = create_enhanced_month_calendar(year, m, show_week_numbers, show_holidays=False)
            panel = Panel(
                calendar_text, 
                title=calendar.month_name[m], 
                style=color,
                expand=False
            )
            month_panels.append(panel)
        
        quarter_column = Columns(month_panels, expand=False, padding=(0, 1))
        quarter_panel = Panel(
            quarter_column,
            title=q_name,
            style=color,
            expand=True
        )
        quarter_columns.append(quarter_panel)
    
    # Display quarters in 2x2 grid
    top_row = Columns([quarter_columns[0], quarter_columns[1]], expand=True)
    bottom_row = Columns([quarter_columns[2], quarter_columns[3]], expand=True)
    
    console.print(top_row)
    console.print(bottom_row)

def show_weekday_info():
    """Show detailed weekday information."""
    today = datetime.now()
    
    table = Table(title="📅 Weekday Information", show_header=False, box=None)
    table.add_column("Attribute", style="bold cyan", width=15)
    table.add_column("Value", style="green")
    
    table.add_row("Today is", f"[bold yellow]{today.strftime('%A')}[/bold yellow]")
    table.add_row("Weekday Number", f"{today.weekday() + 1} (Monday = 1)")
    table.add_row("ISO Weekday", f"{today.isoweekday()} (Monday = 1)")
    table.add_row("Weekend?", "Yes 🎉" if today.weekday() >= 5 else "No 💼")
    
    # Show next few days
    table.add_row("", "")
    table.add_row("Next 7 Days", "")
    for i in range(1, 8):
        future_date = today + timedelta(days=i)
        day_name = future_date.strftime("%A")
        is_weekend = " 🎉" if future_date.weekday() >= 5 else ""
        table.add_row(f"  +{i} day{'s' if i > 1 else ''}", f"{day_name}{is_weekend}")
    
    console.print(table)

def show_time_zones():
    """Show current time in various time zones."""
    now = datetime.now()
    
    timezones = [
        ("Local", None),
        ("UTC", "UTC"),
        ("New York", "America/New_York"),
        ("Los Angeles", "America/Los_Angeles"),
        ("London", "Europe/London"),
        ("Paris", "Europe/Paris"),
        ("Tokyo", "Asia/Tokyo"),
        ("Sydney", "Australia/Sydney"),
        ("Bangkok", "Asia/Bangkok"),
        ("Dubai", "Asia/Dubai"),
    ]
    
    table = Table(title="🌍 World Clock", show_header=True, header_style="bold magenta")
    table.add_column("Location", style="cyan", width=12)
    table.add_column("Time", style="green", width=20)
    table.add_column("Date", style="yellow", width=15)
    
    for location, tz_name in timezones:
        try:
            if tz_name:
                tz = ZoneInfo(tz_name)
                local_time = now.astimezone(tz)
            else:
                local_time = now
            
            time_str = local_time.strftime("%H:%M:%S")
            date_str = local_time.strftime("%Y-%m-%d")
            
            table.add_row(location, time_str, date_str)
        except Exception as e:
            table.add_row(location, "Error", str(e))
    
    console.print(table)

# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────

def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="enhanced_calendar",
        description="📅 Enhanced calendar and date tool with rich formatting and features.",
        epilog="""Examples:
  %(prog)s                           # Show current date and time
  %(prog)s --now --format iso        # Show current time in ISO format
  %(prog)s --calendar                # Show current month calendar
  %(prog)s --calendar --year 2024 --month 12  # Show specific month
  %(prog)s --full-year               # Show full year calendar
  %(prog)s --weekday                 # Show weekday information
  %(prog)s --world-clock             # Show world clock
  %(prog)s --detailed                # Show detailed date information
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Display options
    parser.add_argument("--now", action="store_true", 
                       help="Show current date and time (default if no other options)")
    parser.add_argument("--calendar", action="store_true", 
                       help="Show calendar for specific month")
    parser.add_argument("--full-year", action="store_true", 
                       help="Show full year calendar")
    parser.add_argument("--weekday", action="store_true", 
                       help="Show detailed weekday information")
    parser.add_argument("--world-clock", action="store_true", 
                       help="Show world clock with multiple timezones")
    parser.add_argument("--detailed", action="store_true", 
                       help="Show detailed date information")
    
    # Format options
    parser.add_argument("--format", 
                       choices=["long", "short", "us", "european", "iso", "timestamp", "relative"], 
                       default="long",
                       help="Date format for --now output")
    
    # Date selection
    parser.add_argument("--year", type=int, 
                       help="Year for --calendar or --full-year")
    parser.add_argument("--month", type=int, choices=range(1, 13), 
                       help="Month for --calendar (1-12)")
    parser.add_argument("--date", type=str, 
                       help="Specific date in YYYY-MM-DD format")
    
    # Display options
    parser.add_argument("--week-numbers", action="store_true", 
                       help="Show week numbers in calendar")
    parser.add_argument("--no-holidays", action="store_true", 
                       help="Don't highlight holidays in calendar")
    parser.add_argument("--timezone", type=str, 
                       help="Timezone for date/time display (e.g., 'America/New_York')")
    
    # Utility options
    parser.add_argument("--list-timezones", action="store_true", 
                       help="List available timezones")
    
    return parser

def parse_date_string(date_str: str) -> Optional[datetime]:
    """Parse various date string formats."""
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d", 
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None

def list_timezones():
    """List some common timezones."""
    common_timezones = [
        "UTC",
        "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
        "America/Toronto", "America/Vancouver", "America/Mexico_City",
        "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Rome", "Europe/Madrid",
        "Asia/Tokyo", "Asia/Shanghai", "Asia/Seoul", "Asia/Bangkok", "Asia/Dubai",
        "Asia/Kolkata", "Asia/Singapore", "Asia/Hong_Kong",
        "Australia/Sydney", "Australia/Melbourne", "Australia/Perth",
        "Pacific/Auckland", "Pacific/Honolulu",
        "Africa/Cairo", "Africa/Johannesburg",
    ]
    
    table = Table(title="Common Timezones", show_header=False)
    table.add_column("Timezone", style="cyan")
    
    for tz in sorted(common_timezones):
        table.add_row(tz)
    
    console.print(table)

def main(argv=None):
    """Main application entry point."""
    if argv is None:
        argv = sys.argv[1:]
    
    parser = setup_argument_parser()
    args = parser.parse_args(argv)
    
    # Handle timezone listing
    if args.list_timezones:
        list_timezones()
        return
    
    # Parse specific date if provided
    target_date = None
    if args.date:
        target_date = parse_date_string(args.date)
        if target_date is None:
            console.print(f"[red]Error: Could not parse date '{args.date}'[/]")
            console.print("[yellow]Supported formats: YYYY-MM-DD, YYYY/MM/DD, DD/MM/YYYY, MM/DD/YYYY[/]")
            sys.exit(1)
    
    # Determine what to show
    show_something = False
    
    if args.full_year:
        show_full_year_calendar(year=args.year, show_week_numbers=args.week_numbers)
        show_something = True
    
    if args.calendar:
        show_calendar(
            year=args.year, 
            month=args.month, 
            show_week_numbers=args.week_numbers,
            show_holidays=not args.no_holidays
        )
        show_something = True
    
    if args.weekday:
        show_weekday_info()
        show_something = True
    
    if args.world_clock:
        show_time_zones()
        show_something = True
    
    if args.detailed:
        show_detailed_date_info(target_date, args.timezone)
        show_something = True
    
    if args.now or not show_something:
        date_output = format_date_output(args.format, target_date, args.timezone)
        console.print(date_output)

if __name__ == "__main__":
    main()
