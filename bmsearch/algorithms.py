"""String-search algorithms. Every search returns SearchResult(matches, comparisons)
so algorithms can be compared by work done, not just wall-clock time."""
from dataclasses import dataclass
from typing import Callable, Dict, List

from .tables import (char_positions, extended_bad_char_shift,
                     good_suffix_table, last_occurrence)


@dataclass
class SearchResult:
    matches: List[int]
    comparisons: int


def naive(text: str, pat: str) -> SearchResult:
    n, m = len(text), len(pat)
    out, cmp = [], 0
    for s in range(n - m + 1):
        j = 0
        while j < m:
            cmp += 1
            if text[s + j] != pat[j]:
                break
            j += 1
        if j == m:
            out.append(s)
    return SearchResult(out, cmp)


def horspool(text: str, pat: str) -> SearchResult:
    n, m = len(text), len(pat)
    if m == 0:
        return SearchResult(list(range(n + 1)), 0)
    sh = {c: m - 1 - i for i, c in enumerate(pat[:-1])}
    out, cmp, s = [], 0, 0
    while s <= n - m:
        j = m - 1
        while j >= 0:
            cmp += 1
            if pat[j] != text[s + j]:
                break
            j -= 1
        if j < 0:
            out.append(s)
        s += sh.get(text[s + m - 1], m)
    return SearchResult(out, cmp)


class BoyerMoore:
    """Precompiled Boyer-Moore matcher for one pattern.

    bad_char    : use the bad-character rule
    good_suffix : use the strong good-suffix rule
    extended    : bad-character rule uses nearest occurrence left of the mismatch
                  (instead of the rightmost occurrence overall)
    galil       : Galil's rule - after a match, skip re-comparing the overlapping
                  border; makes the search O(n + m) even for periodic patterns
    """

    def __init__(self, pat: str, bad_char=True, good_suffix=True,
                 extended=False, galil=False):
        self.pat, self.m = pat, len(pat)
        self.bad_char, self.good_suffix = bad_char, good_suffix
        self.extended, self.galil = extended, galil and good_suffix
        if self.m == 0:
            return
        self.last = last_occurrence(pat) if bad_char and not extended else None
        self.pos = char_positions(pat) if bad_char and extended else None
        self.gs = good_suffix_table(pat) if good_suffix else None
        self.period = self.gs[0] if good_suffix else 1

    def search(self, text: str) -> SearchResult:
        p, m, n = self.pat, self.m, len(text)
        if m == 0:
            return SearchResult(list(range(n + 1)), 0)
        gs, last, pos = self.gs, self.last, self.pos
        out, cmp, s, skip = [], 0, 0, 0   # skip = prefix chars known to match (Galil)
        while s <= n - m:
            j = m - 1
            while j >= skip:
                cmp += 1
                if p[j] != text[s + j]:
                    break
                j -= 1
            if j < skip:                          # full match
                out.append(s)
                s += self.period if self.good_suffix else 1
                skip = m - self.period if self.galil else 0
            else:                                 # mismatch at j
                c = text[s + j]
                a = gs[j + 1] if gs else 1
                if last is not None:
                    b = max(1, j - last.get(c, -1))
                elif pos is not None:
                    b = extended_bad_char_shift(pos, c, j)
                else:
                    b = 1
                s += a if a > b else b
                skip = 0
        return SearchResult(out, cmp)


def boyer_moore(text: str, pat: str, **opts) -> SearchResult:
    return BoyerMoore(pat, **opts).search(text)


ALGORITHMS: Dict[str, Callable[[str, str], SearchResult]] = {
    "naive": naive,
    "horspool": horspool,
    "BM-bc": lambda t, p: boyer_moore(t, p, good_suffix=False),
    "BM-bc-ext": lambda t, p: boyer_moore(t, p, good_suffix=False, extended=True),
    "BM-gs": lambda t, p: boyer_moore(t, p, bad_char=False),
    "BM-full": boyer_moore,
    "BM-full-ext": lambda t, p: boyer_moore(t, p, extended=True),
    "BM-galil": lambda t, p: boyer_moore(t, p, extended=True, galil=True),
}
