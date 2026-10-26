"""Local web application for interactive pattern search and algorithm benchmarks."""
import argparse
import json
import statistics
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Sequence
from urllib.parse import urlparse

from .algorithms import ALGORITHMS, BoyerMoore
from .bench import run_case
from .datasets import TEXT_GENERATORS, adversarial, sample_patterns

_STATIC_DIR = Path(__file__).with_name("web")
_MAX_BODY_BYTES = 4 * 1024 * 1024
_MAX_TEXT_CHARS = 2_000_000
_MAX_PATTERN_CHARS = 10_000
_BENCHMARK_ALGORITHMS = list(ALGORITHMS)


def search_text(pattern: str, text: str, algorithm: str) -> Dict[str, object]:
    """Search multiline text and return JSON-ready positions and basic metrics."""
    if not isinstance(pattern, str) or not pattern:
        raise ValueError("Enter a non-empty pattern to search for.")
    if len(pattern) > _MAX_PATTERN_CHARS:
        raise ValueError(f"Pattern must be {_MAX_PATTERN_CHARS:,} characters or fewer.")
    if not isinstance(text, str):
        raise ValueError("Text must be a string.")
    if len(text) > _MAX_TEXT_CHARS:
        raise ValueError(f"Text must be {_MAX_TEXT_CHARS:,} characters or fewer.")
    if not isinstance(algorithm, str) or algorithm not in ALGORITHMS:
        raise ValueError("Choose one of the available search algorithms.")

    if algorithm == "BM-galil":
        matcher = BoyerMoore(pattern, extended=True, galil=True)
        search = matcher.search
    else:
        search_algorithm = ALGORITHMS[algorithm]
        search = lambda line: search_algorithm(line, pattern)

    results = []
    total_matches = 0
    comparisons = 0
    started_at = time.perf_counter()
    for line_number, line in enumerate(text.splitlines(), start=1):
        result = search(line)
        comparisons += result.comparisons
        total_matches += len(result.matches)
        for position in result.matches:
            if len(results) < 1000:
                results.append(
                    {
                        "line": line_number,
                        "column": position + 1,
                        "text": line,
                        "start": position,
                        "end": position + len(pattern),
                    }
                )

    return {
        "algorithm": algorithm,
        "matches": results,
        "total_matches": total_matches,
        "results_truncated": total_matches > len(results),
        "comparisons": comparisons,
        "elapsed_ms": (time.perf_counter() - started_at) * 1000,
    }


def run_benchmark(size: int = 20_000, repetitions: int = 2) -> Dict[str, object]:
    """Run reproducible text and adversarial scenarios with every registered algorithm."""
    if not isinstance(size, int) or isinstance(size, bool) or not 256 <= size <= 100_000:
        raise ValueError("Benchmark size must be between 256 and 100,000 characters.")
    if not isinstance(repetitions, int) or isinstance(repetitions, bool) or not 1 <= repetitions <= 3:
        raise ValueError("Benchmark repetitions must be between 1 and 3.")

    import random

    generator = random.Random(42)
    lengths = [4, 16, 64]
    records: List[Dict[str, object]] = []

    def add_scenario(scenario: str, category: str, text: str, pattern: str, reps: int) -> None:
        timings = run_case(text, pattern, _BENCHMARK_ALGORITHMS, reps)
        expected_matches = None
        for name in _BENCHMARK_ALGORITHMS:
            matches = ALGORITHMS[name](text, pattern).matches
            if expected_matches is None:
                expected_matches = matches
            elif matches != expected_matches:
                raise RuntimeError(f"{name} returned different matches for scenario {scenario!r}.")
            comparisons_per_char, elapsed_ms, hit_count = timings[name]
            records.append(
                {
                    "scenario": scenario,
                    "category": category,
                    "algorithm": name,
                    "text_length": len(text),
                    "pattern_length": len(pattern),
                    "comparisons": round(comparisons_per_char * len(text)),
                    "comparisons_per_char": comparisons_per_char,
                    "elapsed_ms": elapsed_ms,
                    "matches": hit_count,
                }
            )

    for name, make_text in TEXT_GENERATORS.items():
        text = make_text(size, generator)
        for pattern in sample_patterns(text, lengths, generator):
            add_scenario(name, "Text profile", text, pattern, repetitions)

    adversarial_length = max(size // 4, 64)
    for name, (text, pattern) in adversarial(adversarial_length, 8).items():
        add_scenario(name, "Edge case", text, pattern, 1)

    summaries = []
    for name in _BENCHMARK_ALGORITHMS:
        algorithm_records = [record for record in records if record["algorithm"] == name]
        summaries.append(
            {
                "algorithm": name,
                "average_ms": statistics.mean(float(row["elapsed_ms"]) for row in algorithm_records),
                "average_comparisons_per_char": statistics.mean(
                    float(row["comparisons_per_char"]) for row in algorithm_records
                ),
            }
        )
    summaries.sort(key=lambda row: float(row["average_ms"]))

    return {
        "size": size,
        "repetitions": repetitions,
        "algorithms": _BENCHMARK_ALGORITHMS,
        "scenarios": list(dict.fromkeys(str(record["scenario"]) for record in records)),
        "records": records,
        "summary": summaries,
        "best_time": summaries[0]["algorithm"],
        "best_comparisons": min(
            summaries, key=lambda row: float(row["average_comparisons_per_char"])
        )["algorithm"],
    }


class _RequestHandler(BaseHTTPRequestHandler):
    server_version = "BMSearch/1.0"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        static_files = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/app.css": ("app.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
        }
        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        static_file = static_files.get(path)
        if static_file is None:
            self.send_error(HTTPStatus.NOT_FOUND, "Page not found")
            return
        filename, content_type = static_file
        try:
            content = (_STATIC_DIR / filename).read_bytes()
        except OSError:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Web app asset could not be read")
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route not in ("/api/search", "/api/benchmark"):
            self.send_error(HTTPStatus.NOT_FOUND, "API endpoint not found")
            return
        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "A valid Content-Length header is required."})
            return
        if not 0 <= content_length <= _MAX_BODY_BYTES:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "Request body is too large."})
            return
        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Request must contain valid JSON."})
            return
        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Request JSON must be an object."})
            return

        try:
            if route == "/api/search":
                if not isinstance(payload.get("text"), str):
                    raise ValueError("Text must be a string.")
                response = search_text(
                    payload.get("pattern"),
                    payload["text"],
                    payload.get("algorithm", "BM-galil"),
                )
            else:
                response = run_benchmark(
                    payload.get("size", 20_000),
                    payload.get("repetitions", 2),
                )
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        except RuntimeError as error:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})
            return
        self._send_json(HTTPStatus.OK, response)

    def _send_json(self, status: HTTPStatus, payload: Dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local BM Search web app.")
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default: 8000)")
    args = parser.parse_args(argv)
    if not 0 < args.port <= 65535:
        parser.error("port must be between 1 and 65535")

    server = ThreadingHTTPServer((args.host, args.port), _RequestHandler)
    print(f"BM Search is running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down BM Search.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
