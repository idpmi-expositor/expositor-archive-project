"""Deterministic OCR quality gate for PDF page text extraction.

The gate is intentionally limited to extraction quality control. It does not
rewrite OCR text, infer lesson structure, or alter canonical YAML rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable


class QualityStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NEEDS_OCR = "NEEDS_OCR"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class Issue(str, Enum):
    ZERO_TEXT = "zero_text"
    LOW_WORD_COUNT = "low_word_count"
    LOW_VALID_CHAR_RATIO = "low_valid_char_ratio"
    MALFORMED_CHARACTERS = "malformed_characters"
    MERGED_LINES = "merged_lines"
    REPEATED_HEADER_FOOTER = "repeated_header_footer"
    MALFORMED_SCRIPTURE_REFERENCE = "malformed_scripture_reference"
    LOW_OCR_CONFIDENCE = "low_ocr_confidence"


@dataclass(frozen=True)
class QualityThresholds:
    min_pass_words: int = 25
    min_ocr_words: int = 10
    min_valid_char_ratio: float = 0.85
    replacement_char_warning_count: int = 1
    replacement_char_fail_count: int = 5
    long_line_chars: int = 160
    merged_line_warning_ratio: float = 0.25
    merged_line_ocr_ratio: float = 0.50
    malformed_scripture_review_count: int = 3
    ocr_warning_confidence: float = 70.0
    ocr_pass_confidence: float = 85.0
    source_tie_margin: int = 5


@dataclass(frozen=True)
class PageQuality:
    page_number: int
    source: str
    status: QualityStatus
    text: str
    word_count: int
    issues: tuple[Issue, ...]
    ocr_required: bool
    confidence_score: int
    valid_char_ratio: float
    long_line_ratio: float
    malformed_scripture_count: int

    def to_metadata(self) -> dict:
        return {
            "page_number": self.page_number,
            "status": self.status.value,
            "selected_source": (
                self.source
                if self.status in {QualityStatus.PASS, QualityStatus.WARNING}
                else None
            ),
            "word_count": self.word_count,
            "issues": [issue.value for issue in self.issues],
            "ocr_required": self.ocr_required,
            "confidence_score": self.confidence_score,
        }


WORD_RE = re.compile(r"[^\W_]+(?:['-][^\W_]+)?", re.UNICODE)
VALID_PUNCTUATION = set(".,;:'\"!?()[]-/&%¡¿")

BOOK_PATTERN = (
    r"(?:[1-3]\s*)?"
    r"(?:Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|"
    r"Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Job|Psalms?|Proverbs|"
    r"Ecclesiastes|Song(?: of Solomon)?|Isaiah|Jeremiah|Lamentations|Ezekiel|"
    r"Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|"
    r"Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|"
    r"Corinthians|Galatians|Ephesians|Philippians|Colossians|Thessalonians|"
    r"Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|Revelation|"
    r"G[eé]nesis|[EÉ]xodo|Lev[ií]tico|N[uú]meros|Deuteronomio|Josu[eé]|"
    r"Jueces|Rut|Samuel|Reyes|Cr[oó]nicas|Esdras|Nehem[ií]as|Ester|Job|"
    r"Salmos?|Proverbios|Eclesiast[eé]s|Cantares|Isa[ií]as|Jerem[ií]as|"
    r"Lamentaciones|Ezequiel|Daniel|Oseas|Joel|Am[oó]s|Abd[ií]as|Jon[aá]s|"
    r"Miqueas|Nah[uú]m|Habacuc|Sofon[ií]as|Hageo|Zacar[ií]as|Malaqu[ií]as|"
    r"Mateo|Marcos|Lucas|Juan|Hechos|Romanos|Corintios|G[aá]latas|Efesios|"
    r"Filipenses|Colosenses|Tesalonicenses|Timoteo|Tito|Filem[oó]n|Hebreos|"
    r"Santiago|Pedro|Judas|Apocalipsis)"
)

MALFORMED_SCRIPTURE_RE = re.compile(
    rf"\b{BOOK_PATTERN}\s+\d{{1,3}}\s*(?:[;.\s]|[:][lIoO])\s*"
    rf"[lIoO0-9]{{1,3}}(?:\s*[-]\s*[lIoO0-9]{{1,3}})?\b",
    re.IGNORECASE,
)


def evaluate_page_text(
    page_number: int,
    text: str | None,
    source: str,
    ocr_confidence: float | None = None,
    thresholds: QualityThresholds | None = None,
) -> PageQuality:
    """Evaluate one page of extracted text using deterministic rules."""

    thresholds = thresholds or QualityThresholds()
    normalized_text = text or ""
    stripped = normalized_text.strip()
    words = WORD_RE.findall(stripped)
    word_count = len(words)
    issues: list[Issue] = []

    if not stripped:
        issues.append(Issue.ZERO_TEXT)

    if word_count < thresholds.min_pass_words:
        issues.append(Issue.LOW_WORD_COUNT)

    valid_char_ratio = _valid_char_ratio(stripped)
    if stripped and valid_char_ratio < thresholds.min_valid_char_ratio:
        issues.append(Issue.LOW_VALID_CHAR_RATIO)

    replacement_count = stripped.count("\ufffd")
    if replacement_count >= thresholds.replacement_char_warning_count:
        issues.append(Issue.MALFORMED_CHARACTERS)

    long_line_ratio = _long_line_ratio(stripped, thresholds.long_line_chars)
    if long_line_ratio > thresholds.merged_line_warning_ratio:
        issues.append(Issue.MERGED_LINES)

    malformed_scripture_count = len(MALFORMED_SCRIPTURE_RE.findall(stripped))
    if malformed_scripture_count:
        issues.append(Issue.MALFORMED_SCRIPTURE_REFERENCE)

    if ocr_confidence is not None and ocr_confidence < thresholds.ocr_warning_confidence:
        issues.append(Issue.LOW_OCR_CONFIDENCE)

    status = _status_from_rules(
        source=source,
        stripped_text=stripped,
        word_count=word_count,
        valid_char_ratio=valid_char_ratio,
        replacement_count=replacement_count,
        long_line_ratio=long_line_ratio,
        malformed_scripture_count=malformed_scripture_count,
        ocr_confidence=ocr_confidence,
        thresholds=thresholds,
    )

    confidence_score = _confidence_score(
        base_ocr_confidence=ocr_confidence,
        issues=issues,
        status=status,
    )

    return PageQuality(
        page_number=page_number,
        source=source,
        status=status,
        text=normalized_text,
        word_count=word_count,
        issues=tuple(dict.fromkeys(issues)),
        ocr_required=status == QualityStatus.NEEDS_OCR,
        confidence_score=confidence_score,
        valid_char_ratio=valid_char_ratio,
        long_line_ratio=long_line_ratio,
        malformed_scripture_count=malformed_scripture_count,
    )


def select_best_page_text(
    pymupdf_result: PageQuality,
    ocr_result: PageQuality | None,
    thresholds: QualityThresholds | None = None,
) -> PageQuality:
    """Select the deterministic winner between PyMuPDF and OCR output."""

    thresholds = thresholds or QualityThresholds()

    if ocr_result is None:
        return pymupdf_result

    usable_statuses = {QualityStatus.PASS, QualityStatus.WARNING}

    if pymupdf_result.status in usable_statuses and ocr_result.status not in usable_statuses:
        return pymupdf_result

    if ocr_result.status in usable_statuses and pymupdf_result.status not in usable_statuses:
        return ocr_result

    if pymupdf_result.status in usable_statuses and ocr_result.status in usable_statuses:
        difference = ocr_result.confidence_score - pymupdf_result.confidence_score
        if difference > thresholds.source_tie_margin:
            return ocr_result
        return pymupdf_result

    return PageQuality(
        page_number=pymupdf_result.page_number,
        source="none",
        status=QualityStatus.NEEDS_HUMAN_REVIEW,
        text="",
        word_count=max(pymupdf_result.word_count, ocr_result.word_count),
        issues=tuple(dict.fromkeys((*pymupdf_result.issues, *ocr_result.issues))),
        ocr_required=True,
        confidence_score=max(
            pymupdf_result.confidence_score,
            ocr_result.confidence_score,
        ),
        valid_char_ratio=max(pymupdf_result.valid_char_ratio, ocr_result.valid_char_ratio),
        long_line_ratio=max(pymupdf_result.long_line_ratio, ocr_result.long_line_ratio),
        malformed_scripture_count=max(
            pymupdf_result.malformed_scripture_count,
            ocr_result.malformed_scripture_count,
        ),
    )


def apply_repeated_header_footer_issues(
    pages: Iterable[PageQuality],
    min_repeated_pages: int = 3,
    edge_line_count: int = 3,
) -> list[PageQuality]:
    """Flag repeated edge lines without rewriting page text."""

    page_list = list(pages)
    line_pages: dict[str, set[int]] = {}

    for page in page_list:
        for line in _edge_lines(page.text, edge_line_count):
            normalized = _normalize_edge_line(line)
            if normalized:
                line_pages.setdefault(normalized, set()).add(page.page_number)

    repeated_lines = {
        line
        for line, page_numbers in line_pages.items()
        if len(page_numbers) >= min_repeated_pages
    }

    if not repeated_lines:
        return page_list

    updated_pages: list[PageQuality] = []
    for page in page_list:
        has_repeated_edge_line = any(
            _normalize_edge_line(line) in repeated_lines
            for line in _edge_lines(page.text, edge_line_count)
        )
        if not has_repeated_edge_line:
            updated_pages.append(page)
            continue

        issues = tuple(dict.fromkeys((*page.issues, Issue.REPEATED_HEADER_FOOTER)))
        status = QualityStatus.WARNING if page.status == QualityStatus.PASS else page.status

        updated_pages.append(
            PageQuality(
                page_number=page.page_number,
                source=page.source,
                status=status,
                text=page.text,
                word_count=page.word_count,
                issues=issues,
                ocr_required=page.ocr_required,
                confidence_score=max(0, page.confidence_score - 10),
                valid_char_ratio=page.valid_char_ratio,
                long_line_ratio=page.long_line_ratio,
                malformed_scripture_count=page.malformed_scripture_count,
            )
        )

    return updated_pages


def _status_from_rules(
    source: str,
    stripped_text: str,
    word_count: int,
    valid_char_ratio: float,
    replacement_count: int,
    long_line_ratio: float,
    malformed_scripture_count: int,
    ocr_confidence: float | None,
    thresholds: QualityThresholds,
) -> QualityStatus:
    is_ocr_source = source.lower() not in {"pymupdf", "embedded"}

    if not stripped_text or word_count < thresholds.min_ocr_words:
        return QualityStatus.NEEDS_HUMAN_REVIEW if is_ocr_source else QualityStatus.NEEDS_OCR

    hard_quality_failure = (
        valid_char_ratio < thresholds.min_valid_char_ratio
        or replacement_count >= thresholds.replacement_char_fail_count
    )
    if hard_quality_failure:
        return QualityStatus.NEEDS_HUMAN_REVIEW if is_ocr_source else QualityStatus.NEEDS_OCR

    if not is_ocr_source and long_line_ratio > thresholds.merged_line_ocr_ratio:
        return QualityStatus.NEEDS_OCR

    if malformed_scripture_count >= thresholds.malformed_scripture_review_count:
        return QualityStatus.NEEDS_HUMAN_REVIEW

    if is_ocr_source and ocr_confidence is not None:
        if ocr_confidence < thresholds.ocr_warning_confidence:
            return QualityStatus.NEEDS_HUMAN_REVIEW
        if ocr_confidence < thresholds.ocr_pass_confidence:
            return QualityStatus.WARNING

    if (
        word_count < thresholds.min_pass_words
        or long_line_ratio > thresholds.merged_line_warning_ratio
        or malformed_scripture_count > 0
        or replacement_count > 0
    ):
        return QualityStatus.WARNING

    return QualityStatus.PASS


def _confidence_score(
    base_ocr_confidence: float | None,
    issues: Iterable[Issue],
    status: QualityStatus,
) -> int:
    score = 100 if base_ocr_confidence is None else int(round(base_ocr_confidence))

    penalties = {
        Issue.ZERO_TEXT: 40,
        Issue.LOW_WORD_COUNT: 20,
        Issue.LOW_VALID_CHAR_RATIO: 25,
        Issue.MALFORMED_CHARACTERS: 15,
        Issue.MERGED_LINES: 15,
        Issue.REPEATED_HEADER_FOOTER: 10,
        Issue.MALFORMED_SCRIPTURE_REFERENCE: 15,
        Issue.LOW_OCR_CONFIDENCE: 20,
    }

    issue_set = set(issues)
    for issue, penalty in penalties.items():
        if issue in issue_set:
            score -= penalty

    if status == QualityStatus.NEEDS_OCR:
        score = min(score, 49)
    elif status == QualityStatus.NEEDS_HUMAN_REVIEW:
        score = min(score, 59)
    elif status == QualityStatus.WARNING:
        score = min(score, 89)

    return max(0, min(100, score))


def _valid_char_ratio(text: str) -> float:
    if not text:
        return 0.0
    valid_chars = sum(
        1
        for char in text
        if char.isalnum() or char.isspace() or char in VALID_PUNCTUATION
    )
    return valid_chars / len(text)


def _long_line_ratio(text: str, long_line_chars: int) -> float:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return 0.0
    long_lines = [line for line in lines if len(line) > long_line_chars]
    return len(long_lines) / len(lines)


def _edge_lines(text: str, edge_line_count: int) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) <= edge_line_count * 2:
        return lines
    return [*lines[:edge_line_count], *lines[-edge_line_count:]]


def _normalize_edge_line(line: str) -> str:
    normalized = re.sub(r"\s+", " ", line.strip().lower())
    normalized = re.sub(r"\b\d+\b", "#", normalized)
    if len(normalized) < 5:
        return ""
    return normalized
