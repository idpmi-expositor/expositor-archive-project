"""Parse Spanish scripture reference strings into canonical reference records."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


BOOK_ALIASES: dict[str, tuple[str, str]] = {
    "genesis": ("old", "Genesis"),
    "exodo": ("old", "Exodus"),
    "levitico": ("old", "Leviticus"),
    "numeros": ("old", "Numbers"),
    "deuteronomio": ("old", "Deuteronomy"),
    "josue": ("old", "Joshua"),
    "jueces": ("old", "Judges"),
    "rut": ("old", "Ruth"),
    "1 samuel": ("old", "1 Samuel"),
    "2 samuel": ("old", "2 Samuel"),
    "1 reyes": ("old", "1 Kings"),
    "2 reyes": ("old", "2 Kings"),
    "1 cronicas": ("old", "1 Chronicles"),
    "2 cronicas": ("old", "2 Chronicles"),
    "esdras": ("old", "Ezra"),
    "nehemias": ("old", "Nehemiah"),
    "ester": ("old", "Esther"),
    "job": ("old", "Job"),
    "salmo": ("old", "Psalms"),
    "salmos": ("old", "Psalms"),
    "proverbios": ("old", "Proverbs"),
    "eclesiastes": ("old", "Ecclesiastes"),
    "cantares": ("old", "Song of Songs"),
    "isaias": ("old", "Isaiah"),
    "jeremias": ("old", "Jeremiah"),
    "lamentaciones": ("old", "Lamentations"),
    "ezequiel": ("old", "Ezekiel"),
    "daniel": ("old", "Daniel"),
    "oseas": ("old", "Hosea"),
    "joel": ("old", "Joel"),
    "amos": ("old", "Amos"),
    "abdias": ("old", "Obadiah"),
    "jonas": ("old", "Jonah"),
    "miqueas": ("old", "Micah"),
    "nahum": ("old", "Nahum"),
    "habacuc": ("old", "Habakkuk"),
    "sofonias": ("old", "Zephaniah"),
    "hageo": ("old", "Haggai"),
    "zacarias": ("old", "Zechariah"),
    "malaquias": ("old", "Malachi"),
    "mateo": ("new", "Matthew"),
    "marcos": ("new", "Mark"),
    "lucas": ("new", "Luke"),
    "juan": ("new", "John"),
    "hechos": ("new", "Acts"),
    "romanos": ("new", "Romans"),
    "1 corintios": ("new", "1 Corinthians"),
    "2 corintios": ("new", "2 Corinthians"),
    "galatas": ("new", "Galatians"),
    "efesios": ("new", "Ephesians"),
    "filipenses": ("new", "Philippians"),
    "colosenses": ("new", "Colossians"),
    "1 tesalonicenses": ("new", "1 Thessalonians"),
    "2 tesalonicenses": ("new", "2 Thessalonians"),
    "1 timoteo": ("new", "1 Timothy"),
    "2 timoteo": ("new", "2 Timothy"),
    "tito": ("new", "Titus"),
    "filemon": ("new", "Philemon"),
    "hebreos": ("new", "Hebrews"),
    "santiago": ("new", "James"),
    "1 pedro": ("new", "1 Peter"),
    "2 pedro": ("new", "2 Peter"),
    "1 juan": ("new", "1 John"),
    "2 juan": ("new", "2 John"),
    "3 juan": ("new", "3 John"),
    "judas": ("new", "Jude"),
    "apocalipsis": ("new", "Revelation"),
}

ROMAN_PREFIXES = {"i": "1", "ii": "2", "iii": "3"}
REFERENCE_RE = re.compile(
    r"(?P<book>(?:(?:[123]|I{1,3})\s*)?[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+"
    r"(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*)\s+"
    r"(?P<chapter>\d+):(?P<verses>\d+(?:-\d+)?(?:\s*,\s*\d+(?:-\d+)?)*)"
)


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    without_accents = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    normalized = re.sub(r"\s+", " ", without_accents.lower()).strip()
    parts = normalized.split(" ", 1)
    if parts and parts[0] in ROMAN_PREFIXES:
        return f"{ROMAN_PREFIXES[parts[0]]} {parts[1]}" if len(parts) > 1 else parts[0]
    return normalized


def parse_verse_ranges(verses: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for item in re.split(r"\s*,\s*", verses):
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start = int(start_text)
            end = int(end_text)
        else:
            start = end = int(item)
        ranges.append((start, end))
    return ranges


def parse_scripture_references(reference_display: str) -> list[dict[str, Any]]:
    """Return canonical reference dictionaries parsed from a display string."""

    references: list[dict[str, Any]] = []
    current_book: tuple[str, str] | None = None

    for part in re.split(r"\s*;\s*", reference_display):
        part = part.strip().strip(".")
        if not part:
            continue

        match = REFERENCE_RE.search(part)
        if match:
            alias = normalize_text(match.group("book"))
            current_book = BOOK_ALIASES.get(alias)
            chapter = int(match.group("chapter"))
            verses = match.group("verses")
        else:
            continuation = re.search(
                r"(?P<chapter>\d+):(?P<verses>\d+(?:-\d+)?(?:\s*,\s*\d+(?:-\d+)?)*)",
                part,
            )
            if not continuation or current_book is None:
                continue
            chapter = int(continuation.group("chapter"))
            verses = continuation.group("verses")

        if current_book is None:
            continue

        testament, standardized_book = current_book
        for verse_start, verse_end in parse_verse_ranges(verses):
            references.append(
                {
                    "testament": testament,
                    "book_standardized": standardized_book,
                    "chapter": chapter,
                    "verse_start": verse_start,
                    "verse_end": verse_end,
                }
            )

    return references
