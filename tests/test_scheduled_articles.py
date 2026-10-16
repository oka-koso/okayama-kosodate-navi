import importlib.util
from datetime import datetime
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publish_scheduled_articles', ROOT / 'scripts/publish_scheduled_articles.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for p in ['_scheduled_articles', 'data', 'assets', 'articles']:
            shutil.copytree(ROOT / p, self.root / p)
        for p in ['index.html', 'bibouroku.html', 'sitemap.xml', 'moushikomi.html']:
            shutil.copy2(ROOT / p, self.root / p)
        self.entries = json.loads((self.root / '_scheduled_articles/manifest.json').read_text())
        self.urls = [entry['article']['url'] for entry in self.entries]

    def run_at(self, time):
        return publisher.release(self.root, datetime.fromisoformat(time))

    def assert_public(self, expected):
        data = json.loads((self.root / 'data/bibouroku.json').read_text())
        sitemap = (self.root / 'sitemap.xml').read_text()
        ET.fromstring(sitemap)
        for url in self.urls:
            self.assertEqual(url in [a['url'] for a in data], url in expected)
            self.assertEqual((self.root / url).exists(), url in expected)
            for page in ['index.html', 'bibouroku.html', 'sitemap.xml']:
                self.assertEqual(url in (self.root / page).read_text(), url in expected)

    def test_japan_midnight_each_day_and_idempotence(self):
        self.assertEqual(self.run_at('2026-10-17T14:59:59+00:00'), [])
        self.assert_public([])
        self.assertEqual(self.run_at('2026-10-17T15:00:00+00:00'), self.urls[:1])
        self.assert_public(self.urls[:1])
        self.assertEqual(self.run_at('2026-10-18T14:59:59+00:00'), [])
        self.assertEqual(self.run_at('2026-10-18T15:00:00+00:00'), self.urls[1:])
        self.assert_public(self.urls)
        data = json.loads((self.root / 'data/bibouroku.json').read_text())
        self.assertEqual(data[0]['url'], self.urls[1])
        self.assertEqual(data[1]['url'], self.urls[0])
        before = (self.root / 'bibouroku.html').read_bytes()
        self.assertEqual(self.run_at('2026-10-20T10:00:00+09:00'), [])
        self.assertEqual((self.root / 'bibouroku.html').read_bytes(), before)
        for entry in self.entries:
            for page in entry['backlinks']:
                self.assertIn(Path(entry['article']['url']).name, (self.root / page).read_text())

    def test_missed_run_catches_up_both_articles(self):
        self.assertEqual(self.run_at('2026-10-19T09:00:00+09:00'), self.urls)
        self.assert_public(self.urls)

    def test_invalid_batch_does_not_publish_partial_article(self):
        (self.root / self.entries[1]['article']['image']).unlink()
        with self.assertRaisesRegex(ValueError, 'Missing image'):
            self.run_at('2026-10-19T09:00:00+09:00')
        self.assert_public([])
