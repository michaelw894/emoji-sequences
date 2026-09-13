import os
import tempfile
import unittest

from emoji_sequences import Token, iter_file, scan, scan_text

FAMILY = "\U0001F468‍\U0001F469‍\U0001F467‍\U0001F466"
HEART_ON_FIRE = "❤️‍\U0001F525"
CANADA_FLAG = "\U0001F1E8\U0001F1E6"
THUMBS_UP_MEDIUM = "\U0001F44D\U0001F3FD"
KEYCAP_ONE = "1️⃣"
KEYCAP_HASH_NO_VS = "#⃣"
ENGLAND_FLAG = (
    "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F"
)


def tokens_of(text):
    return list(scan_text(text))


class ZwjChainTests(unittest.TestCase):
    def test_family_is_one_token(self):
        self.assertEqual(tokens_of(FAMILY), [Token(FAMILY, is_emoji=True)])

    def test_chain_starting_with_variation_selector(self):
        self.assertEqual(
            tokens_of(HEART_ON_FIRE), [Token(HEART_ON_FIRE, is_emoji=True)]
        )

    def test_zwj_not_followed_by_emoji_breaks_the_chain(self):
        text = "\U0001F468‍x"
        self.assertEqual(
            tokens_of(text),
            [
                Token("\U0001F468", is_emoji=True),
                Token("‍x", is_emoji=False),
            ],
        )

    def test_trailing_zwj_at_end_of_input_is_plain_text(self):
        text = "\U0001F468‍"
        self.assertEqual(
            tokens_of(text),
            [
                Token("\U0001F468", is_emoji=True),
                Token("‍", is_emoji=False),
            ],
        )


class FlagTests(unittest.TestCase):
    def test_flag_is_one_token(self):
        self.assertEqual(tokens_of(CANADA_FLAG), [Token(CANADA_FLAG, is_emoji=True)])

    def test_lone_regional_indicator_is_its_own_token(self):
        text = "\U0001F1E8x"
        self.assertEqual(
            tokens_of(text),
            [
                Token("\U0001F1E8", is_emoji=True),
                Token("x", is_emoji=False),
            ],
        )

    def test_flag_embedded_in_plain_text(self):
        text = "go " + CANADA_FLAG + " team"
        self.assertEqual(
            tokens_of(text),
            [
                Token("go ", is_emoji=False),
                Token(CANADA_FLAG, is_emoji=True),
                Token(" team", is_emoji=False),
            ],
        )


class ModifierTests(unittest.TestCase):
    def test_skin_tone_modifier_attaches_to_base(self):
        self.assertEqual(
            tokens_of(THUMBS_UP_MEDIUM), [Token(THUMBS_UP_MEDIUM, is_emoji=True)]
        )


class KeycapTests(unittest.TestCase):
    def test_digit_vs16_keycap(self):
        self.assertEqual(tokens_of(KEYCAP_ONE), [Token(KEYCAP_ONE, is_emoji=True)])

    def test_hash_keycap_without_variation_selector(self):
        self.assertEqual(
            tokens_of(KEYCAP_HASH_NO_VS), [Token(KEYCAP_HASH_NO_VS, is_emoji=True)]
        )

    def test_digit_without_keycap_suffix_is_plain_text(self):
        self.assertEqual(tokens_of("42"), [Token("42", is_emoji=False)])

    def test_digit_followed_by_vs16_but_no_keycap(self):
        text = "1️x"
        self.assertEqual(tokens_of(text), [Token(text, is_emoji=False)])


class TagSequenceTests(unittest.TestCase):
    def test_subdivision_flag_is_one_token(self):
        self.assertEqual(
            tokens_of(ENGLAND_FLAG), [Token(ENGLAND_FLAG, is_emoji=True)]
        )

    def test_tag_sequence_embedded_in_plain_text(self):
        text = "go " + ENGLAND_FLAG + " team"
        self.assertEqual(
            tokens_of(text),
            [
                Token("go ", is_emoji=False),
                Token(ENGLAND_FLAG, is_emoji=True),
                Token(" team", is_emoji=False),
            ],
        )

    def test_tag_sequence_split_across_chunks(self):
        chunks = [ENGLAND_FLAG[:1], ENGLAND_FLAG[1:4], ENGLAND_FLAG[4:]]
        self.assertEqual(list(scan(chunks)), [Token(ENGLAND_FLAG, is_emoji=True)])

    def test_unterminated_tag_sequence_falls_back_to_plain_text(self):
        text = "\U0001F3F4\U000E0067\U000E0062x"
        self.assertEqual(
            tokens_of(text),
            [
                Token("\U0001F3F4", is_emoji=True),
                Token("\U000E0067\U000E0062x", is_emoji=False),
            ],
        )

    def test_tag_sequence_cut_off_at_end_of_input(self):
        text = "\U0001F3F4\U000E0067\U000E0062"
        self.assertEqual(
            tokens_of(text),
            [
                Token("\U0001F3F4", is_emoji=True),
                Token("\U000E0067\U000E0062", is_emoji=False),
            ],
        )


class PlainTextTests(unittest.TestCase):
    def test_no_emoji_is_a_single_token(self):
        self.assertEqual(tokens_of("just words"), [Token("just words", is_emoji=False)])

    def test_mixed_text_and_emoji(self):
        text = "Great job team! " + FAMILY + CANADA_FLAG + " " + KEYCAP_ONE
        self.assertEqual(
            tokens_of(text),
            [
                Token("Great job team! ", is_emoji=False),
                Token(FAMILY, is_emoji=True),
                Token(CANADA_FLAG, is_emoji=True),
                Token(" ", is_emoji=False),
                Token(KEYCAP_ONE, is_emoji=True),
            ],
        )


class ChunkBoundaryTests(unittest.TestCase):
    def test_zwj_chain_split_across_chunks(self):
        chunks = [FAMILY[:2], FAMILY[2:5], FAMILY[5:]]
        self.assertEqual(list(scan(chunks)), [Token(FAMILY, is_emoji=True)])

    def test_flag_split_between_the_two_regional_indicators(self):
        chunks = [CANADA_FLAG[:1], CANADA_FLAG[1:]]
        self.assertEqual(list(scan(chunks)), [Token(CANADA_FLAG, is_emoji=True)])

    def test_keycap_split_between_every_code_point(self):
        chunks = list(KEYCAP_ONE)
        self.assertEqual(list(scan(chunks)), [Token(KEYCAP_ONE, is_emoji=True)])

    def test_plain_text_split_mid_run_is_reassembled(self):
        chunks = ["hello ", "wor", "ld"]
        self.assertEqual(list(scan(chunks)), [Token("hello world", is_emoji=False)])

    def test_text_chunk_limit_flushes_long_plain_runs_in_pieces(self):
        from emoji_sequences.scanner import _TEXT_CHUNK_LIMIT

        text = "a" * (_TEXT_CHUNK_LIMIT * 2 + 5)
        result = list(scan_text(text))
        self.assertTrue(all(not tok.is_emoji for tok in result))
        self.assertEqual("".join(tok.text for tok in result), text)
        self.assertGreaterEqual(len(result), 2)
        for tok in result[:-1]:
            self.assertEqual(len(tok.text), _TEXT_CHUNK_LIMIT)


class IterFileTests(unittest.TestCase):
    def test_iter_file_matches_scan_text(self):
        text = "hi " + FAMILY + " " + KEYCAP_ONE + " bye"
        fd, path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            self.assertEqual(list(iter_file(path, chunk_size=3)), tokens_of(text))
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
