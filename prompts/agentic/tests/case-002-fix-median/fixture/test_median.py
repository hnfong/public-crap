import unittest

from median import median


class TestMedian(unittest.TestCase):
    def test_odd_count(self):
        self.assertEqual(median([1, 2, 3]), 2)

    def test_even_count(self):
        self.assertEqual(median([1, 2, 3, 4]), 2.5)

    def test_single(self):
        self.assertEqual(median([7]), 7)

    def test_unsorted(self):
        self.assertEqual(median([5, 1, 3]), 3)

    def test_floats(self):
        self.assertEqual(median([1.0, 2.0]), 1.5)


if __name__ == "__main__":
    unittest.main()
