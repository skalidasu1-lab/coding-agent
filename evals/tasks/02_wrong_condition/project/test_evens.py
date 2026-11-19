import unittest

from evens import count_evens, is_even


class EvenTests(unittest.TestCase):
    def test_is_even(self):
        self.assertTrue(is_even(4))
        self.assertFalse(is_even(3))

    def test_count_evens(self):
        self.assertEqual(count_evens([1, 2, 3, 4]), 2)


if __name__ == "__main__":
    unittest.main()
