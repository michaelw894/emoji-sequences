"""Streaming scanner that splits text into emoji sequences and plain runs.

An "emoji sequence" here means what UTS #51 calls it: a base emoji
optionally followed by a variation selector or skin tone modifier, a
chain of ZWJ-joined emoji (families, professions, ...), a pair of
regional indicators (flags), a keycap sequence (digit/#/* + VS16 +
combining enclosing keycap), or a tag sequence (a base emoji plus tag
characters and a cancel tag, e.g. the England flag). Treating these as
one unit matters because naive code-point-by-code-point handling
splits a single visual emoji into several "characters", which breaks
counting, truncation, and search.

The scanner never buffers more than a bounded amount of state: at most
one pending emoji sequence, a small pushback stack (at most a couple of
characters), and a plain-text run that gets flushed once it crosses
_TEXT_CHUNK_LIMIT. That's what makes scan() safe to point at arbitrarily
large input.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, List, Optional

from ._ranges import (
    TAG_TERMINATOR,
    is_emoji_modifier,
    is_extended_pictographic,
    is_regional_indicator,
    is_tag_spec_char,
)

ZWJ = "‍"
VARIATION_SELECTOR_16 = "️"
KEYCAP = "⃣"

# Flush accumulated plain text at this size even if no emoji has been
# seen yet, so a long run of ordinary text can't grow the buffer
# without bound.
_TEXT_CHUNK_LIMIT = 4096


@dataclass(frozen=True)
class Token:
    text: str
    is_emoji: bool


def _iter_codepoints(chunks: Iterable[str]) -> Iterator[str]:
    for chunk in chunks:
        for ch in chunk:
            yield ch


class SequenceScanner:
    def __init__(self, chars: Iterator[str]):
        self._chars = chars
        self._pushback: List[str] = []

    def _next(self) -> Optional[str]:
        if self._pushback:
            return self._pushback.pop()
        return next(self._chars, None)

    def _push_back(self, ch: str) -> None:
        self._pushback.append(ch)

    def tokens(self) -> Iterator[Token]:
        text_buf: List[str] = []

        def flush() -> Optional[Token]:
            if not text_buf:
                return None
            tok = Token("".join(text_buf), is_emoji=False)
            text_buf.clear()
            return tok

        while True:
            ch = self._next()
            if ch is None:
                break

            if is_regional_indicator(ch) or is_extended_pictographic(ch):
                tok = flush()
                if tok is not None:
                    yield tok
                yield Token(self._read_sequence(ch), is_emoji=True)
            elif ch.isdigit() or ch in ("#", "*"):
                seq = self._try_keycap(ch)
                if seq is not None:
                    tok = flush()
                    if tok is not None:
                        yield tok
                    yield Token(seq, is_emoji=True)
                else:
                    text_buf.append(ch)
            else:
                text_buf.append(ch)

            if len(text_buf) >= _TEXT_CHUNK_LIMIT:
                tok = flush()
                if tok is not None:
                    yield tok

        tok = flush()
        if tok is not None:
            yield tok

    def _try_keycap(self, first: str) -> Optional[str]:
        second = self._next()
        if second == VARIATION_SELECTOR_16:
            third = self._next()
            if third == KEYCAP:
                return first + second + third
            if third is not None:
                self._push_back(third)
            self._push_back(second)
            return None
        if second == KEYCAP:
            return first + second
        if second is not None:
            self._push_back(second)
        return None

    def _read_tag_spec(self, first: str) -> Optional[str]:
        # A tag sequence is tag_base tag_spec_char+ TAG_TERMINATOR. If we
        # run out of input or hit a non-spec character before the
        # terminator, it isn't one - push everything back so the caller
        # can reprocess it as plain text.
        consumed = [first]
        while True:
            nxt = self._next()
            if nxt is None:
                break
            consumed.append(nxt)
            if nxt == TAG_TERMINATOR:
                return "".join(consumed)
            if not is_tag_spec_char(nxt):
                break
        for ch in reversed(consumed):
            self._push_back(ch)
        return None

    def _read_sequence(self, first: str) -> str:
        # Flags are exactly two regional indicators, never more.
        if is_regional_indicator(first):
            seq = [first]
            second = self._next()
            if second is not None and is_regional_indicator(second):
                seq.append(second)
            elif second is not None:
                self._push_back(second)
            return "".join(seq)

        seq = [first]
        while True:
            nxt = self._next()
            if nxt is None:
                break
            if nxt == VARIATION_SELECTOR_16 or is_emoji_modifier(nxt):
                seq.append(nxt)
                continue
            if is_tag_spec_char(nxt):
                tag = self._read_tag_spec(nxt)
                if tag is not None:
                    seq.append(tag)
                break
            if nxt == ZWJ:
                after = self._next()
                if after is not None and (
                    is_extended_pictographic(after) or is_regional_indicator(after)
                ):
                    seq.append(nxt)
                    seq.append(after)
                    continue
                if after is not None:
                    self._push_back(after)
                self._push_back(nxt)
                break
            self._push_back(nxt)
            break
        return "".join(seq)


def scan(chunks: Iterable[str]) -> Iterator[Token]:
    """Scan an iterable of text chunks, yielding Tokens lazily.

    `chunks` can be any iterable of strings, in order - chunk
    boundaries don't need to line up with sequence boundaries. This is
    what makes it possible to feed scan() a generator that reads a
    file a few KB at a time instead of a single giant string.
    """
    return SequenceScanner(_iter_codepoints(chunks)).tokens()


def scan_text(text: str) -> Iterator[Token]:
    """Convenience wrapper for scanning a single in-memory string."""
    return scan((text,))


def iter_file(path: str, chunk_size: int = 65536) -> Iterator[Token]:
    """Scan a text file on disk without reading it into memory at once."""

    def _chunks() -> Iterator[str]:
        with open(path, "r", encoding="utf-8") as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    return
                yield data

    return scan(_chunks())
