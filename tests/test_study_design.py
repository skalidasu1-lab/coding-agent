import unittest

from study.design import CELLS, assignment, williams_row


class CounterbalancingTests(unittest.TestCase):
    def test_every_cell_appears_once_per_position(self):
        for position in range(6):
            cells = {assignment(p)[position][1:] for p in range(6)}
            self.assertEqual(len(cells), 6)

    def test_each_task_meets_every_cell_once(self):
        for task in range(6):
            cells = {assignment(p)[task][1:] for p in range(6)}
            self.assertEqual(len(cells), 6)

    def test_each_participant_sees_every_cell_once(self):
        for p in range(6):
            cells = [item[1:] for item in assignment(p)]
            self.assertEqual(len(set(cells)), 6)

    def test_every_ordered_pair_of_neighbours_appears_once(self):
        pairs = []
        for k in range(6):
            row = williams_row(6, k)
            pairs.extend(zip(row, row[1:]))
        self.assertEqual(len(pairs), 30)
        self.assertEqual(len(set(pairs)), 30)

    def test_sequences_repeat_every_six_participants(self):
        self.assertEqual(assignment(0), assignment(6))
        self.assertEqual(len(CELLS), 6)


if __name__ == "__main__":
    unittest.main()