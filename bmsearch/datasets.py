"""Text / pattern generators covering different alphabet and structure regimes."""
import random
import string
from typing import Callable, Dict, List

_WORDS = ("the of and to in is that it was for on are as with his they at be this from "
          "have or by one had not but what all were when we there can an your which "
          "their said if do will each about how up out them then she many some so "
          "these would other into has more her two like him see time could no make "
          "than first been its who now people my made over did down only way find "
          "use may water long little very after words called just where most know").split()


def random_text(n: int, alphabet, rnd: random.Random) -> str:
    return "".join(rnd.choice(alphabet) for _ in range(n))


def english_like(n: int, rnd: random.Random) -> str:
    parts, size = [], 0
    while size < n:
        w = rnd.choice(_WORDS)
        parts.append(w)
        size += len(w) + 1
    return " ".join(parts)[:n]


def markov_text(n: int, rnd: random.Random, alphabet="acgt", stay=0.7) -> str:
    """Repetitive text: each char repeats the previous with probability `stay`."""
    out, c = [], rnd.choice(alphabet)
    for _ in range(n):
        if rnd.random() > stay:
            c = rnd.choice(alphabet)
        out.append(c)
    return "".join(out)


def sample_patterns(text: str, lengths: List[int], rnd: random.Random) -> List[str]:
    """Patterns copied from the text so they actually occur."""
    return [text[(i := rnd.randrange(len(text) - m)):i + m] for m in lengths]


TEXT_GENERATORS: Dict[str, Callable[[int, random.Random], str]] = {
    "binary": lambda n, r: random_text(n, "ab", r),
    "DNA": lambda n, r: random_text(n, "ACGT", r),
    "lowercase": lambda n, r: random_text(n, string.ascii_lowercase, r),
    "ascii-128": lambda n, r: random_text(n, [chr(i) for i in range(128)], r),
    "english-like": english_like,
    "repetitive-DNA": lambda n, r: markov_text(n, r),
}

# Adversarial cases: name -> (text, pattern) factories
def adversarial(n: int, m: int):
    return {
        "a^n / a^m (all match)": ("a" * n, "a" * m),
        "a^n / b a^(m-1)": ("a" * n, "b" + "a" * (m - 1)),
        "a^n / b^m (best case)": ("a" * n, "b" * m),
        "a^n / a^(m/2) b a^(m/2)": ("a" * n, "a" * (m // 2) + "b" + "a" * (m // 2 - 1)),
    }
