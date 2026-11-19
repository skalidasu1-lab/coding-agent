import os
import tempfile
import unittest
from unittest.mock import patch

from config import MAX_CHARS
from functions.get_file_content import get_file_content
from functions.get_files_info import get_files_info
from functions.run_python_file import run_python_file
from functions.write_file import write_file


class GuardrailTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = os.path.realpath(self.tmp.name)
        self.work = os.path.join(base, "work")
        self.evil = os.path.join(base, "work-evil")  # sibling whose name starts with "work"
        self.outside = os.path.join(base, "outside")
        for folder in (self.work, self.evil, self.outside):
            os.makedirs(folder)
        for folder, text in ((self.work, "inside"), (self.evil, "secret"), (self.outside, "secret")):
            name = "inside.txt" if folder == self.work else "secret.txt"
            with open(os.path.join(folder, name), "w") as f:
                f.write(text)

    def tearDown(self):
        self.tmp.cleanup()

    def assert_blocked(self, result):
        self.assertTrue(result.startswith("Error:"), result)
        self.assertIn("outside the permitted working directory", result)

    def test_read_inside_works(self):
        self.assertEqual(get_file_content(self.work, "inside.txt"), "inside")

    def test_read_parent_traversal_blocked(self):
        self.assert_blocked(get_file_content(self.work, "../outside/secret.txt"))

    def test_read_absolute_path_blocked(self):
        self.assert_blocked(get_file_content(self.work, os.path.join(self.outside, "secret.txt")))

    def test_read_sibling_with_same_prefix_blocked(self):
        self.assert_blocked(get_file_content(self.work, "../work-evil/secret.txt"))

    def test_read_through_symlink_blocked(self):
        os.symlink(self.outside, os.path.join(self.work, "link"))
        self.assert_blocked(get_file_content(self.work, "link/secret.txt"))

    def test_write_outside_blocked(self):
        self.assert_blocked(write_file(self.work, "../outside/new.txt", "x"))
        self.assertFalse(os.path.exists(os.path.join(self.outside, "new.txt")))

    def test_write_inside_creates_parent_folders(self):
        result = write_file(self.work, "sub/new.txt", "hello")
        self.assertIn("5 characters written", result)
        self.assertTrue(os.path.isfile(os.path.join(self.work, "sub", "new.txt")))

    def test_list_parent_blocked(self):
        self.assert_blocked(get_files_info(self.work, ".."))

    def test_run_outside_blocked(self):
        self.assert_blocked(run_python_file(self.work, "../outside/x.py"))

    def test_run_rejects_non_python_file(self):
        self.assertIn("is not a Python file", run_python_file(self.work, "inside.txt"))

    def test_run_does_not_leak_secrets(self):
        write_file(self.work, "leak.py", "import os\nprint(os.environ.get('FAKE_API_KEY'))\n")
        with patch.dict(os.environ, {"FAKE_API_KEY": "topsecret"}):
            result = run_python_file(self.work, "leak.py")
        self.assertNotIn("topsecret", result)

    def test_long_file_is_truncated(self):
        write_file(self.work, "big.txt", "a" * (MAX_CHARS + 50))
        self.assertIn("truncated", get_file_content(self.work, "big.txt"))


if __name__ == "__main__":
    unittest.main()