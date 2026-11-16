"""Require complete native statuses and safe pagination before any shutdown."""
import unittest
from test_aap_snapshots import snap


ORIGIN = 'https://aap.example.invalid'
PATH = '/api/controller/v2/unified_jobs/'


def page(rows, count=None, next_page=None):
    return {'count': len(rows) if count is None else count, 'results': rows,
            'next': None if next_page is None else PATH + '?order_by=id&page_size=100&page=' + str(next_page)}


def job(number, status='successful'):
    return {'id': number, 'status': status, 'type': 'project_update'}


class ControllerJobsTests(unittest.TestCase):
    def test_complete_unfiltered_success_is_idle_but_filtered_count_mismatch_is_not(self):
        self.assertTrue(snap.controller_jobs_page(page([job(1)]), ORIGIN)['idle'])
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            snap.controller_jobs_page({'count': 1, 'next': None, 'results': []}, ORIGIN)
        self.assertTrue(snap.controller_jobs_page(page([]), ORIGIN)['idle'])

    def test_every_explicit_nonterminal_status_is_active(self):
        for status in ('new', 'pending', 'waiting', 'running'):
            with self.subTest(status=status):
                observed = snap.controller_jobs_page(page([job(1, status)]), ORIGIN)
                self.assertTrue(observed['complete']); self.assertFalse(observed['idle'])
        for status in ('successful', 'failed', 'error', 'canceled'):
            with self.subTest(status=status):
                self.assertTrue(snap.controller_jobs_page(page([job(1, status)]), ORIGIN)['idle'])

    def test_late_page_active_job_is_never_hidden_by_terminal_first_page(self):
        first = snap.controller_jobs_page(page([job(i) for i in range(1, 101)], 101, 2), ORIGIN)
        self.assertFalse(first['complete']); self.assertFalse(first['idle'])
        last = snap.controller_jobs_page(page([job(101, 'running')], 101), ORIGIN, first)
        self.assertTrue(last['complete']); self.assertFalse(last['idle']); self.assertEqual(len(last['jobs']), 101)

    def test_count_changes_duplicate_ids_missing_rows_and_page_bound_fail_closed(self):
        first = snap.controller_jobs_page(page([job(1)], 2, 2), ORIGIN)
        for response in (page([job(2)], 3), page([job(1)], 2), page([], 2), page([job(2), job(3)], 2)):
            with self.subTest(response=response), self.assertRaises(ValueError):
                snap.controller_jobs_page(response, ORIGIN, first)
        with self.assertRaises(ValueError): snap.controller_jobs_page(page([], 2001), ORIGIN)
        scan = {}
        for number in range(1, 20):
            scan = snap.controller_jobs_page(page([job(number)], 21, number + 1), ORIGIN, scan)
        with self.assertRaisesRegex(ValueError, 'finite'):
            snap.controller_jobs_page(page([job(20)], 21, 21), ORIGIN, scan)

    def test_unknown_or_missing_statuses_and_non_native_ids_are_refused(self):
        invalid = [{}, {'id': 1}, {'id': 1, 'status': None}, job(1, 'unknown'), job(1, 'never updated'),
                   job(True), job(0), job(-1), job('1')]
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(ValueError):
                snap.controller_jobs_page(page([row]), ORIGIN)
        for response in ({'count': True, 'results': [], 'next': None},
                         {'count': -1, 'results': [], 'next': None},
                         {'count': 0, 'results': []}, {'count': 0, 'results': {}, 'next': None}):
            with self.subTest(response=response), self.assertRaises(ValueError):
                snap.controller_jobs_page(response, ORIGIN)

    def test_pagination_preserves_exact_authenticated_unfiltered_query(self):
        good = PATH + '?page_size=100&page=2&order_by=id'
        for link in (good, ORIGIN + good):
            observed = snap.controller_jobs_page(dict(page([job(1)], 2, 2), next=link), ORIGIN)
            self.assertEqual(observed['next'], ORIGIN + link if link.startswith('/') else link)
        invalid = ['https://foreign.example.invalid' + good, 'http://aap.example.invalid' + good,
                   '//foreign.example.invalid' + good, '/api/controller/v2/jobs/?page=2',
                   good + '&status__in=running', good + '#fragment', good.replace('page=2', 'page=3'),
                   good.replace('page_size=100', 'page_size=1'), good.replace('order_by=id', 'order_by=-id'),
                   good + '&page=2', 'https://user@aap.example.invalid' + good, '?page=2']
        for link in invalid:
            with self.subTest(link=link), self.assertRaises(ValueError):
                snap.controller_jobs_page(dict(page([job(1)], 2, 2), next=link), ORIGIN)

    def test_duplicate_descending_and_oversized_page_rows_are_refused(self):
        for rows in ([job(1), job(1)], [job(2), job(1)], [job(i) for i in range(1, 102)]):
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                snap.controller_jobs_page(page(rows), ORIGIN)


if __name__ == '__main__': unittest.main()
