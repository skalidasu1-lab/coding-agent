import os
import tempfile
import unittest

from study import tasks

HAVE_TASKS = bool(tasks.task_ids())


@unittest.skipUnless(HAVE_TASKS, "task bank not generated (study/tasks is git-ignored)")
class TaskBankTests(unittest.TestCase):
    def test_reference_solutions_pass_every_hidden_test(self):
        for task_id in tasks.task_ids():
            solution = os.path.join(tasks.TASKS_DIR, task_id, "solution")
            result = tasks.grade(task_id, solution)
            self.assertTrue(result["passed"], f"{task_id}: {result}")
            self.assertEqual(result["score"], 1.0)

    def test_an_empty_project_fails(self):
        for task_id in tasks.task_ids():
            with tempfile.TemporaryDirectory() as tmp:
                open(os.path.join(tmp, "main.py"), "w").close()
                result = tasks.grade(task_id, tmp)
            self.assertFalse(result["passed"], task_id)
            self.assertLess(result["score"], 1.0)

    def test_each_task_has_three_ambiguities_with_answers(self):
        for task_id in tasks.task_ids():
            task = tasks.load_task(task_id)
            self.assertEqual(len(task["ambiguities"]), 3, task_id)
            for item in task["ambiguities"]:
                self.assertTrue(item["keywords"] and item["answer"])

    def test_scripted_student_answers_matching_questions(self):
        task = tasks.load_task("t1_temperature")
        answer = tasks.canned_answer(task, "What should happen with an invalid unit?")
        self.assertIn("unknown unit", answer)
        self.assertIn("best judgment", tasks.canned_answer(task, "What is your favourite colour?"))


if __name__ == "__main__":
    unittest.main()