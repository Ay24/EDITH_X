"""M8 — Information-Density Prompt Compressor (Reverse-Engineered from LLMLingua)."""
from __future__ import annotations

import re
from edith_x.core.interfaces import CompressedPrompt

# Common boilerplate phrases that consume tokens without information
FILLER_PATTERNS = [
    re.compile(r"\bplease note that\b", re.IGNORECASE),
    re.compile(r"\bit is important to remember that\b", re.IGNORECASE),
    re.compile(r"\bas previously mentioned\b", re.IGNORECASE),
    re.compile(r"\bin addition to this\b", re.IGNORECASE),
    re.compile(r"\bfurthermore\b,?", re.IGNORECASE),
    re.compile(r"\bmoreover\b,?", re.IGNORECASE),
    re.compile(r"\bneedless to say\b,?", re.IGNORECASE),
    re.compile(r"\bas a matter of fact\b,?", re.IGNORECASE),
    re.compile(r"\bat the end of the day\b,?", re.IGNORECASE),
    re.compile(r"\bit should be noted that\b", re.IGNORECASE),
    re.compile(r"\bfor the purpose of\b", re.IGNORECASE),
]


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.3))


class InformationDensityCompressor:
    """Coarse-to-fine token compressor preserving technical information & code."""

    def compress(self, prompt: str, budget: int) -> CompressedPrompt:
        original_tokens = _estimate_tokens(prompt)
        if original_tokens <= budget:
            return CompressedPrompt(
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compressed_text=prompt,
                compression_ratio=1.0,
            )

        # Stage 1: Strip structural and polite filler phrases
        cleaned = prompt
        for pattern in FILLER_PATTERNS:
            cleaned = pattern.sub("", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        cleaned_tokens = _estimate_tokens(cleaned)
        if cleaned_tokens <= budget:
            return CompressedPrompt(
                original_tokens=original_tokens,
                compressed_tokens=cleaned_tokens,
                compressed_text=cleaned,
                compression_ratio=cleaned_tokens / original_tokens,
            )

        # Stage 2: Sentence-Level Density Ranking (indexed to avoid duplicate sentence expansion)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
        scored_sentences: list[tuple[float, int, str]] = []

        for idx, s in enumerate(sentences):
            # Score sentences based on numbers, code, identifiers, technical terms
            numbers_count = len(re.findall(r"\b\d+\b", s))
            code_markers = len(re.findall(r"[`_{}\[\]:=]", s))
            words = s.split()
            density = (numbers_count * 2.0 + code_markers * 1.5 + len(words)) / max(len(words), 1)
            scored_sentences.append((density, idx, s))

        # Sort descending by information density
        scored_sentences.sort(key=lambda x: x[0], reverse=True)

        selected_indices: set[int] = set()
        token_count = 0
        for _, idx, s in scored_sentences:
            s_tokens = _estimate_tokens(s)
            if token_count + s_tokens <= budget or not selected_indices:
                selected_indices.add(idx)
                token_count += s_tokens
            if token_count >= budget:
                break

        # Re-order strictly by original sentence sequence
        final_sentences = [s for idx, s in enumerate(sentences) if idx in selected_indices]
        compressed_text = " ".join(final_sentences)
        final_tokens = _estimate_tokens(compressed_text)

        return CompressedPrompt(
            original_tokens=original_tokens,
            compressed_tokens=final_tokens,
            compressed_text=compressed_text,
            compression_ratio=final_tokens / max(original_tokens, 1),
        )
