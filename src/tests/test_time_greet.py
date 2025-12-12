import unittest
from datetime import datetime, timezone, timedelta

from src.api_fastapi import time_greet


class TestTimeGreet(unittest.TestCase):
    def test_morning(self):
        dt = datetime(2025, 12, 3, 6, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(time_greet(now=dt), "Selamat pagi")

    def test_noon(self):
        dt = datetime(2025, 12, 3, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(time_greet(now=dt), "Selamat siang")

    def test_afternoon(self):
        dt = datetime(2025, 12, 3, 16, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(time_greet(now=dt), "Selamat sore")

    def test_night(self):
        dt = datetime(2025, 12, 3, 22, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(time_greet(now=dt), "Selamat malam")


if __name__ == '__main__':
    unittest.main()
