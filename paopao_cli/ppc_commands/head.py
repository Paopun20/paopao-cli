# head plugin
#!/usr/bin/env python3
import sys
import argparse

def main(argv):
    parser = argparse.ArgumentParser(description="Python version of 'head'. Prints first N lines from stdin.")
    parser.add_argument("-n", type=int, default=10, help="Number of lines to print (default: 10)")
    args = parser.parse_args(argv)

    count = 0
    try:
        for line in sys.stdin:
            if count >= args.n:
                break
            sys.stdout.write(line)
            count += 1
    except (BrokenPipeError, OSError):
        # Pipe closed early (e.g., downstream closed), exit silently
        try:
            sys.exit(0)
        except SystemExit:
            pass

if __name__ == "__main__":
    main()
