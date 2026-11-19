import unittest

from palindrome import is_palindrome


class PalindromeTests(unittest.TestCase):
    def test_simple(self):
        self.assertTrue(is_palindrome("racecar"))

    def test_sentence(self):
        self.assertTrue(is_palindrome("A man, a plan, a canal: Panama"))

    def test_not_a_palindrome(self):
        self.assertFalse(is_palindrome("hello"))


if __name__ == "__main__":
    unittest.main()
