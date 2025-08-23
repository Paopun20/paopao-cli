import argparse
import sys
import signal
import time
import multiprocessing
import os


class SafeStdout:
    """
    Safe stdout wrapper: never crashes if the pipe is closed.
    """
    def __init__(self):
        self.closed = False

    def write(self, text):
        if self.closed:
            return False
        try:
            sys.stdout.write(text)
            sys.stdout.flush()
            return True
        except (BrokenPipeError, OSError):
            self.closed = True
            return False


def is_powershell():
    """
    Detect if running inside PowerShell.
    """
    return (
        'pwsh' in os.environ.get('SHELL', '').lower()
        or 'powershell' in os.environ.get('PROMPT', '').lower()
        or 'PSModulePath' in os.environ
    )


def yes_worker(text, count, delay, quiet):
    safe_stdout = SafeStdout()
    output = text + "\n"

    try:
        i = 0
        while i < count:
            if not quiet:
                if not safe_stdout.write(output):
                    break
            i += 1
            if delay > 0:
                time.sleep(delay)
    except KeyboardInterrupt:
        pass


def main(argv):
    parser = argparse.ArgumentParser(
        description="Custom yes command in Python (prints a string repeatedly)."
    )
    parser.add_argument("text", nargs="?", default="y",
                        help="The string to print repeatedly. Defaults to 'y'.")
    parser.add_argument("-c", "--count", type=int,
                        help="Print only this many times (per process).")
    parser.add_argument("-d", "--delay", type=float, default=0,
                        help="Delay between prints (in seconds).")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Do not print, just simulate.")
    parser.add_argument("--debug-time", action="store_true",
                        help="Print total execution time at the end.")
    parser.add_argument("--workers", type=int, default=1,
                        help="Number of parallel processes to run.")

    args = parser.parse_args(argv)
    text = args.text or "y"
    count = args.count if args.count else float("inf")

    # Avoid SIGPIPE errors on Unix
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    # Warn PowerShell + pipe + multiprocessing user
    if is_powershell() and not sys.stdout.isatty() and args.workers > 1:
        print(
            "[WARNING] PowerShell with multiprocessing and pipe may cause 'pipe is being closed'.",
            file=sys.stderr
        )

    start_time = time.perf_counter()

    if args.workers == 1:
        yes_worker(text, count, args.delay, args.quiet)
    else:
        processes = []
        for _ in range(args.workers):
            p = multiprocessing.Process(
                target=yes_worker,
                args=(text, count, args.delay, args.quiet)
            )
            p.start()
            print(f"[INFO] Process {p.pid} started.", file=sys.stderr)
            processes.append(p)

        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            for p in processes:
                print(f"[INFO] Process {p.pid} terminated.", file=sys.stderr)
                p.terminate()

    if args.debug_time:
        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"\n[DEBUG] Time elapsed: {duration:.6f} seconds", file=sys.stderr)


if __name__ == "__main__":
    multiprocessing.freeze_support()  # Needed for Windows
    try:
        main()
    except (BrokenPipeError, OSError, ValueError):
        # Exit quietly if pipe is closed
        try:
            sys.exit(0)
        except SystemExit:
            pass
