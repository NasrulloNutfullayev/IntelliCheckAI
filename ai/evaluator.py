from __future__ import annotations

import math
import os
import re
from functools import lru_cache
from typing import Any

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None


MODEL_NAME = os.getenv("INTELLICHECK_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
AI_COPY_THRESHOLD = 78.0


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\u0400-\u04ff\u0100-\u017f\u2018\u2019'` -]+", " ", text)
    return re.sub(r"\s+", " ", text)


def _tokenize(text: str) -> list[str]:
    return [token for token in _normalize_text(text).split() if len(token) > 1]


def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(vector_a, vector_b))
    denominator_a = math.sqrt(sum(a * a for a in vector_a))
    denominator_b = math.sqrt(sum(b * b for b in vector_b))
    if denominator_a == 0 or denominator_b == 0:
        return 0.0
    return numerator / (denominator_a * denominator_b)


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer | None:
    if SentenceTransformer is None:
        return None
    try:
        return SentenceTransformer(MODEL_NAME)
    except Exception:
        return None


def _semantic_similarity(answer: str, question_text: str, reference_answer: str) -> float:
    model = _load_model()
    normalized_answer = _normalize_text(answer)
    target_text = _normalize_text(f"{question_text} {reference_answer}")
    if not normalized_answer or not target_text:
        return 0.0

    if model is None:
        return _fallback_semantic_similarity(normalized_answer, target_text)

    answer_embedding = model.encode(normalized_answer, normalize_embeddings=True)
    target_embedding = model.encode(target_text, normalize_embeddings=True)
    return max(0.0, min(float(_cosine_similarity(answer_embedding.tolist(), target_embedding.tolist())), 1.0))


def _fallback_semantic_similarity(answer: str, target_text: str) -> float:
    answer_tokens = set(_tokenize(answer))
    target_tokens = set(_tokenize(target_text))
    if not answer_tokens or not target_tokens:
        return 0.0
    return len(answer_tokens & target_tokens) / len(answer_tokens | target_tokens)


def _concept_coverage(answer: str, keywords: list[str], reference_answer: str, question_text: str) -> float:
    normalized_answer = _normalize_text(answer)
    concepts = [
        _normalize_text(term)
        for term in [*keywords, *_extract_reference_concepts(reference_answer or question_text)]
        if _normalize_text(term)
    ]
    unique_concepts = list(dict.fromkeys(concepts))
    if not unique_concepts:
        return 1.0
    matches = sum(1 for concept in unique_concepts if concept in normalized_answer)
    return matches / len(unique_concepts)


def _extract_reference_concepts(reference_answer: str) -> list[str]:
    return [token for token in _tokenize(reference_answer) if len(token) > 4][:8]


def _completeness_score(answer: str, minimum_words: int) -> float:
    if minimum_words <= 0:
        return 1.0
    return min(len(_tokenize(answer)) / minimum_words, 1.0)


def _sentence_balance_score(answer: str) -> float:
    sentences = [part.strip() for part in re.split(r"[.!?]+", answer) if part.strip()]
    if len(sentences) < 2:
        return 0.25
    lengths = [len(_tokenize(sentence)) for sentence in sentences]
    average = sum(lengths) / len(lengths)
    variance = sum((length - average) ** 2 for length in lengths) / len(lengths)
    normalized = 1 - min(variance / 20, 1)
    return max(0.0, normalized)


def _llm_phrase_score(answer: str) -> float:
    patterns = [
        "xulosa qilib aytganda",
        "umuman olganda",
        "shu sababli",
        "bundan tashqari",
        "demak",
        "yakuniy qilib",
    ]
    normalized_answer = _normalize_text(answer)
    matches = sum(1 for pattern in patterns if pattern in normalized_answer)
    return min(matches / 3, 1.0)


def _ai_copy_risk(answer: str, semantic: float, completeness: float) -> float:
    token_count = len(_tokenize(answer))
    length_signal = min(token_count / 120, 1.0)
    sentence_balance = _sentence_balance_score(answer)
    llm_phrase_signal = _llm_phrase_score(answer)

    risk = (
        semantic * 0.55
        + length_signal * 0.15
        + sentence_balance * 0.15
        + llm_phrase_signal * 0.15
    ) * 100
    if completeness < 0.45:
        risk *= 0.7
    return round(max(0.0, min(risk, 100.0)), 2)


def _feedback(score: float, semantic: float, coverage: float, completeness: float) -> str:
    points = []
    if semantic >= 0.75:
        points.append("mazmun savolga yaqin")
    elif semantic < 0.5:
        points.append("asosiy mazmun sust")

    if coverage >= 0.65:
        points.append("asosiy tushunchalar bor")
    elif coverage < 0.4:
        points.append("kalit tushunchalar yetishmaydi")

    if completeness < 0.6:
        points.append("javob qisqa")
    elif completeness >= 0.9:
        points.append("javob yetarlicha to'liq")

    if score >= 85:
        return "Javob yaxshi baholandi: " + ", ".join(points or ["mazmun aniq va to'liq"]) + "."
    if score >= 60:
        return "Javob o'rtacha baholandi: " + ", ".join(points or ["ba'zi joylari yaxshi, ba'zilari sust"]) + "."
    return "Javob past baholandi: " + ", ".join(points or ["savol yetarli yoritilmagan"]) + "."


def evaluate_answer(answer: str, question_text: str, reference_answer: str, rubric: dict[str, Any]) -> dict[str, Any]:
    weights = rubric.get("weights", {})
    semantic_weight = float(weights.get("semantic", 0.7))
    coverage_weight = float(weights.get("coverage", 0.2))
    completeness_weight = float(weights.get("completeness", 0.1))
    total_weight = semantic_weight + coverage_weight + completeness_weight
    if total_weight <= 0:
        semantic_weight, coverage_weight, completeness_weight, total_weight = 0.7, 0.2, 0.1, 1.0

    semantic = _semantic_similarity(answer, question_text, reference_answer)
    coverage = _concept_coverage(answer, rubric.get("keywords", []), reference_answer, question_text)
    completeness = _completeness_score(answer, int(rubric.get("minimum_words", 25)))
    ai_copy_risk = _ai_copy_risk(answer, semantic, completeness)
    ai_copy_flag = ai_copy_risk >= AI_COPY_THRESHOLD

    if ai_copy_flag:
        return {
            "score": 0.0,
            "feedback": "Javob AI dan ko'chirilgan bo'lishi mumkin. Tekshirish to'xtatildi.",
            "breakdown": {
                "mazmun_mosligi": round(semantic * 100, 2),
                "tushuncha_qamrovi": round(coverage * 100, 2),
                "toliqlik": round(completeness * 100, 2),
                "ai_copy_risk": ai_copy_risk,
            },
            "ai_copy_risk": ai_copy_risk,
            "ai_copy_flag": True,
        }

    raw_score = (
        semantic * semantic_weight
        + coverage * coverage_weight
        + completeness * completeness_weight
    ) / total_weight
    score = round(max(0.0, min(raw_score * 100, 100.0)), 2)

    return {
        "score": score,
        "feedback": _feedback(score, semantic, coverage, completeness),
        "breakdown": {
            "mazmun_mosligi": round(semantic * 100, 2),
            "tushuncha_qamrovi": round(coverage * 100, 2),
            "toliqlik": round(completeness * 100, 2),
            "ai_copy_risk": ai_copy_risk,
        },
        "ai_copy_risk": ai_copy_risk,
        "ai_copy_flag": False,
    }
