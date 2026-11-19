import os
import tempfile
import unittest

from functions.edit_file import edit_file


class EditFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = os.path.realpath(self.tmp.name)
        self.path = os.path.join(self.work, "a.txt")
        with open(self.path, "w") as f:
            f.write("alpha\nbeta\nbeta\n")
        with open(os.path.join(os.path.dirname(self.work), "outside.txt"), "w") as f:
            f.write("keep")

    def tearDown(self):
        self.tmp.cleanup()

    def read(self):
        with open(self.path) as f:
            return f.read()

    def test_replaces_a_unique_match(self):
        result = edit_file(self.work, "a.txt", "alpha", "ALPHA")
        self.assertIn("Successfully edited", result)
        self.assertEqual(self.read(), "ALPHA\nbeta\nbeta\n")

    def test_missing_text_is_an_error_and_changes_nothing(self):
        result = edit_file(self.work, "a.txt", "gamma", "x")
        self.assertTrue(result.startswith("Error:"))
        self.assertEqual(self.read(), "alpha\nbeta\nbeta\n")

    def test_ambiguous_match_is_an_error_and_changes_nothing(self):
        result = edit_file(self.work, "a.txt", "beta", "x")
        self.assertIn("appears 2 times", result)
        self.assertEqual(self.read(), "alpha\nbeta\nbeta\n")

    def test_outside_path_is_blocked(self):
        result = edit_file(self.work, "../outside.txt", "keep", "gone")
        self.assertIn("outside the permitted working directory", result)

    def test_empty_old_text_is_rejected(self):
        self.assertTrue(edit_file(self.work, "a.txt", "", "x").startswith("Error:"))


if __name__ == "__main__":
    unittest.main()