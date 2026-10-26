# BM Search

BM Search is a local pattern-finding application with a polished browser interface and a command-line option. Search pasted text or run a controlled performance comparison across eight string-matching algorithms. Each match includes its line and column.

The search engine is implemented in pure Python. Its default is Boyer–Moore with an extended bad-character table, the strong good-suffix rule and Galil's rule. The application can also run and compare all eight search algorithms. The interface and server run on your machine and require no third-party packages.

## Launch the application

Requires Python 3.9 or newer. No third-party packages are needed.

From the project directory, start the local web app:

```powershell
python -m bmsearch.web
```

Open **http://127.0.0.1:8000** in your browser. The app has two views:

- **Pattern search** accepts a pattern and multiline text, reports every matching line and column, and shows the character-comparison count and search time. Choose any of the eight algorithms from the dropdown.
- **Algorithm lab** benchmarks all eight algorithms against binary, DNA, lowercase, 128-symbol, English-like and repetitive text, plus four edge-case patterns. It shows average runtime and comparisons per character, and a per-scenario results table. Benchmark sizes range from 10,000 to 100,000 characters.

Stop the server with **Ctrl+C**. To use a different local port:

```powershell
python -m bmsearch.web --port 8080
```

For an installed `bmsearch-ui` command, install the project into the active Python environment:

```powershell
python -m pip install -e .
bmsearch-ui
```

## Command-line search

```powershell
python -m bmsearch find "Boyer-Moore" README.md
python -m bmsearch find "needle" --text "Look for a needle in this haystack."
```

When searching files, the command prints one result per match in `file:line:column: text` format. With no file paths or `--text` argument, it reads from standard input. Use `--algorithm` to select one of `naive`, `horspool`, `BM-bc`, `BM-bc-ext`, `BM-gs`, `BM-full`, `BM-full-ext`, or `BM-galil`.

## Run the test suite and standalone benchmark

```powershell
python -m unittest discover -s tests
python -m bmsearch.bench --quick
python -m bmsearch.bench --n 500000 --csv benchmark-results.csv
```

## Use the search engine from Python

```powershell
from bmsearch import BoyerMoore

matcher = BoyerMoore("GCAGAGAG", extended=True, galil=True)
result = matcher.search("GCATCGCAGAGAGTATACAGTACG")
print(result.matches)       # [5]
print(result.comparisons)   # character comparisons performed
```

## Project structure

```text
bmsearch/
  algorithms.py   naive, Horspool and Boyer-Moore search algorithms
  cli.py          command-line pattern finder
  web.py          local web server and search / benchmark APIs
  web/            responsive browser interface
  tables.py       bad-character and strong good-suffix preprocessing
  datasets.py     benchmark text generators and adversarial cases
  bench.py        standalone performance comparison and CSV export
tests/
  test_algorithms.py
```
