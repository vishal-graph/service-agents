"""
Aadhya – Voice Response Optimizer
Rewrites Gemini responses for voice (Vapi + ElevenLabs TTS).
Strips markdown, enforces 60-token limit, single question only.
"""
from __future__ import annotations
import re


def optimize_for_voice(text: str) -> str:
    """
    Clean and optimize a text response for spoken TTS delivery.
    """
    text = _strip_markdown(text)
    text = _ensure_single_question(text)
    text = _add_natural_pauses(text)
    text = _trim_to_token_limit(text, max_words=65)
    return text.strip()


def _strip_markdown(text: str) -> str:
    """Remove all markdown formatting."""
    # Remove headers
    text = re.sub(r"#{1,6}\s+", "", text)
    # Remove bold/italic
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
    # Remove bullet/numbered lists — convert to prose
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    # Remove emojis (basic unicode range)
    text = re.sub(
        r"[\U0001F300-\U0001F9FF\U00002600-\U000027BF]", "", text
    )
    # Replace multiple newlines with a space
    text = re.sub(r"\n+", " ", text)
    # Collapse multiple spaces
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _ensure_single_question(text: str) -> str:
    """
    If multiple questions exist, keep only the first one.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    questions = [s for s in sentences if "?" in s]
    non_questions = [s for s in sentences if "?" not in s]

    if len(questions) <= 1:
        return text  # Already fine

    # Keep all non-questions + only the last (most important) question
    result_sentences = non_questions + [questions[-1]]
    return " ".join(result_sentences)


def _add_natural_pauses(text: str) -> str:
    """
    Add a soft pause before questions for natural TTS phrasing.
    """
    # Add pause before question words at mid-sentence
    text = re.sub(r"([a-z])\. (Could|Would|Can|May|What|Which|Who|How|When|Where)", r"\1, \2", text)
    return text


def _trim_to_token_limit(text: str, max_words: int = 65) -> str:
    """
    Trim to approximately max_words words at a sentence boundary.
    """
    words = text.split()
    if len(words) <= max_words:
        return text

    # Find last sentence boundary within limit
    truncated = " ".join(words[:max_words])
    # Try to cut at last sentence boundary
    last_sentence_end = max(
        truncated.rfind(". "),
        truncated.rfind("? "),
        truncated.rfind("! "),
    )
    if last_sentence_end > len(truncated) // 2:
        return truncated[:last_sentence_end + 1].strip()

    # Fallback: cut at word boundary and add ellipsis
    return truncated.rsplit(" ", 1)[0] + "."
