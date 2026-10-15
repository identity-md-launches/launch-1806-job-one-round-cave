"""Offline selection, validation, bounds and CLI integration tests."""
import contextlib
import copy
import io
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

S = runpy.run_path(str(Path(__file__).with_name('select_result.py')))
SAMPLE = 'line-1/tools/bounded-rpc-snapshot/sample-zto-supply.json'


class SelectionTests(unittest.TestCase):
    def test_real_zto(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
            snapshot = S['B']['verify_snapshot'](SAMPLE)
            r = S['report'](snapshot, '')
        self.assertEqual(r['value_type'], 'string')
        self.assertEqual(int(r['value'], 16), 10**27)
        self.assertEqual(r['request']['params'][0]['to'], S['B']['ZTO'])

    def test_real_block(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
            s = S['B']['verify_snapshot']('line-1/tools/snapshot-select/live-block.json')
            self.assertEqual(int(S['report'](s, '/number')['value'], 16), 26195002)
            r = S['report'](s, '/transactions/0')
        self.assertEqual(r['value'], s['response']['result']['transactions'][0])
        self.assertEqual(len(r['value']), 66)
        self.assertEqual(len(s['response']['result']['transactions']), 192)

    def test_rfc_escapes_and_empty_keys(self):
        value = {'a/b': {'~key': {'': [False, None, 10**80]}}}
        for index, expected in enumerate([False, None, 10**80]):
            self.assertEqual(S['select'](value, '/a~1b/~0key//'+str(index)), expected)
        self.assertEqual(S['select']({'~1': 3}, '/~01'), 3)

    def test_root(self):
        for value in [None, False, 0, '', [], {}]:
            self.assertIs(S['select'](value, ''), value)

    def test_bad_pointer(self):
        for pointer in ['a', '#/a', '/~', '/~2', '/a~9b', '/'+'x'*4096, '/'*65]:
            with self.subTest(pointer=pointer[:20]), self.assertRaises(S['SelectionError']):
                S['tokens'](pointer)

    def test_bad_array_indexes(self):
        for token in ['-', '00', '01', '-1', '+1', '1.0', ' ', '\u0660', '2', '9'*4000]:
            with self.subTest(token=token[:20]), self.assertRaises(S['SelectionError']):
                S['select']([1, 2], '/'+token)
        with self.assertRaises(S['SelectionError']):
            S['select']([], '/0')

    def test_numeric_object_key(self):
        self.assertEqual(S['select']({'01': 'member'}, '/01'), 'member')

    def test_missing_vs_null(self):
        self.assertIsNone(S['select']({'a': None}, '/a'))
        with self.assertRaises(S['SelectionError']):
            S['select']({}, '/a')
        with self.assertRaises(S['SelectionError']):
            S['select']({'a': None}, '/a/b')

    def test_types(self):
        for value, kind in [(None, 'null'), (False, 'boolean'), (4, 'integer'),
                            ('a', 'string'), ([], 'array'), ({}, 'object')]:
            self.assertEqual(S['value_type'](value), kind)
        for value in [0.1, {'a': [0.1]}]:
            with self.assertRaises(S['SelectionError']):
                S['value_type'](value)

    def test_depth(self):
        value = 0
        for _ in range(66):
            value = [value]
        with self.assertRaises(S['SelectionError']):
            S['value_type'](value)

    def test_output_limit(self):
        with self.assertRaises(S['SelectionError']):
            S['render']({'value': 'x'*100000})
        with self.assertRaises(S['SelectionError']):
            S['render']({'value': '\u2603'*20000})
        self.assertLessEqual(len(S['render']({'value': 'ok'})), 100000)

    def test_input_immutable(self):
        s = S['B']['verify_snapshot'](SAMPLE)
        before = copy.deepcopy(s)
        S['render'](S['report'](s, ''))
        self.assertEqual(s, before)

    def test_cli(self):
        before = Path(SAMPLE).read_bytes()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(S['main']([SAMPLE]), 0)
        self.assertEqual(json.loads(output.getvalue())['value_type'], 'string')
        self.assertEqual(Path(SAMPLE).read_bytes(), before)
        for path, pointer in [(SAMPLE, '/missing'), ('/etc/passwd', ''),
                              ('../outside', ''), ('.hidden', ''), (SAMPLE, '#')]:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(S['main']([path, '--pointer', pointer]), 1)

    def test_tampered_and_error_snapshot(self):
        # Scratch fixtures remain inside the explicitly allowed scratch tree.
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir='test/scratch') as tmp:
            path = Path(tmp)/'snapshot.json'
            snapshot = S['B']['verify_snapshot'](SAMPLE)
            for response in [dict(snapshot['response'], result='altered'),
                             {'jsonrpc':'2.0', 'id':1, 'error':{'code':-1, 'message':'failure'}}]:
                changed = dict(snapshot, response=response)
                path.write_text(json.dumps(changed))
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(S['main']([str(path)]), 1)
            path.write_text('{"response":1,"response":2}')
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(S['main']([str(path)]), 1)
            link = Path(tmp)/'link.json'
            link.symlink_to('snapshot.json')
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(S['main']([str(link)]), 1)


if __name__ == '__main__':
    unittest.main()
