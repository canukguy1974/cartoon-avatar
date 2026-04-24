from unittest import TestCase

from app.services.sentence_service import split_sentences


class SentenceSplittingTests(TestCase):
    def test_single_sentence(self) -> None:
        self.assertEqual(split_sentences("Hello there."), ["Hello there."])

    def test_multiple_sentences(self) -> None:
        result = split_sentences("Hello there. How are you? I am fine!")
        self.assertEqual(result, ["Hello there.", "How are you?", "I am fine!"])

    def test_empty_string_returns_empty_list(self) -> None:
        self.assertEqual(split_sentences(""), [])
        self.assertEqual(split_sentences("   "), [])

    def test_none_returns_empty_list(self) -> None:
        self.assertEqual(split_sentences(None), [])

    def test_no_terminating_punctuation(self) -> None:
        result = split_sentences("Hello there")
        self.assertEqual(result, ["Hello there"])

    def test_abbreviation_does_not_split(self) -> None:
        result = split_sentences("Talk to Dr. Smith about it.")
        self.assertEqual(result, ["Talk to Dr. Smith about it."])

    def test_multiple_sentences_with_abbreviation(self) -> None:
        result = split_sentences("Mr. Jones arrived. He sat down.")
        self.assertEqual(result, ["Mr. Jones arrived.", "He sat down."])

    def test_question_and_exclamation(self) -> None:
        result = split_sentences("Really? Yes! Absolutely.")
        self.assertEqual(result, ["Really?", "Yes!", "Absolutely."])

    def test_single_word(self) -> None:
        self.assertEqual(split_sentences("Hello"), ["Hello"])

    def test_preserves_whitespace_within_sentences(self) -> None:
        result = split_sentences("Hello   there.   How are you?")
        self.assertEqual(len(result), 2)
        self.assertIn("Hello   there.", result[0])
