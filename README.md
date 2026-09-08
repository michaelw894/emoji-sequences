# emoji-sequences

Split text into runs of plain text and single emoji sequences, streaming
from files or iterables instead of requiring the whole input in memory.

## The problem

A single emoji you see on screen is often several Unicode code points
underneath. A thumbs-up with a skin tone is a base emoji plus a
modifier. A family is four emoji joined with zero-width joiners. A
flag is a pair of regional indicator letters. If you slice text by
code point, or even by `len()`, you can split one of these in half and
end up with mojibake or a broken character on either side of the cut.

Doing this correctly also usually means loading the whole string into
memory first, which doesn't work if you're processing a large export
(chat logs, tweet dumps, CSVs of comments) that doesn't comfortably
fit. This library scans as it goes: you feed it chunks or a file path
and it yields tokens as soon as it has enough lookahead to know where
one ends, never materializing more than one chunk plus a couple of
characters at a time.

## Usage

```python
from emoji_sequences import scan_text

for token in scan_text("Great job team! 👨‍👩‍👧‍👦🇨🇦 1️⃣"):
    print(token.is_emoji, repr(token.text))
```

```
False 'Great job team! '
True '👨‍👩‍👧‍👦'
True '🇨🇦'
False ' '
True '1️⃣'
```

Streaming a large file without loading it all into memory:

```python
from emoji_sequences import iter_file

emoji_count = 0
for token in iter_file("chat_export.txt"):
    if token.is_emoji:
        emoji_count += 1

print(emoji_count)
```

`iter_file` reads the file in fixed-size chunks (64 KB by default) and
`scan` will happily take any iterable of string chunks, so you can wire
it up to a socket, a decompressed stream, or anything else that hands
you text incrementally:

```python
from emoji_sequences import scan

def read_in_chunks(fileobj, size=8192):
    while True:
        data = fileobj.read(size)
        if not data:
            return
        yield data

with open("big.txt", encoding="utf-8") as f:
    for token in scan(read_in_chunks(f)):
        ...
```

## What counts as one sequence

- A base emoji, optionally followed by a variation selector or a skin
  tone modifier (`👍🏽`).
- A chain of emoji joined by zero-width joiners (`👨‍👩‍👧‍👦`, `❤️‍🔥`).
- A pair of regional indicator letters, i.e. a flag (`🇨🇦`).
- A keycap sequence: digit or `#`/`*`, optional variation selector,
  combining enclosing keycap (`1️⃣`).

## Known limitations

The table in `_ranges.py` classifying which code points can start or
continue a sequence is a hand-picked subset of Unicode's emoji data,
not the generated table from the official files. It covers the emoji
in common use but will miss some newer or obscure ones. Tag sequences
(subdivision flags like the England flag) aren't recognized yet either.

## Installing

No dependencies beyond the standard library. Install locally for
development with:

```
pip install -e .
```
