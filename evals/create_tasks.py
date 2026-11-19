import os

TASKS = {
    "01_off_by_one": {
        "prompt": "The function sum_to_n in mathutils.py should return the sum of the numbers 1 through n, but the tests in test_mathutils.py fail. Find the bug and fix it.",
        "files": {
            "mathutils.py": '''def sum_to_n(n):
    total = 0
    for i in range(n):
        total += i
    return total
''',
            "test_mathutils.py": '''import unittest

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
''',
        },
    },
    "02_wrong_condition": {
        "prompt": "The tests in test_evens.py fail. Find the bug in evens.py and fix it.",
        "files": {
            "evens.py": '''def is_even(n):
    return n % 2 == 1


def count_evens(numbers):
    return sum(1 for n in numbers if is_even(n))
''',
            "test_evens.py": '''import unittest

from evens import count_evens, is_even


class EvenTests(unittest.TestCase):
    def test_is_even(self):
        self.assertTrue(is_even(4))
        self.assertFalse(is_even(3))

    def test_count_evens(self):
        self.assertEqual(count_evens([1, 2, 3, 4]), 2)


if __name__ == "__main__":
    unittest.main()
''',
        },
    },
    "03_palindrome": {
        "prompt": "is_palindrome in palindrome.py should ignore case, spaces and punctuation. The tests in test_palindrome.py fail. Fix the function.",
        "files": {
            "palindrome.py": '''def is_palindrome(text):
    return text == text[::-1]
''',
            "test_palindrome.py": '''import unittest

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
''',
        },
    },
    "04_new_feature": {
        "prompt": "Add two functions to ops.py: multiply(a, b), and divide(a, b), which raises ValueError when b is 0. The file test_ops.py describes the expected behavior.",
        "files": {
            "ops.py": '''def add(a, b):
    return a + b


def subtract(a, b):
    return a - b
''',
            "test_ops.py": '''import unittest

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
''',
        },
    },
    "05_bug_in_another_file": {
        "prompt": "The tests in test_cart.py fail. Find the cause (it may be in a different file from the tests) and fix it.",
        "files": {
            "pricing.py": '''def apply_discount(price, percent):
    return price * (percent / 100)
''',
            "cart.py": '''from pricing import apply_discount


def total(prices, discount_percent=0):
    subtotal = sum(prices)
    if discount_percent:
        return apply_discount(subtotal, discount_percent)
    return subtotal
''',
            "test_cart.py": '''import unittest

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
''',
        },
    },
}

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks")
for name, task in TASKS.items():
    task_dir = os.path.join(root, name)
    project_dir = os.path.join(task_dir, "project")
    os.makedirs(project_dir, exist_ok=True)
    with open(os.path.join(task_dir, "prompt.txt"), "w") as f:
        f.write(task["prompt"] + "\n")
    for filename, content in task["files"].items():
        with open(os.path.join(project_dir, filename), "w") as f:
            f.write(content)
    print(f"created {name}")