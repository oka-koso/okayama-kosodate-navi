import importlib.util
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

midyear = module('update_midyear_admission')
dual = module('update_availability_dual')
HTML = '''<table><tr><td>令和８年１１月入園</td><td>令和８年１０月１日（木曜日）</td></tr>
<tr><td>令和8年12月入園</td><td>令和8年11月2日（月曜日）</td></tr>
<tr><td>令和9年1月入園</td><td>令和8年12月1日（火曜日）</td></tr>
<tr><td>令和9年4月入園</td><td>令和8年11月4日（水曜日）</td></tr></table>'''

class DeadlineTests(unittest.TestCase):
    def test_holiday_adjusted_dates_and_cutoff(self):
        rows = midyear.parse_deadlines(HTML)
        self.assertEqual(len(rows), 3)  # April is a separate recruitment stream.
        self.assertEqual(rows[1]['deadline_date'], '2026-11-02')
        def selected(iso):
            return midyear.next_deadline(rows, datetime.fromisoformat(iso))
        self.assertEqual(selected('2026-10-01T17:15:00+09:00')['target_month'], 11)
        self.assertEqual(selected('2026-10-01T17:15:01+09:00')['target_month'], 12)
        self.assertEqual(selected('2026-11-02T17:15:01+09:00')['target_year'], 2027)
        self.assertIsNone(selected('2027-02-01T00:00:00+09:00'))

    def test_invalid_table_is_not_replaced_with_guessed_dates(self):
        for html in ['<p>no table</p>', HTML + '<table><tr><td>令和8年12月入園</td><td>令和8年11月3日</td></tr></table>']:
            with self.assertRaises(ValueError):
                midyear.parse_deadlines(html)

    def test_failed_fetch_preserves_verified_schedule_and_records_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'midyear.json'
            existing = {'checked_at': '2026-10-10T12:00:00+09:00', 'deadlines': midyear.parse_deadlines(HTML)}
            out.write_text(json.dumps(existing))
            with patch.object(midyear, 'OUT', out), patch.object(midyear, 'fetch_html', side_effect=RuntimeError('offline')):
                with self.assertRaises(RuntimeError):
                    midyear.main()
            actual = json.loads(out.read_text())
            self.assertEqual(actual['deadlines'], existing['deadlines'])
            self.assertEqual(actual['checked_at'], existing['checked_at'])
            self.assertEqual(actual['check_status'], 'failed')

    def test_publication_parser_excludes_nonrecognised_and_education(self):
        rows = midyear.availability_publications('''<a href="R8.12ninka.pdf">【認可保育園】令和８年１２月受入見込み</a>
<a href="ninkagai.pdf">【認可外】令和8年12月受入見込み</a><a href="education.pdf">教育利用 令和9年4月受入見込み</a>''')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['target_month'], 12)

    def test_publication_plans_use_explicit_monthly_announcement(self):
        html = '''<p>次回、令和８年１２月入園に関する受入見込み情報は、令和８年１０月２６日（月曜日）に公表する予定です。</p>
<p>令和9年4月入園の受入見込み情報は、平成8年10月14日に公表予定です。</p>'''
        plans = midyear.availability_publication_plans(html)
        self.assertEqual(plans, [{'target_year': 2026, 'target_month': 12,
                                 'publish_date': '2026-10-26', 'source': midyear.AVAILABILITY_PAGE}])
        self.assertEqual(midyear.availability_publication_plans('<p>締切の約1週間前に公開します。</p>'), [])
        self.assertEqual(midyear.availability_publication_plans('<p>令和9年4月入園に関する受入見込み情報は、令和8年10月14日に公表する予定です。</p>'), [])

class AprilPipelineTests(unittest.TestCase):
    def test_deadline_sync_still_runs_after_availability_failure(self):
        with patch.object(dual, 'main', side_effect=RuntimeError('PDF parse failed')), patch.object(dual.subprocess, 'run') as run:
            with self.assertRaises(RuntimeError):
                dual.run_updates()
        run.assert_called_once()

    def test_april_is_processed_when_monthly_pdf_is_not_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data').mkdir()
            april = {'stream': 'april', 'score': 20, 'order': 1, 'title': '令和9年4月受入見込み', 'url': 'https://example.test/april.pdf'}
            with patch.object(dual, 'ROOT', root), patch.object(dual, 'DISCOVERY_AUDIT', root / 'data' / 'audit.json'), patch.object(dual, 'ensure_verified_facility_master'), patch.object(dual, 'load_legacy'), patch.object(dual, 'fetch_source_page', return_value=('2026-10-14', '', [april])), patch.object(dual, 'run_legacy_for') as run:
                dual.main()
            run.assert_called_once()
            self.assertEqual(run.call_args.args[-2], 'availability_april.json')
            audit = json.loads((root / 'data' / 'audit.json').read_text())
            self.assertEqual(audit['results'], {'monthly': 'not-published-now', 'april': 'updated'})

if __name__ == '__main__':
    unittest.main()
