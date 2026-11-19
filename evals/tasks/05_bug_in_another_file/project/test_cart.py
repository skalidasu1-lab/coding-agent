import unittest

from cart import total


class CartTests(unittest.TestCase):
    def test_ten_percent_off(self):
        self.assertAlmostEqual(total([50, 50], 10), 90)

    def test_no_discount(self):
        self.assertAlmostEqual(total([20], 0), 20)

    def test_twenty_five_percent_off(self):
        self.assertAlmostEqual(total([40], 25), 30)


if __name__ == "__main__":
    unittest.main()
