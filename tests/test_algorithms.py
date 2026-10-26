import random
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from bmsearch import ALGORITHMS, BoyerMoore, good_suffix_table
from bmsearch.cli import main as cli_main
from bmsearch.web import run_benchmark, search_text


def brute(t, p):
    return [i for i in range(len(t) - len(p) + 1) if t.startswith(p, i)]


class TestAlgorithms(unittest.TestCase):
    def test_algorithm_comparison_set(self):
        self.assertEqual(
            list(ALGORITHMS),
            ["naive", "horspool", "BM-bc", "BM-bc-ext", "BM-gs", "BM-full", "BM-full-ext", "BM-galil"],
        )

    def test_random_agreement(self):
        rnd = random.Random(7)
        for _ in range(4000):
            alpha = rnd.choice(["a", "ab", "abc", "acgt"])
            t = "".join(rnd.choice(alpha) for _ in range(rnd.randint(0, 70)))
            p = "".join(rnd.choice(alpha) for _ in range(rnd.randint(1, 9)))
            exp = brute(t, p)
            for name, f in ALGORITHMS.items():
                self.assertEqual(f(t, p).matches, exp, (name, t, p))

    def test_edge_cases(self):
        for name, f in ALGORITHMS.items():
            self.assertEqual(f("", "a").matches, [], name)
            self.assertEqual(f("abc", "abcd").matches, [], name)
            self.assertEqual(f("abc", "abc").matches, [0], name)
            self.assertEqual(f("aaaa", "aa").matches, [0, 1, 2], name)
            self.assertEqual(f("abcabc", "c").matches, [2, 5], name)

    def test_empty_pattern(self):
        self.assertEqual(BoyerMoore("").search("ab").matches, [0, 1, 2])

    def test_unicode(self):
        self.assertEqual(ALGORITHMS["BM-full"]("héllo wörld héllo", "héllo").matches, [0, 12])

    def test_good_suffix_known_table(self):
        # GCAGAGAG (hand-verified): e.g. shift[4]=2 because suffix AGAG recurs at
        # index 2 preceded by C; shift[5]=7 because only the border "G" survives.
        self.assertEqual(good_suffix_table("GCAGAGAG"), [7, 7, 7, 7, 2, 7, 4, 7, 1])

    def test_galil_is_linear(self):
        n, m = 20000, 40
        r = ALGORITHMS["BM-galil"]("a" * n, "a" * m)
        self.assertLess(r.comparisons, 3 * n)
        r2 = ALGORITHMS["BM-full"]("a" * n, "a" * m)
        self.assertGreater(r2.comparisons, 10 * n)  # quadratic-ish without Galil

    def test_comparisons_sublinear_on_large_alphabet(self):
        rnd = random.Random(1)
        t = "".join(rnd.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(50000))
        r = ALGORITHMS["BM-full"](t, t[1000:1032])
        self.assertLess(r.comparisons, len(t) / 8)

    def test_cli_searches_text_and_reports_positions(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = cli_main(["find", "aba", "--text", "ababa"])
        self.assertEqual(result, 0)
        self.assertIn("1:1: ababa", output.getvalue())
        self.assertIn("1:3: ababa", output.getvalue())
        self.assertIn("2 match(es) found.", output.getvalue())

    def test_cli_searches_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.txt"
            path.write_text("first match\nno hit\nmatch again\n", encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                result = cli_main(["find", "match", str(path)])
        self.assertEqual(result, 0)
        self.assertIn(f"{path}:1:7: first match", output.getvalue())
        self.assertIn(f"{path}:3:1: match again", output.getvalue())
        self.assertIn("2 match(es) found.", output.getvalue())

    def test_cli_reports_missing_file(self):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            result = cli_main(["find", "pattern", "missing-file.txt"])
        self.assertEqual(result, 1)
        self.assertIn("missing-file.txt", errors.getvalue())

    def test_web_search_reports_multiline_match_positions(self):
        result = search_text("aba", "ababa\nnothing\naba", "BM-galil")
        self.assertEqual(result["total_matches"], 3)
        self.assertEqual(
            [(match["line"], match["column"]) for match in result["matches"]],
            [(1, 1), (1, 3), (3, 1)],
        )
        self.assertGreaterEqual(result["comparisons"], 0)
        self.assertGreaterEqual(result["elapsed_ms"], 0)

    def test_web_search_rejects_invalid_inputs(self):
        for pattern, text, algorithm in [
            ("", "text", "BM-galil"),
            ("needle", "text", "missing"),
            ("needle", "text", []),
        ]:
            with self.subTest(pattern=pattern, algorithm=algorithm):
                with self.assertRaises(ValueError):
                    search_text(pattern, text, algorithm)

    def test_web_benchmark_runs_all_algorithms_and_scenarios(self):
        result = run_benchmark(size=256, repetitions=1)
        self.assertEqual(result["algorithms"], list(ALGORITHMS))
        self.assertEqual(len(result["scenarios"]), 10)
        self.assertEqual(len(result["records"]), 22 * len(ALGORITHMS))
        self.assertEqual(
            {record["algorithm"] for record in result["records"]},
            set(ALGORITHMS),
        )
        self.assertIn(result["best_time"], ALGORITHMS)
        self.assertIn(result["best_comparisons"], ALGORITHMS)

    def test_web_benchmark_validates_limits(self):
        with self.assertRaises(ValueError):
            run_benchmark(size=100, repetitions=1)
        with self.assertRaises(ValueError):
            run_benchmark(size=256, repetitions=4)


if __name__ == "__main__":
    unittest.main()
