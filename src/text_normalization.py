from __future__ import annotations

import unicodedata

TRANSLATION = str.maketrans({
    "\r": "\n", "\u00a0": " ", "\u200b": "", "\ufeff": "",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u2022": "•",
})


def normalize_with_mapping(text: str) -> tuple[str, list[int]]:
    """Normalize text and map every normalized character to a raw offset."""
    out: list[str] = []
    mapping: list[int] = []
    previous_space = False
    previous_newline = False
    clusters: list[tuple[int, str]] = []
    for raw_i, original in enumerate(text):
        translated = original.translate(TRANSLATION)
        if translated and unicodedata.combining(translated[0]) and clusters:
            index, value = clusters[-1]
            clusters[-1] = (index, value + translated)
        else:
            clusters.append((raw_i, translated))
    for raw_i, cluster in clusters:
        expanded = unicodedata.normalize("NFC", cluster)
        for char in expanded:
            if char == "\n":
                if previous_newline:
                    continue
                while out and out[-1] == " ":
                    out.pop(); mapping.pop()
                out.append("\n"); mapping.append(raw_i)
                previous_space, previous_newline = False, True
            elif char.isspace():
                if not previous_space and not previous_newline and out:
                    out.append(" "); mapping.append(raw_i)
                previous_space = True
            elif unicodedata.category(char) not in {"Cc", "Cf"}:
                out.append(char); mapping.append(raw_i)
                previous_space = previous_newline = False
    while out and out[-1] in {" ", "\n"}:
        out.pop(); mapping.pop()
    return "".join(out), mapping


def normalize_text(text: str) -> str:
    return normalize_with_mapping(text)[0]


def normalize_match_value(value: object) -> str:
    return normalize_text(str(value)).casefold()
