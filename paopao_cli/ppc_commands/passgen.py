import argparse
import random
import string
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

def generate_password(length=12, use_uppercase=True, use_numbers=True, use_symbols=True):
    charset = string.ascii_lowercase
    if use_uppercase:
        charset += string.ascii_uppercase
    if use_numbers:
        charset += string.digits
    if use_symbols:
        charset += "!@#$%^&*()-_=+[]{}|;:,.<>?/"

    if not charset:
        raise ValueError("Character set is empty. Enable at least one type of character.")

    return ''.join(random.choice(charset) for _ in range(length))

def get_strength(password):
    score = 0
    if any(c.islower() for c in password): score += 1
    if any(c.isupper() for c in password): score += 1
    if any(c.isdigit() for c in password): score += 1
    if any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for c in password): score += 1

    if len(password) >= 16: score += 1

    labels = ["😬 Weak", "😐 OK", "🙂 Decent", "😎 Strong", "🧠 Master"]
    colors = ["red", "orange1", "yellow3", "green", "bright_cyan"]
    return labels[score-1 if score > 0 else 0], colors[score-1 if score > 0 else 0]

def main(argv):
    parser = argparse.ArgumentParser(
        prog="passgen",
        description="🔐 Generate strong random passwords from your terminal.",
        epilog="Example: passgen --length 16 --symbols"
    )
    parser.add_argument("--length", type=int, default=12, help="Length of the password (default: 12)")
    parser.add_argument("--count", type=int, default=1, help="Number of passwords to generate (default: 1)")
    parser.add_argument("--no-uppercase", action="store_true", help="Exclude uppercase letters")
    parser.add_argument("--no-numbers", action="store_true", help="Exclude digits")
    parser.add_argument("--no-symbols", action="store_true", help="Exclude symbols")

    args = parser.parse_args(argv)

    for i in range(args.count):
        try:
            password = generate_password(
                length=args.length,
                use_uppercase=not args.no_uppercase,
                use_numbers=not args.no_numbers,
                use_symbols=not args.no_symbols
            )
            label, color = get_strength(password)
            table = Table.grid(expand=True)
            table.add_column(justify="center")
            table.add_row(f"[bold white]{password}[/bold white]")
            table.add_row(f"[{color}]{label}[/{color}]")
            console.print(Panel(table, title=f"🔐 Password #{i+1}", style="bold cyan", box=box.ROUNDED, expand=False))
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")

if __name__ == "__main__":
    main()
