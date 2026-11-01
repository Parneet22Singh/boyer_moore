# Preprocessing tables for Boyer-Moore.
from bisect import bisect_left
from typing import Dict, List


def last_occurrence(p: str) -> Dict[str, int]:
    return {c: i for i, c in enumerate(p)}


def char_positions(p: str) -> Dict[str, List[int]]:
    pos: Dict[str, List[int]] = {}
    for i, c in enumerate(p):
        pos.setdefault(c, []).append(i)
    return pos


def extended_bad_char_shift(pos: Dict[str, List[int]], c: str, j: int) -> int:
    # Shift to the nearest earlier occurrence of the mismatched character.
    lst = pos.get(c)
    if not lst:
        return j + 1
    k = bisect_left(lst, j) - 1
    return j - lst[k] if k >= 0 else j + 1


def good_suffix_table(p: str) -> List[int]:
    """Build strong good-suffix shifts in linear time using pattern borders.

    Entry j + 1 handles a mismatch at index j; entry 0 handles a full match.
    """
    m = len(p)
    shift = [0] * (m + 1)
    border = [0] * (m + 1)
    i, j = m, m + 1
    border[i] = j
    while i > 0:
        while j <= m and p[i - 1] != p[j - 1]:
            if shift[j] == 0:
                shift[j] = j - i
            j = border[j]
        i -= 1
        j -= 1
        border[i] = j
    j = border[0]
    for i in range(m + 1):
        if shift[i] == 0:
            shift[i] = j
        if i == j:
            j = border[j]
    return shift
