import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ask_engine_utils import _is_read_only_sql


class ReadOnlySqlGuardTest(unittest.TestCase):
    def test_select_and_with_select_are_allowed(self):
        allowed = [
            "SELECT id, name FROM users",
            "WITH active AS (SELECT id FROM users) SELECT * FROM active",
        ]

        for sql in allowed:
            with self.subTest(sql=sql):
                self.assertTrue(_is_read_only_sql(sql))

    def test_cte_writes_are_rejected(self):
        rejected = [
            "WITH changed AS (INSERT INTO logs(message) VALUES ('x') RETURNING *) SELECT * FROM changed",
            "WITH changed AS (UPDATE users SET active = true RETURNING *) SELECT * FROM changed",
            "WITH changed AS (DELETE FROM users RETURNING *) SELECT * FROM changed",
        ]

        for sql in rejected:
            with self.subTest(sql=sql):
                self.assertFalse(_is_read_only_sql(sql))

    def test_execute_vacuum_and_copy_are_rejected(self):
        rejected = [
            "SELECT 1; EXECUTE prepared_statement",
            "SELECT 1; VACUUM users",
            "SELECT 1; COPY users TO STDOUT",
        ]

        for sql in rejected:
            with self.subTest(sql=sql):
                self.assertFalse(_is_read_only_sql(sql))

    def test_comments_with_blocked_keywords_are_ignored(self):
        allowed = [
            "/* DELETE FROM users */ SELECT id FROM users",
            "SELECT id FROM users -- UPDATE users SET active = false",
        ]

        for sql in allowed:
            with self.subTest(sql=sql):
                self.assertTrue(_is_read_only_sql(sql))

    def test_similar_identifiers_are_not_rejected(self):
        allowed = [
            "SELECT updated_at, deleted_at FROM audit_log",
            "SELECT copy_count, vacuum_status, analyzer_name FROM job_stats",
            "WITH inserted_rows AS (SELECT insert_count FROM metrics) SELECT * FROM inserted_rows",
        ]

        for sql in allowed:
            with self.subTest(sql=sql):
                self.assertTrue(_is_read_only_sql(sql))


if __name__ == "__main__":
    unittest.main()
