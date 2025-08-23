import argparse
import secrets
import string
import sys
import pyperclip
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from rich.prompt import Confirm
from rich import box

console = Console()

class PasswordGenerator:
    def __init__(self):
        self.symbol_sets = {
            'basic': "!@#$%^&*",
            'extended': "!@#$%^&*()-_=+[]{}|;:,.<>?/",
            'safe': "!@#$%^&*-_"  # Symbols that work well in most contexts
        }
    
    def generate_password(self, length=12, use_uppercase=True, use_numbers=True, 
                         use_symbols=True, symbol_set='extended', exclude_ambiguous=False):
        """Generate a cryptographically secure password."""
        if length < 4:
            raise ValueError("Password length must be at least 4 characters")
        
        charset = string.ascii_lowercase
        required_chars = []
        
        # Build charset and ensure at least one character from each enabled type
        if use_uppercase:
            charset += string.ascii_uppercase
            required_chars.append(secrets.choice(string.ascii_uppercase))
        
        if use_numbers:
            digits = string.digits
            if exclude_ambiguous:
                digits = digits.replace('0', '').replace('1', '')
            charset += digits
            required_chars.append(secrets.choice(digits))
        
        if use_symbols:
            symbols = self.symbol_sets.get(symbol_set, self.symbol_sets['extended'])
            charset += symbols
            required_chars.append(secrets.choice(symbols))
        
        if exclude_ambiguous:
            # Remove commonly confused characters
            ambiguous_chars = "0O1lI"
            for char in ambiguous_chars:
                charset = charset.replace(char, '')
        
        if not charset:
            raise ValueError("Character set is empty. Enable at least one character type.")
        
        # Always include at least one lowercase letter
        if not required_chars or not any(c.islower() for c in required_chars):
            required_chars.append(secrets.choice(string.ascii_lowercase))
        
        # Generate remaining characters
        remaining_length = length - len(required_chars)
        if remaining_length < 0:
            raise ValueError(f"Password length {length} is too short for required character types")
        
        password_chars = required_chars + [secrets.choice(charset) for _ in range(remaining_length)]
        
        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password_chars)
        
        return ''.join(password_chars)
    
    def get_strength_score(self, password):
        """Calculate password strength score and return detailed analysis."""
        score = 0
        feedback = []
        
        # Character type checks
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for c in password)
        
        if has_lower:
            score += 1
        else:
            feedback.append("Add lowercase letters")
            
        if has_upper:
            score += 1
        else:
            feedback.append("Add uppercase letters")
            
        if has_digit:
            score += 1
        else:
            feedback.append("Add numbers")
            
        if has_symbol:
            score += 1
        else:
            feedback.append("Add symbols")
        
        # Length bonuses
        length = len(password)
        if length >= 12:
            score += 1
        if length >= 16:
            score += 1
        if length >= 20:
            score += 1
            
        # Additional security checks
        unique_chars = len(set(password))
        if unique_chars / length > 0.7:  # High character diversity
            score += 1
            
        return min(score, 7), feedback  # Cap at 7 for clean display
    
    def get_strength_label(self, password):
        """Get strength label and color for password."""
        score, feedback = self.get_strength_score(password)
        
        if score <= 2:
            return "💀 Very Weak", "bright_red", feedback
        elif score <= 3:
            return "😬 Weak", "red", feedback
        elif score <= 4:
            return "😐 Fair", "yellow", feedback
        elif score <= 5:
            return "🙂 Good", "green", feedback
        elif score <= 6:
            return "😎 Strong", "bright_green", feedback
        else:
            return "🛡️ Excellent", "bright_cyan", feedback

def display_password(password, index, total, copy_to_clipboard=False):
    """Display a password with strength analysis in a formatted panel."""
    generator = PasswordGenerator()
    label, color, feedback = generator.get_strength_label(password)
    
    table = Table.grid(expand=True)
    table.add_column(justify="center")
    
    # Password display
    table.add_row(f"[bold white on black] {password} [/bold white on black]")
    table.add_row("")  # Spacing
    
    # Strength indicator
    table.add_row(f"[{color}]●[/{color}] Strength: [{color}]{label}[/{color}]")
    
    # Password stats
    stats = f"Length: {len(password)} | Unique chars: {len(set(password))}"
    table.add_row(f"[dim]{stats}[/dim]")
    
    title = f"🔐 Password {index}/{total}" if total > 1 else "🔐 Generated Password"
    
    if copy_to_clipboard:
        title += " (Copied to clipboard)"
    
    console.print(Panel(
        table, 
        title=title, 
        style="bold cyan", 
        box=box.ROUNDED, 
        expand=False
    ))
    
    # Show improvement suggestions for weaker passwords
    if feedback and len(feedback) > 0:
        console.print(f"[dim]💡 Suggestions: {', '.join(feedback)}[/dim]\n")
    else:
        console.print("")  # Add spacing

def copy_to_clipboard(text):
    """Safely copy text to clipboard."""
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="passgen",
        description="🔐 Generate cryptographically secure passwords",
        epilog="Examples:\n"
               "  passgen --length 16 --count 3\n"
               "  passgen --no-symbols --exclude-ambiguous\n"
               "  passgen --symbols safe --clipboard",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Password options
    parser.add_argument("--length", "-l", type=int, default=16, 
                       help="Password length (default: 16, minimum: 4)")
    parser.add_argument("--count", "-c", type=int, default=1,
                       help="Number of passwords to generate (default: 1)")
    
    # Character type options
    parser.add_argument("--no-uppercase", action="store_true",
                       help="Exclude uppercase letters")
    parser.add_argument("--no-numbers", action="store_true",
                       help="Exclude numbers")
    parser.add_argument("--no-symbols", action="store_true",
                       help="Exclude symbols")
    
    # Advanced options
    parser.add_argument("--symbols", choices=['basic', 'extended', 'safe'], 
                       default='extended',
                       help="Symbol set to use (default: extended)")
    parser.add_argument("--exclude-ambiguous", action="store_true",
                       help="Exclude ambiguous characters (0, O, 1, l, I)")
    parser.add_argument("--clipboard", action="store_true",
                       help="Copy first password to clipboard")
    parser.add_argument("--batch", action="store_true",
                       help="Generate passwords without interactive prompts")
    
    args = parser.parse_args(argv)
    
    # Validate arguments
    if args.length < 4:
        console.print("[bold red]Error:[/bold red] Password length must be at least 4")
        sys.exit(1)
    
    if args.count < 1:
        console.print("[bold red]Error:[/bold red] Count must be at least 1")
        sys.exit(1)
    
    if args.count > 100:
        console.print("[bold red]Error:[/bold red] Maximum count is 100")
        sys.exit(1)
    
    # Initialize generator
    generator = PasswordGenerator()
    passwords = []
    
    try:
        # Generate passwords with progress bar for large batches
        password_range = track(range(args.count), description="Generating passwords...") if args.count > 5 else range(args.count)
        
        for i in password_range:
            password = generator.generate_password(
                length=args.length,
                use_uppercase=not args.no_uppercase,
                use_numbers=not args.no_numbers,
                use_symbols=not args.no_symbols,
                symbol_set=args.symbols,
                exclude_ambiguous=args.exclude_ambiguous
            )
            passwords.append(password)
        
        # Display results
        for i, password in enumerate(passwords, 1):
            copy_first = args.clipboard and i == 1
            if copy_first:
                copy_to_clipboard(password)
            
            display_password(password, i, len(passwords), copy_first)
        
        # Interactive clipboard option for single password
        if len(passwords) == 1 and not args.clipboard and not args.batch:
            if Confirm.ask("Copy to clipboard?"):
                if copy_to_clipboard(passwords[0]):
                    console.print("[green]✓[/green] Copied to clipboard!")
                else:
                    console.print("[yellow]⚠[/yellow] Could not copy to clipboard")
    
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Generation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
