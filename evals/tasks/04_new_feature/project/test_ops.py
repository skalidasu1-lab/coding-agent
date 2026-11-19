import unittest

from ops import add, divide, multiply, subtract


class OpsTests(unittest.TestCase):
    def test_existing_functions_still_work(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(subtract(5, 3), 2)

    def test_multiply(self):
        self.assertEqual(multiply(3, 4), 12)

    def test_divide(self):
        self.assertEqual(divide(10, 4), 2.5)

    def test_divide_by_zero(self):
        with self.assertRaises(ValueError):
            divide(1, 0)


if __name__ == "__main__":
    unittest.main()
