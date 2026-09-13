"""Code point ranges used to classify emoji sequence members.

This is a hand-picked subset of the ranges in Unicode's emoji-data.txt
(Extended_Pictographic, Emoji_Modifier, and the regional indicator
block), not the full generated table. It covers the emoji blocks
people actually type day to day: emoticons, symbols, transport, the
supplemental pictograph blocks, flags. Rare additions from newer
Unicode versions may fall outside these ranges until the table is
regenerated from the real data files (see README roadmap).
"""

# Kept in ascending order by start so is_extended_pictographic can
# stop scanning as soon as it passes the code point.
_PICTOGRAPHIC_RANGES = (
    (0x00A9, 0x00A9),
    (0x00AE, 0x00AE),
    (0x203C, 0x203C),
    (0x2049, 0x2049),
    (0x2122, 0x2122),
    (0x2139, 0x2139),
    (0x2194, 0x21AA),
    (0x231A, 0x231B),
    (0x2328, 0x2328),
    (0x23E9, 0x23FA),
    (0x24C2, 0x24C2),
    (0x25AA, 0x25FE),
    (0x2600, 0x27BF),
    (0x2934, 0x2935),
    (0x2B00, 0x2BFF),
    (0x3030, 0x3030),
    (0x303D, 0x303D),
    (0x3297, 0x3297),
    (0x3299, 0x3299),
    (0x1F000, 0x1F0FF),
    (0x1F100, 0x1F1FF),
    (0x1F200, 0x1F2FF),
    (0x1F300, 0x1FAFF),
)

_MODIFIER_RANGE = (0x1F3FB, 0x1F3FF)
_REGIONAL_INDICATOR_RANGE = (0x1F1E6, 0x1F1FF)

# Tag sequences (UTS #51) spell out an ASCII-derived string using the
# code points at 0xE0000 + ord(ascii_char). 0xE0020-0xE007E covers the
# printable ASCII range used for subdivision codes like "gbeng"; 0xE007F
# is the fixed cancel tag that ends the sequence.
_TAG_SPEC_RANGE = (0xE0020, 0xE007E)
TAG_TERMINATOR = chr(0xE007F)


def is_extended_pictographic(ch: str) -> bool:
    cp = ord(ch)
    for start, end in _PICTOGRAPHIC_RANGES:
        if cp < start:
            break
        if cp <= end:
            return True
    return False


def is_emoji_modifier(ch: str) -> bool:
    cp = ord(ch)
    return _MODIFIER_RANGE[0] <= cp <= _MODIFIER_RANGE[1]


def is_regional_indicator(ch: str) -> bool:
    cp = ord(ch)
    return _REGIONAL_INDICATOR_RANGE[0] <= cp <= _REGIONAL_INDICATOR_RANGE[1]


def is_tag_spec_char(ch: str) -> bool:
    cp = ord(ch)
    return _TAG_SPEC_RANGE[0] <= cp <= _TAG_SPEC_RANGE[1]
