import sqlite3
import unittest

from db_creation.postgres.load_from_sqlite import load_platform_rows


class PlatformImportTests(unittest.TestCase):
    def test_preserves_false_flags_and_missing_records(self):
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.execute("CREATE TABLE game_platforms (appid INTEGER, windows INTEGER, mac INTEGER, linux INTEGER)")
        connection.executemany("INSERT INTO game_platforms VALUES (?, ?, ?, ?)", [(1, 1, 0, 1), (2, 0, 0, 0)])
        platforms = load_platform_rows(connection)
        self.assertEqual(platforms[1], {"windows": True, "mac": False, "linux": True})
        self.assertEqual(platforms[2], {"windows": False, "mac": False, "linux": False})
        self.assertIsNone(platforms.get(3))
