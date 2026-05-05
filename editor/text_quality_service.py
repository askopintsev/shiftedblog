from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from html import unescape
from itertools import pairwise
from typing import Any, ClassVar
from uuid import UUID, uuid4

from django.conf import settings

try:
    import language_tool_python
except ImportError:
    language_tool_python = None

try:
    from spellchecker import SpellChecker
except ImportError:
    SpellChecker = None

MetricStatus = str

_WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:[-'][A-Za-zА-Яа-яЁё]+)*")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])[\s\n]+")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_MIXED_ALPHABET_RE = re.compile(r"(?=.*[A-Za-z])(?=.*[А-Яа-яЁё])[A-Za-zА-Яа-яЁё]+")
_TRIPLE_CHAR_RE = re.compile(r"(.)\1{2,}")
_CONSONANT_CLUSTER_RE = re.compile(
    r"[бвгджзйклмнпрстфхцчшщ]{5,}|[bcdfghjklmnpqrstvwxyz]{5,}",
    re.IGNORECASE,
)
_PUNCT_REPEAT_RE = re.compile(r"[!?.,;:]{3,}")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+[,.!?;:]")
_NO_SPACE_AFTER_PUNCT_RE = re.compile(r"[,.!?;:][^\s\])}\"»”]")
_DOUBLE_COMMA_RE = re.compile(r",\s*,")
_COMMON_RU_MISTAKES_RE = re.compile(r"жы|шы|чя|щя|чю|щю", re.IGNORECASE)
_LIST_MARKER_RE = re.compile(r"(?:^|\s)(?:[-*•]|\d+[.)])\s+")
_DECIMAL_NUMBER_RE = re.compile(r"\b\d[\d\s]*(?:[.,]\d+)+\b")
_NUMERIC_TOKEN_RE = re.compile(r"\b\d[\d\s\-/:]*\b")
_ABBREVIATION_RE = re.compile(
    r"\b(?:т\.к\.|т\.е\.|т\.д\.|т\.п\.|т\.н\.|и\s+т\.д\.|и\s+т\.п\.|"
    r"e\.g\.|i\.e\.)",
    re.IGNORECASE,
)

_STOP_WORDS = {
    "и",
    "а",
    "но",
    "или",
    "как",
    "так",
    "это",
    "этот",
    "эта",
    "эти",
    "для",
    "про",
    "по",
    "на",
    "в",
    "во",
    "к",
    "ко",
    "с",
    "со",
    "от",
    "до",
    "что",
    "чтобы",
    "когда",
    "если",
    "то",
    "же",
    "ли",
    "бы",
    "у",
    "из",
    "за",
    "над",
    "под",
    "при",
    "about",
    "the",
    "a",
    "an",
    "to",
    "for",
    "with",
    "of",
    "on",
    "in",
    "and",
    "or",
    "if",
    "that",
    "this",
}


def _clamp(value: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    return max(min_value, min(max_value, value))


def _piecewise_linear(value: float, points: list[tuple[float, float]]) -> float:
    if value <= points[0][0]:
        return points[0][1]
    if value >= points[-1][0]:
        return points[-1][1]
    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        if value <= x1:
            ratio = (value - x0) / (x1 - x0)
            return y0 + ratio * (y1 - y0)
    return points[-1][1]


def _status_for_score(score: int) -> MetricStatus:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 55:
        return "fair"
    if score >= 40:
        return "weak"
    return "poor"


def _grade_for_score(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 55:
        return "D"
    if score >= 40:
        return "E"
    return "F"


def _is_edit_distance_one(a: str, b: str) -> bool:
    if a == b:
        return False
    la = len(a)
    lb = len(b)
    if abs(la - lb) > 1:
        return False
    if la > lb:
        a, b = b, a
        la, lb = lb, la

    i = 0
    j = 0
    edits = 0
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1
            j += 1
            continue
        edits += 1
        if edits > 1:
            return False
        if la == lb:
            i += 1
            j += 1
        else:
            j += 1
    if i < la or j < lb:
        edits += 1
    return edits == 1


@dataclass(frozen=True)
class TextQualityRequestDTO:
    text: str
    locale: str = "ru-RU"
    content_format: str = "html"
    request_id: UUID = field(default_factory=uuid4)
    enable_extra_metrics: bool = True


@dataclass(frozen=True)
class MetricScoreDTO:
    score: int
    weight: float
    status: MetricStatus
    reasons: list[str]
    suggestions: list[str]
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TextMetaDTO:
    characters: int
    characters_no_spaces: int
    words: int
    sentences: int
    paragraphs: int
    reading_time_minutes: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OverallScoreDTO:
    score: int
    grade: str
    status: str
    formula: str
    weights_sum: float
    weighted_metrics: list[str]
    top_issues: list[str]
    editor_hint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TextQualityReportDTO:
    schema_version: str
    request_id: str
    ok: bool
    locale: str
    content_format: str
    analyzed_at: str
    text_meta: TextMetaDTO
    scores: dict[str, MetricScoreDTO]
    overall: OverallScoreDTO
    timing_ms: dict[str, int]
    engine: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "ok": self.ok,
            "locale": self.locale,
            "content_format": self.content_format,
            "analyzed_at": self.analyzed_at,
            "text_meta": self.text_meta.to_dict(),
            "scores": {k: v.to_dict() for k, v in self.scores.items()},
            "overall": self.overall.to_dict(),
            "timing_ms": self.timing_ms,
            "engine": self.engine,
        }


@dataclass(frozen=True)
class _PreparedText:
    source_text: str
    plain_text: str
    words: list[str]
    sentences: list[str]
    paragraphs: list[str]


@dataclass(frozen=True)
class _LanguageToolInsights:
    orthography_issues: int
    punctuation_issues: int
    total_matches: int
    source: str
    spellchecker_issues: int = 0


class PostTextQualityService:
    _WEIGHTS: ClassVar[dict[str, float]] = {
        "readability": 0.20,
        "spam_words": 0.15,
        "waterness": 0.15,
        "orthography": 0.20,
        "punctuation": 0.15,
        "typos": 0.15,
    }
    _lt_tools: ClassVar[dict[str, Any]] = {}
    _lt_failed_locales: ClassVar[set[str]] = set()
    _spell_tools: ClassVar[dict[str, Any]] = {}
    _spell_failed_langs: ClassVar[set[str]] = set()

    def evaluate(self, request: TextQualityRequestDTO) -> TextQualityReportDTO:
        started_at = datetime.now(tz=UTC)
        prepared = self._prepare_text(request.text, request.content_format)
        text_meta = self._build_text_meta(prepared)
        lt_insights = self._analyze_with_languagetool(
            plain_text=prepared.plain_text,
            locale=request.locale,
        )

        scores = {
            "readability": self.score_readability(prepared),
            "spam_words": self.score_spam_words(prepared),
            "waterness": self.score_waterness(prepared),
            "orthography": self.score_orthography(prepared, lt_insights),
            "punctuation": self.score_punctuation(prepared, lt_insights),
            "typos": self.score_typos(prepared),
        }
        if request.enable_extra_metrics:
            scores["clarity"] = self.score_clarity(prepared)
            scores["structure"] = self.score_structure(prepared, request.content_format)

        overall = self.compute_overall(scores)

        duration_ms = max(
            1,
            int((datetime.now(tz=UTC) - started_at).total_seconds() * 1000),
        )
        timing_ms = {
            "total": duration_ms,
            "readability": 2,
            "spam_words": 1,
            "waterness": 2,
            "orthography": 2,
            "punctuation": 2,
            "typos": 2,
            "extras": 2 if request.enable_extra_metrics else 0,
        }
        return TextQualityReportDTO(
            schema_version="1.0",
            request_id=str(request.request_id),
            ok=True,
            locale=request.locale,
            content_format=request.content_format,
            analyzed_at=datetime.now(tz=UTC).isoformat(),
            text_meta=text_meta,
            scores=scores,
            overall=overall,
            timing_ms=timing_ms,
            engine={
                "name": "post-text-quality-service",
                "version": "1.0.0",
            },
        )

    def _analyze_with_languagetool(
        self,
        plain_text: str,
        locale: str,
    ) -> _LanguageToolInsights | None:
        if not getattr(settings, "TEXT_QUALITY_PY_CHECKER_ENABLED", False):
            return None
        if len(plain_text) < 40:
            return None

        language = str(
            getattr(settings, "TEXT_QUALITY_LANGUAGETOOL_LANGUAGE", "")
            or locale
            or "ru-RU"
        )
        matches: list[Any] = []
        lt_tool = self._get_language_tool(language)
        if lt_tool is not None:
            try:
                matches = lt_tool.check(plain_text[:20000])
            except Exception:
                matches = []

        orthography_issues = 0
        punctuation_issues = 0
        spellchecker_issues = self._count_spellchecker_issues(plain_text, locale)
        for match in matches:
            issue_type = str(getattr(match, "ruleIssueType", "")).lower()
            category_id = str(getattr(match, "category", "")).upper()

            if issue_type in {"misspelling", "typographical"}:
                orthography_issues += 1
                continue
            if issue_type == "punctuation":
                punctuation_issues += 1
                continue
            if category_id in {"TYPOS", "CASING"}:
                orthography_issues += 1
            elif category_id in {"PUNCTUATION"}:
                punctuation_issues += 1

        if not matches and spellchecker_issues == 0:
            return None

        return _LanguageToolInsights(
            orthography_issues=orthography_issues,
            punctuation_issues=punctuation_issues,
            total_matches=len(matches),
            source="python_libs",
            spellchecker_issues=spellchecker_issues,
        )

    def _get_language_tool(self, language: str) -> Any | None:
        if language in self._lt_failed_locales:
            return None
        if language in self._lt_tools:
            return self._lt_tools[language]
        if language_tool_python is None:
            self._lt_failed_locales.add(language)
            return None
        try:
            tool = language_tool_python.LanguageTool(language)
        except Exception:
            self._lt_failed_locales.add(language)
            return None
        self._lt_tools[language] = tool
        return tool

    def _count_spellchecker_issues(self, plain_text: str, locale: str) -> int:
        if SpellChecker is None:
            return 0
        lang = "ru" if locale.lower().startswith("ru") else "en"
        if lang in self._spell_failed_langs:
            return 0
        spell_tool = self._spell_tools.get(lang)
        if spell_tool is None:
            try:
                spell_tool = SpellChecker(language=lang, distance=1)
            except Exception:
                self._spell_failed_langs.add(lang)
                return 0
            self._spell_tools[lang] = spell_tool

        words = [
            token for token in _WORD_RE.findall(plain_text.lower()) if len(token) >= 4
        ]
        if not words:
            return 0
        try:
            return len(spell_tool.unknown(words))
        except Exception:
            return 0

    def _near_duplicate_typo_candidates(
        self,
        token_counts: Counter[str],
    ) -> set[str]:
        typo_candidates: set[str] = set()
        frequent = [
            token
            for token, count in token_counts.items()
            if count >= 1 and len(token) >= 6
        ]
        rare = [
            token
            for token, count in token_counts.items()
            if count == 1 and len(token) >= 4
        ]
        for rare_token in rare:
            for base_token in frequent:
                if base_token == rare_token:
                    continue
                if rare_token[0] != base_token[0]:
                    continue
                if (
                    len(rare_token) >= 2
                    and len(base_token) >= 2
                    and rare_token[:2] != base_token[:2]
                ):
                    continue
                if rare_token[-1] != base_token[-1]:
                    continue
                if _is_edit_distance_one(rare_token, base_token):
                    base_count = token_counts.get(base_token, 0)
                    rare_count = token_counts.get(rare_token, 0)
                    if base_count < rare_count:
                        continue
                    if base_count == rare_count and base_token > rare_token:
                        continue
                    typo_candidates.add(rare_token)
                    break
        return typo_candidates

    def _prepare_text(self, text: str, content_format: str) -> _PreparedText:
        plain_text = self._to_plain_text(text) if content_format == "html" else text
        normalized = _WS_RE.sub(" ", plain_text).strip()
        words = [w.lower() for w in _WORD_RE.findall(normalized)]
        sentences = [
            s.strip() for s in _SENTENCE_SPLIT_RE.split(normalized) if s.strip()
        ]
        if not sentences and normalized:
            sentences = [normalized]
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", plain_text) if p.strip()]
        if not paragraphs and normalized:
            paragraphs = [normalized]
        return _PreparedText(
            source_text=text,
            plain_text=normalized,
            words=words,
            sentences=sentences,
            paragraphs=paragraphs,
        )

    def _build_text_meta(self, prepared: _PreparedText) -> TextMetaDTO:
        words_count = len(prepared.words)
        return TextMetaDTO(
            characters=len(prepared.plain_text),
            characters_no_spaces=len(prepared.plain_text.replace(" ", "")),
            words=words_count,
            sentences=len(prepared.sentences),
            paragraphs=len(prepared.paragraphs),
            reading_time_minutes=round(max(0.1, words_count / 200), 1),
        )

    def _to_plain_text(self, html: str) -> str:
        without_tags = _TAG_RE.sub(" ", html)
        return unescape(without_tags)

    def _prepare_punctuation_text(self, prepared: _PreparedText) -> str:
        text = prepared.plain_text
        text = _ABBREVIATION_RE.sub(" ABBR ", text)
        text = _DECIMAL_NUMBER_RE.sub(" NUM ", text)
        text = _NUMERIC_TOKEN_RE.sub(" NUM ", text)
        text = _LIST_MARKER_RE.sub(" ", text)
        return _WS_RE.sub(" ", text).strip()

    @staticmethod
    def _normalize_keyword(token: str) -> str:
        t = token.lower().strip("'\"-")
        if len(t) <= 3:
            return t

        ru_suffixes = (
            "иями",
            "ями",
            "ами",
            "иях",
            "его",
            "ого",
            "ему",
            "ому",
            "ыми",
            "ими",
            "ий",
            "ый",
            "ой",
            "ам",
            "ям",
            "ах",
            "ях",
            "ов",
            "ев",
            "ом",
            "ем",
            "ия",
            "ья",
            "ие",
            "ые",
            "ое",
            "ая",
            "яя",
            "ую",
            "юю",
            "ть",
            "ти",
            "ся",
            "сь",
            "а",
            "я",
            "ы",
            "и",
            "у",
            "ю",
            "е",
            "о",
        )
        for suffix in ru_suffixes:
            if t.endswith(suffix) and len(t) - len(suffix) >= 3:
                t = t[: -len(suffix)]
                break

        en_suffixes = ("ing", "edly", "ed", "es", "s", "ly")
        for suffix in en_suffixes:
            if t.endswith(suffix) and len(t) - len(suffix) >= 3:
                t = t[: -len(suffix)]
                break
        return t

    def score_readability(self, prepared: _PreparedText) -> MetricScoreDTO:
        words = prepared.words
        sentences = prepared.sentences or [prepared.plain_text]
        words_count = max(1, len(words))
        sentence_lengths = [len(_WORD_RE.findall(s)) for s in sentences]
        avg_sentence_len = sum(sentence_lengths) / max(1, len(sentence_lengths))
        long_sentence_ratio = sum(
            1 for length in sentence_lengths if length > 25
        ) / max(1, len(sentences))
        avg_word_len = sum(len(word) for word in words) / words_count
        complex_word_ratio = sum(1 for word in words if len(word) >= 8) / words_count

        penalty_asl = (
            0
            if 8 <= avg_sentence_len <= 18
            else (8 - avg_sentence_len) * 3.0
            if avg_sentence_len < 8
            else (avg_sentence_len - 18) * 2.5
        )
        penalty_asl = min(30.0, max(0.0, penalty_asl))
        penalty_lsr = min(25.0, max(0.0, (long_sentence_ratio - 0.20) * 120.0))
        penalty_cwr = min(25.0, max(0.0, (complex_word_ratio - 0.28) * 140.0))
        penalty_awl = (
            0
            if 4.5 <= avg_word_len <= 6.2
            else min(
                20.0,
                abs(avg_word_len - (4.5 if avg_word_len < 4.5 else 6.2)) * 8.0,
            )
        )
        score = round(
            _clamp(100.0 - penalty_asl - penalty_lsr - penalty_cwr - penalty_awl)
        )
        reasons = [
            "Средняя длина предложений в целевом диапазоне."
            if 8 <= avg_sentence_len <= 18
            else "Предложения заметно длиннее/короче оптимального диапазона.",
        ]
        suggestions = (
            []
            if score >= 80
            else ["Сократите длинные предложения и упростите сложные конструкции."]
        )
        return MetricScoreDTO(
            score=score,
            weight=self._WEIGHTS["readability"],
            status=_status_for_score(score),
            reasons=reasons,
            suggestions=suggestions,
            raw={
                "avg_sentence_len": round(avg_sentence_len, 2),
                "avg_word_len": round(avg_word_len, 2),
                "complex_word_ratio": round(complex_word_ratio, 4),
                "long_sentence_ratio": round(long_sentence_ratio, 4),
            },
        )

    def score_spam_words(self, prepared: _PreparedText) -> MetricScoreDTO:
        keyword_tokens = [
            self._normalize_keyword(token)
            for token in prepared.words
            if len(token) >= 3 and token not in _STOP_WORDS
        ]
        keyword_count = max(1, len(keyword_tokens))
        token_counts = Counter(keyword_tokens)

        repeated_token_excess = sum(
            max(0, count - 1) for count in token_counts.values()
        )
        spam_percent = repeated_token_excess * 100 / keyword_count

        top_keyword = ""
        top_keyword_count = 0
        if token_counts:
            top_keyword, top_keyword_count = token_counts.most_common(1)[0]
        top_keyword_share = top_keyword_count * 100 / keyword_count

        phrase_counts = Counter(pairwise(keyword_tokens))
        repeated_phrase_excess = sum(
            max(0, count - 1) for count in phrase_counts.values()
        )
        phrase_spam_percent = repeated_phrase_excess * 100 / keyword_count

        # SEO "classic nausea": sqrt(max repeat count of the top keyword).
        classic_nausea = top_keyword_count**0.5 if top_keyword_count > 0 else 0.0
        academic_nausea = (
            sum(count * count for count in token_counts.values()) / keyword_count
            if token_counts
            else 0.0
        )
        sample_scale = min(1.0, keyword_count / 80.0)

        base_score = _piecewise_linear(
            spam_percent,
            [
                (0.0, 100.0),
                (30.0, 100.0),
                (45.0, 70.0),
                (60.0, 35.0),
                (80.0, 0.0),
            ],
        )
        top_keyword_penalty = min(
            30.0, max(0.0, (top_keyword_share - 8.0) * 2.5) * sample_scale
        )
        phrase_penalty = min(
            25.0, max(0.0, (phrase_spam_percent - 6.0) * 3.0) * sample_scale
        )
        nausea_penalty = min(
            22.0, max(0.0, (classic_nausea - 3.5) * 6.0) * sample_scale
        )
        academic_penalty = min(
            18.0, max(0.0, (academic_nausea - 2.2) * 6.0) * sample_scale
        )
        score = round(
            _clamp(
                base_score
                - top_keyword_penalty
                - phrase_penalty
                - nausea_penalty
                - academic_penalty
            )
        )
        reasons = (
            ["Заспамленность и тошнота в безопасном диапазоне."]
            if spam_percent <= 30
            else ["Обнаружен переспам по повторяемости ключевых слов/фраз."]
        )
        suggestions = (
            []
            if score >= 80
            else [
                "Разбавьте повторяющиеся ключевые слова синонимами и перефразируйте "
                "часто повторяющиеся фразы."
            ]
        )
        return MetricScoreDTO(
            score=score,
            weight=self._WEIGHTS["spam_words"],
            status=_status_for_score(score),
            reasons=reasons,
            suggestions=suggestions,
            raw={
                "spam_percent": round(spam_percent, 2),
                "phrase_spam_percent": round(phrase_spam_percent, 2),
                "classic_nausea": round(classic_nausea, 2),
                "academic_nausea": round(academic_nausea, 2),
                "top_keyword": top_keyword,
                "top_keyword_count": top_keyword_count,
                "top_keyword_share_percent": round(top_keyword_share, 2),
                "keyword_count": keyword_count,
                "sample_scale": round(sample_scale, 3),
                "top_keyword_penalty": round(top_keyword_penalty, 2),
                "phrase_penalty": round(phrase_penalty, 2),
                "nausea_penalty": round(nausea_penalty, 2),
                "academic_penalty": round(academic_penalty, 2),
            },
        )

    def score_waterness(self, prepared: _PreparedText) -> MetricScoreDTO:
        words_count = max(1, len(prepared.words))
        unique_words = len(set(prepared.words))
        stopword_ratio = (
            sum(1 for token in prepared.words if token in _STOP_WORDS) / words_count
        )
        repetition_ratio = 1 - (unique_words / words_count)
        lexical_diversity = unique_words / words_count

        penalty_sr_hi = max(0.0, (stopword_ratio - 0.58) * 120.0)
        penalty_sr_lo = max(0.0, (0.40 - stopword_ratio) * 40.0)
        penalty_sr = min(35.0, penalty_sr_hi + penalty_sr_lo)
        penalty_rr = min(40.0, max(0.0, (repetition_ratio - 0.10) * 180.0))
        penalty_ld = min(30.0, max(0.0, (0.52 - lexical_diversity) * 120.0))
        score = round(_clamp(100.0 - penalty_sr - penalty_rr - penalty_ld))

        reasons = (
            ["Информационная плотность текста в норме."]
            if score >= 80
            else ["Есть повторы и лишние вводные конструкции."]
        )
        suggestions = (
            []
            if score >= 80
            else ["Уберите повторяющиеся обороты и замените общие фразы конкретикой."]
        )
        return MetricScoreDTO(
            score=score,
            weight=self._WEIGHTS["waterness"],
            status=_status_for_score(score),
            reasons=reasons,
            suggestions=suggestions,
            raw={
                "stopword_ratio": round(stopword_ratio, 4),
                "repetition_ratio": round(repetition_ratio, 4),
                "lexical_diversity": round(lexical_diversity, 4),
            },
        )

    def score_orthography(
        self,
        prepared: _PreparedText,
        lt_insights: _LanguageToolInsights | None = None,
    ) -> MetricScoreDTO:
        words_count = max(1, len(prepared.words))
        token_counts = Counter(prepared.words)
        near_duplicate_typos = self._near_duplicate_typo_candidates(token_counts)
        heuristic_mistakes = 0
        suspicious_examples: list[str] = []
        for token in prepared.words:
            if (
                _COMMON_RU_MISTAKES_RE.search(token)
                or _MIXED_ALPHABET_RE.fullmatch(token)
                or _TRIPLE_CHAR_RE.search(token)
                or token in near_duplicate_typos
            ):
                heuristic_mistakes += 1
                suspicious_examples.append(token)
        lt_mistakes = lt_insights.orthography_issues if lt_insights else 0
        spellchecker_mistakes = lt_insights.spellchecker_issues if lt_insights else 0
        mistakes = max(heuristic_mistakes, lt_mistakes, spellchecker_mistakes)
        errors_per_100_words = mistakes * 100 / words_count
        score = round(
            _clamp(
                _piecewise_linear(
                    errors_per_100_words,
                    [
                        (0.0, 100.0),
                        (0.2, 100.0),
                        (1.0, 65.0),
                        (3.0, 20.0),
                        (6.0, 0.0),
                    ],
                )
            )
        )
        reasons = (
            ["Орфографических аномалий почти нет."]
            if score >= 85
            else ["Найдены потенциальные орфографические ошибки."]
        )
        if lt_insights is not None:
            reasons.append("Учтены проверки локальных Python-библиотек.")
        suggestions = (
            []
            if score >= 85
            else [
                "Проверьте подозрительные слова через spell-checker перед публикацией."
            ]
        )
        return MetricScoreDTO(
            score=score,
            weight=self._WEIGHTS["orthography"],
            status=_status_for_score(score),
            reasons=reasons,
            suggestions=suggestions,
            raw={
                "mistakes": mistakes,
                "heuristic_mistakes": heuristic_mistakes,
                "languagetool_mistakes": lt_mistakes,
                "spellchecker_mistakes": spellchecker_mistakes,
                "mistakes_per_100_words": round(errors_per_100_words, 4),
                "examples": suspicious_examples[:8],
            },
        )

    def score_punctuation(
        self,
        prepared: _PreparedText,
        lt_insights: _LanguageToolInsights | None = None,
    ) -> MetricScoreDTO:
        text = self._prepare_punctuation_text(prepared)
        sentence_chunks = [
            s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()
        ]
        sentences_count = max(1, len(sentence_chunks))
        heuristic_issue_count = 0
        hard_anomalies = 0

        for regex in (
            _PUNCT_REPEAT_RE,
            _SPACE_BEFORE_PUNCT_RE,
            _NO_SPACE_AFTER_PUNCT_RE,
            _DOUBLE_COMMA_RE,
        ):
            matches = regex.findall(text)
            heuristic_issue_count += len(matches)

        if text.count("«") != text.count("»"):
            heuristic_issue_count += 1
            hard_anomalies += 1
        if text.count("(") != text.count(")"):
            heuristic_issue_count += 1
            hard_anomalies += 1
        hard_anomalies += len(re.findall(r"!!!+|\?\?\?+|!\?{2,}|\?!{2,}", text))
        lt_issue_count = lt_insights.punctuation_issues if lt_insights else 0
        issue_count = max(heuristic_issue_count, lt_issue_count)

        issues_per_100_sentences = issue_count * 100 / sentences_count
        base_score = _piecewise_linear(
            issues_per_100_sentences,
            [
                (0.0, 100.0),
                (2.0, 100.0),
                (8.0, 60.0),
                (20.0, 20.0),
                (40.0, 0.0),
            ],
        )
        hard_penalty = min(24.0, hard_anomalies * 6.0)
        score = round(_clamp(base_score - hard_penalty))
        reasons = (
            ["Пунктуация в целом аккуратная."]
            if score >= 80
            else ["Есть пунктуационные аномалии и спорные места."]
        )
        if lt_insights is not None:
            reasons.append("Учтены проверки локальных Python-библиотек.")
        suggestions = (
            []
            if score >= 80
            else ["Проверьте двойные запятые, пробелы перед знаками и баланс кавычек."]
        )
        return MetricScoreDTO(
            score=score,
            weight=self._WEIGHTS["punctuation"],
            status=_status_for_score(score),
            reasons=reasons,
            suggestions=suggestions,
            raw={
                "issues": issue_count,
                "heuristic_issues": heuristic_issue_count,
                "languagetool_issues": lt_issue_count,
                "issues_per_100_sentences": round(issues_per_100_sentences, 4),
                "hard_anomalies": hard_anomalies,
            },
        )

    def score_typos(self, prepared: _PreparedText) -> MetricScoreDTO:
        words_count = max(1, len(prepared.words))
        token_counts = Counter(prepared.words)
        near_duplicate_typos = self._near_duplicate_typo_candidates(token_counts)
        typo_candidates: list[str] = []
        for token in prepared.words:
            if len(token) < 4:
                continue
            if token in near_duplicate_typos:
                typo_candidates.append(token)
                continue
            if _MIXED_ALPHABET_RE.fullmatch(token):
                typo_candidates.append(token)
                continue
            if _TRIPLE_CHAR_RE.search(token):
                typo_candidates.append(token)
                continue
            if _CONSONANT_CLUSTER_RE.search(token):
                typo_candidates.append(token)

        typo_density = len(typo_candidates) * 100 / words_count
        repeat_typo_lemmas = len(
            {token for token in typo_candidates if token_counts[token] > 1}
        )
        base_score = _piecewise_linear(
            typo_density,
            [
                (0.0, 100.0),
                (0.15, 100.0),
                (0.8, 65.0),
                (2.0, 20.0),
                (4.0, 0.0),
            ],
        )
        repeat_penalty = min(12.0, repeat_typo_lemmas * 3.0)
        score = round(_clamp(base_score - repeat_penalty))
        reasons = (
            ["Опечаток почти нет."]
            if score >= 85
            else ["Есть токены, похожие на опечатки."]
        )
        suggestions = (
            []
            if score >= 85
            else ["Пройдитесь по словам с нетипичными буквенными паттернами."]
        )
        return MetricScoreDTO(
            score=score,
            weight=self._WEIGHTS["typos"],
            status=_status_for_score(score),
            reasons=reasons,
            suggestions=suggestions,
            raw={
                "typo_candidates": len(typo_candidates),
                "typos_per_100_words": round(typo_density, 4),
                "repeat_typo_lemmas": repeat_typo_lemmas,
                "examples": typo_candidates[:8],
            },
        )

    def score_clarity(self, prepared: _PreparedText) -> MetricScoreDTO:
        cliches = {"в рамках", "на сегодняшний день", "имеет место", "в целом"}
        text_l = prepared.plain_text.lower()
        hits = sum(text_l.count(pattern) for pattern in cliches)
        score = round(_clamp(100 - hits * 8))
        return MetricScoreDTO(
            score=score,
            weight=0.0,
            status=_status_for_score(score),
            reasons=["Чем меньше штампов и канцелярита, тем выше оценка."],
            suggestions=(
                [] if score >= 80 else ["Упростите канцелярские формулировки."]
            ),
            raw={"cliche_hits": hits},
        )

    def score_structure(
        self,
        prepared: _PreparedText,
        content_format: str,
    ) -> MetricScoreDTO:
        paragraphs = len(prepared.paragraphs)
        long_paragraphs = sum(
            1 for p in prepared.paragraphs if len(_WORD_RE.findall(p)) > 120
        )
        heading_hits = 0
        list_hits = 0
        if content_format == "html":
            heading_hits = len(
                re.findall(r"<h[1-6][^>]*>", prepared.source_text, re.IGNORECASE)
            )
            list_hits = len(
                re.findall(r"<(?:ul|ol)[^>]*>", prepared.source_text, re.IGNORECASE)
            )
        penalty = 0.0
        if paragraphs <= 1:
            penalty += 25
        penalty += min(35.0, long_paragraphs * 10.0)
        if heading_hits == 0 and len(prepared.words) > 450:
            penalty += 15
        score = round(_clamp(100.0 - penalty))
        return MetricScoreDTO(
            score=score,
            weight=0.0,
            status=_status_for_score(score),
            reasons=[
                "Оценка структуры зависит от длины абзацев и наличия визуальных опор."
            ],
            suggestions=(
                []
                if score >= 80
                else ["Добавьте подзаголовки и разделите длинные блоки текста."]
            ),
            raw={
                "paragraphs": paragraphs,
                "long_paragraphs": long_paragraphs,
                "headings_count": heading_hits,
                "lists_count": list_hits,
            },
        )

    def compute_overall(self, scores: dict[str, MetricScoreDTO]) -> OverallScoreDTO:
        weighted_metrics = list(self._WEIGHTS.keys())
        total = 0.0
        for metric in weighted_metrics:
            total += scores[metric].score * self._WEIGHTS[metric]
        final_score = round(_clamp(total))
        top_issues = [
            metric.replace("_", " ")
            for metric in weighted_metrics
            if scores[metric].score < 70
        ][:3]
        if final_score >= 85:
            hint = "Текст выглядит качественным, можно публиковать."
        elif final_score >= 70:
            hint = "Нужна легкая вычитка перед публикацией."
        else:
            hint = "Рекомендуется заметная редактура до публикации."
        return OverallScoreDTO(
            score=final_score,
            grade=_grade_for_score(final_score),
            status=_status_for_score(final_score),
            formula="weighted_mean",
            weights_sum=1.0,
            weighted_metrics=weighted_metrics,
            top_issues=top_issues,
            editor_hint=hint,
        )
