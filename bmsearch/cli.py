"""Command-line interface for searching literal patterns in text and files."""
import argparse
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence, TextIO, Tuple

from .algorithms import ALGORITHMS, BoyerMoore, SearchResult


def _search_lines(
    lines: Iterable[str],
    search: Callable[[str], SearchResult],
    source: Optional[str],
    output: TextIO,
) -> int:
    count = 0
    for line_number, line in enumerate(lines, start=1):
        content = line.rstrip("\r\n")
        for position in search(content).matches:
            location = f"{source}:" if source else ""
            print(f"{location}{line_number}:{position + 1}: {content}", file=output)
            count += 1
    return count


def _search_file(path: Path, search: Callable[[str], SearchResult], output: TextIO) -> Tuple[int, Optional[str]]:
    try:
        with path.open(encoding="utf-8-sig") as file:
            return _search_lines(file, search, str(path), output), None
    except (OSError, UnicodeError) as error:
        return 0, f"{path}: {error}"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bmsearch",
        description="Find literal patterns in text or UTF-8 files using Boyer-Moore.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    find_parser = subparsers.add_parser("find", help="search text or files for a pattern")
    find_parser.add_argument("pattern", help="literal text to find")
    find_parser.add_argument("files", nargs="*", help="UTF-8 files to search (reads standard input if omitted)")
    find_parser.add_argument("--text", help="search this text directly instead of reading files or standard input")
    find_parser.add_argument(
        "--algorithm",
        choices=sorted(ALGORITHMS),
        default="BM-galil",
        help="search algorithm to use (default: BM-galil)",
    )

    args = parser.parse_args(argv)
    if not args.pattern:
        parser.error("pattern must not be empty")
    if args.text is not None and args.files:
        parser.error("use either --text or file paths, not both")

    if args.algorithm == "BM-galil":
        matcher = BoyerMoore(args.pattern, extended=True, galil=True)
        search = matcher.search
    else:
        algorithm = ALGORITHMS[args.algorithm]
        search = lambda text: algorithm(text, args.pattern)

    total = 0
    errors = []
    if args.text is not None:
        total += _search_lines(args.text.splitlines(), search, None, sys.stdout)
    elif args.files:
        for filename in args.files:
            path = Path(filename)
            if path.is_dir():
                errors.append(f"{path}: is a directory; provide file paths instead")
                continue
            count, error = _search_file(path, search, sys.stdout)
            total += count
            if error:
                errors.append(error)
    else:
        total += _search_lines(sys.stdin, search, None, sys.stdout)

    for error in errors:
        print(error, file=sys.stderr)
    if total:
        print(f"\n{total} match(es) found.")
    else:
        print("No matches found.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
