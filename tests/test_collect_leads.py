"""Synthetic fixtures test protocol behavior; they are never saved as leads."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import collect_leads as c


class CollectorTests(unittest.TestCase):
    def test_rss_and_atom(self):
        rss = b'<rss><channel><item><title>Singapore school tuition?</title><link>https://example.test/q</link></item></channel></rss>'
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Malaysia university admission?</title><link rel="self" href="https://example.test/api"/><link href="https://example.test/q"/><author><name>Author</name></author></entry></feed>'
        for feed in (rss, atom):
            rows, scanned = c.parse_feed(feed, {'name': 'fixture'})
            self.assertEqual((len(rows), scanned), (1, 1))
            self.assertEqual(rows[0]['url'], 'https://example.test/q')
        self.assertEqual(c.parse_feed(atom, {'name':'fixture'})[0][0]['author'], 'Author')

    def test_unrelated_and_invalid_feed(self):
        self.assertEqual(c.parse_feed(b'<rss><channel><item><title>Singapore weather</title></item></channel></rss>', {'name':'fixture'}), ([], 1))
        with self.assertRaises(ValueError):
            c.parse_feed(b'<html/>', {'name':'fixture'})

    def test_collection_outcomes_and_dedup(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            output, report = Path(d)/'leads.json', Path(d)/'report.json'
            original = '[{"url":"https://example.test/q#fragment"}]'
            output.write_text(original)
            source = [{'name':'fixture','url':'https://example.test/feed'}]
            with patch.object(c, 'fetch_rss', return_value=([{'url':'https://example.test/q'}], 1)):
                self.assertEqual(c.collect(source, output, report), 0)
                self.assertEqual(json.loads(report.read_text())['added'], 0)
            with patch.object(c, 'fetch_rss', return_value=([], 10)):
                self.assertEqual(c.collect(source, output, report), 0)
                self.assertEqual(json.loads(report.read_text())['sources'][0]['matched'], 0)
            with patch.object(c, 'fetch_rss', side_effect=urllib.error.HTTPError(source[0]['url'],429,'limited',{},None)):
                self.assertEqual(c.collect(source, output, report), 1)
                self.assertEqual(json.loads(report.read_text())['status'], 'failed')
            self.assertEqual(output.read_text(), original)
            with patch.object(c, 'fetch_rss', side_effect=[([],2), urllib.error.URLError('denied')]):
                self.assertEqual(c.collect(source*2, output, report), 1)
                self.assertEqual(json.loads(report.read_text())['status'], 'partial_failure')
            with patch.object(c, 'fetch_rss', return_value=([{'url':'https://example.test/new'}], 1)):
                self.assertEqual(c.collect(source, output, report), 0)
                self.assertEqual(len(json.loads(output.read_text())), 2)
                self.assertEqual(json.loads(report.read_text())['added'], 1)
            output.write_text('broken')
            with self.assertRaises(ValueError):
                c.collect(source, output, report)
            self.assertEqual(output.read_text(), 'broken')

if __name__ == '__main__':
    unittest.main()
