import unittest

from mathutils import sum_to_n


class SumToNTests(unittest.TestCase):
    def test_five(self):
        self.assertEqual(sum_to_n(5), 15)

    def test_one(self):
        self.assertEqual(sum_to_n(1), 1)

    def test_zero(self):
        self.assertEqual(sum_to_n(0), 0)


if __name__ == "__main__":
    unittest.main()
