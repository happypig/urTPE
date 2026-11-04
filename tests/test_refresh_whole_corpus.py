# -*- coding: utf-8 -*-
"""refresh-whole-corpus (R — B1, B5, B6, C2, §7 4.1): the resumable
whole-corpus refresh. Slices of ~100 projects under the single-writer lock,
a checkpoint between slices, change detection with one cheap signal per
source, the report counting every skip. The driver's logic is imported from
the script module so the tests run offline (adapters injected)."""

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "refresh_whole_corpus", ROOT / "scripts" / "refresh_whole_corpus.py")
rwc = importlib.util.module_from_spec(_spec)
try:
    _spec.loader.exec_module(rwc)
except FileNotFoundError:
    rwc = None


@unittest.skipIf(rwc is None, "refresh_whole_corpus.py not implemented yet (test-first)")
class TestCheckpoint(unittest.TestCase):
    """Task 1.1 — the checkpoint round-trips."""

    def test_write_read_skip_finished(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ck = Path(td) / "checkpoint.json"
            rwc.write_checkpoint(ck, last_pid="乙", finished=["甲", "乙"])
            state = rwc.read_checkpoint(ck)
            self.assertEqual(state["last_pid"], "乙")
            self.assertEqual(state["finished"], ["甲", "乙"])
            # skip-finished: a project in the list is skipped on resume
            self.assertTrue(rwc.is_finished(state, "甲"))
            self.assertFalse(rwc.is_finished(state, "丙"))

    def test_a_missing_checkpoint_reads_empty(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            state = rwc.read_checkpoint(Path(td) / "absent.json")
            self.assertEqual(state, {"last_pid": "", "finished": []})


@unittest.skipIf(rwc is None, "refresh_whole_corpus.py not implemented yet (test-first)")
class TestSlices(unittest.TestCase):
    """Task 1.2 — the slice splitter."""

    def test_sorted_keys_slice_to_about_100(self):
        keys = [f"proj-{i:03d}" for i in range(250)]
        slices = rwc.make_slices(keys, size=100)
        self.assertEqual([len(s) for s in slices], [100, 100, 50])
        # sorted order preserved across slices
        flat = [k for s in slices for k in s]
        self.assertEqual(flat, keys)

    def test_resume_skips_finished(self):
        keys = [f"proj-{i:03d}" for i in range(250)]
        state = {"last_pid": "proj-099", "finished": keys[:100]}
        slices = rwc.make_slices(keys, size=100, state=state)
        self.assertEqual([len(s) for s in slices], [100, 50])


@unittest.skipIf(rwc is None, "refresh_whole_corpus.py not implemented yet (test-first)")
class TestPageSignal(unittest.TestCase):
    """Task 1.3 — the national-page change signal."""

    def test_a_later_date_marks_moved(self):
        self.assertTrue(rwc.page_moved("本專案資料最後更新於 111.05.01", "111.04.01"))
        self.assertFalse(rwc.page_moved("本專案資料最後更新於 111.05.01", "111.05.01"))
        self.assertFalse(rwc.page_moved("", "111.05.01"))  # absent cached date: no signal

    def test_the_date_parses_from_the_page_text(self):
        html = "<html>...本專案資料最後更新於 114.12.31...</html>"
        self.assertEqual(rwc.page_update_date(html), "114.12.31")
        self.assertEqual(rwc.page_update_date("<html>no date</html>"), "")


@unittest.skipIf(rwc is None, "refresh_whole_corpus.py not implemented yet (test-first)")
class TestFinishedCaseSkip(unittest.TestCase):
    """Task 1.4 — a finished case skips its header fetch."""

    def test_finished_by_schedule(self):
        self.assertTrue(rwc.case_finished(
            {"schedule": "已完工"}, {}))
        self.assertTrue(rwc.case_finished(
            {"schedule": "完成成果備查"}, {}))

    def test_finished_by_ulic(self):
        self.assertTrue(rwc.case_finished(
            {}, {"使照核發日期": "2020/01/19"}))

    def test_an_open_case_is_not_finished(self):
        self.assertFalse(rwc.case_finished(
            {"schedule": "審查中"}, {"申請核定日期": "2026/07/30"}))

    def test_a_moved_project_overrides_the_skip(self):
        self.assertFalse(rwc.case_finished(
            {"schedule": "已完工"}, {}, project_moved=True))


@unittest.skipIf(rwc is None, "refresh_whole_corpus.py not implemented yet (test-first)")
class TestReport(unittest.TestCase):
    """Task 1.5 — the report counts every skip."""

    def test_counts_per_source(self):
        rep = rwc.new_report()
        rwc.count(rep, "page", "fetched")
        rwc.count(rep, "page", "skipped_unchanged")
        rwc.count(rep, "header", "skipped_unchanged")
        self.assertEqual(rep["page"], {"fetched": 1, "skipped_unchanged": 1, "failed": 0})
        self.assertEqual(rep["header"]["skipped_unchanged"], 1)

    def test_failures_are_named(self):
        rep = rwc.new_report()
        rwc.count(rep, "page", "failed", name="甲")
        self.assertEqual(rep["page_failed"], ["甲"])


@unittest.skipIf(rwc is None, "refresh_whole_corpus.py not implemented yet (test-first)")
class TestDriverCalls(unittest.TestCase):
    """Task 1.6 — the driver calls the standing refresh_project."""

    def test_refresh_project_is_called_per_project(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cache = Path(td)
            calls = []

            def fake_refresh(cache_dir, pid, search_key=None):
                calls.append(pid)
                return {"project_id": pid, "error": ""}

            rwc.refresh_slice(
                cache, ["甲", "乙"], search_keys={},
                refresh_fn=fake_refresh, page_fetch=None, report=None)
            self.assertEqual(calls, ["甲", "乙"])


if __name__ == "__main__":
    unittest.main()
