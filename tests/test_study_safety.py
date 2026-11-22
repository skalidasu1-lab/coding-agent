import json
import os
import shutil
import tempfile
import unittest

from functions.get_file_content import get_file_content
from functions.run_python_file import run_python_file
from study import tasks
from study.safety import flag_suspicious

HAVE_TASKS = bool(tasks.task_ids())
T1 = "t1_temperature"


@unittest.skipUnless(os.name == "posix", "resource limits need POSIX")
class ChildLimitTests(unittest.TestCase):
    def run_script(self, code):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "s.py"), "w") as f:
                f.write(code)
            return run_python_file(tmp, "s.py")

    def test_huge_file_write_is_stopped(self):
        out = self.run_script("open('x.bin', 'wb').write(b'0' * (50 * 1024 * 1024))\n")
        self.assertIn("Process exited with code", out)

    def test_huge_memory_use_is_stopped(self):
        out = self.run_script("data = bytearray(3 * 1024 * 1024 * 1024)\n")
        self.assertIn("Process exited with code", out)


@unittest.skipUnless(HAVE_TASKS, "task bank not generated")
class GradingIntegrityTests(unittest.TestCase):
    def project(self, tmp, with_solution):
        folder = os.path.join(tmp, "project")
        os.makedirs(folder)
        if with_solution:
            shutil.copy(os.path.join(tasks.TASKS_DIR, T1, "solution", "main.py"), folder)
        else:
            open(os.path.join(folder, "main.py"), "w").close()
        return folder

    def test_a_planted_fake_test_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.project(tmp, with_solution=False)
            with open(os.path.join(folder, "test_hidden.py"), "w") as f:
                f.write("import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        pass\n")
            self.assertFalse(tasks.grade(T1, folder)["passed"])

    def test_files_that_shadow_standard_modules_do_not_break_grading(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.project(tmp, with_solution=True)
            for name in ("subprocess.py", "unittest.py"):
                with open(os.path.join(folder, name), "w") as f:
                    f.write("raise RuntimeError('shadowed')\n")
            self.assertTrue(tasks.grade(T1, folder)["passed"])

    def test_grading_leaves_the_agents_folder_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.project(tmp, with_solution=True)
            before = sorted(os.listdir(folder))
            tasks.grade(T1, folder)
            self.assertEqual(sorted(os.listdir(folder)), before)
            self.assertNotIn("test_hidden.py", os.listdir(folder))


class ToolGuardrailTests(unittest.TestCase):
    def test_tools_cannot_read_a_hidden_test_file_beside_the_workdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "work"))
            os.makedirs(os.path.join(tmp, "hidden_tests"))
            with open(os.path.join(tmp, "hidden_tests", "test_hidden.py"), "w") as f:
                f.write("secret")
            result = get_file_content(os.path.join(tmp, "work"), "../hidden_tests/test_hidden.py")
        self.assertIn("outside the permitted working directory", result)


class FlagTests(unittest.TestCase):
    def call(self, name, **arguments):
        return {"name": name, "arguments": json.dumps(arguments)}

    def test_normal_calls_are_not_flagged(self):
        log = [self.call("write_file", file_path="main.py", content="print('hi')"),
               self.call("get_files_info", directory=".")]
        self.assertEqual(flag_suspicious(log), [])

    def test_paths_that_leave_the_folder_are_flagged(self):
        for path in ("../x", "/etc/passwd", "~/secret", "a/../../b"):
            self.assertTrue(flag_suspicious([self.call("get_file_content", file_path=path)]), path)

    def test_code_that_reads_the_environment_is_flagged(self):
        log = [self.call("write_file", file_path="main.py", content="import os\nprint(os.environ)")]
        self.assertEqual(flag_suspicious(log)[0]["marker"], "os.environ")

    def test_invalid_json_does_not_crash(self):
        self.assertEqual(flag_suspicious([{"name": "x", "arguments": "{oops"}]), [])


if __name__ == "__main__":
    unittest.main()