import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('plan_diff_test', HERE / 'plan_diff.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.raw = (HERE.parent / 'settlement-batch/demo-manifest.json').read_bytes()
        self.old = json.loads(self.raw)
        self.new = copy.deepcopy(self.old)
        self.pin = hashlib.sha256(self.raw).hexdigest()

    def result(self):
        return d.compare(self.raw, json.dumps(self.new).encode(), self.pin)

    def test_real_plan(self):
        result = self.result()
        self.assertTrue(result['planCompatible'])
        self.assertFalse(result['evidenceChecked'])
        self.assertEqual(result['changes'], [])
        self.assertEqual(result['baselineCount'], 2)

    def test_baseline_pin_before_parse(self):
        with patch.object(d.b, 'validate', side_effect=AssertionError('parsed')):
            result = d.compare(b'not json', self.raw, self.pin)
        self.assertEqual(result['state'], 'baseline_pin_mismatch')
        self.assertFalse(result['planCompatible'])

    def test_lower_confirmations(self):
        self.new['items'][0]['policy']['minimumConfirmations'] = 1
        self.assertFalse(self.result()['planCompatible'])
        self.assertEqual(self.result()['changes'][0]['kind'], 'policy_weakened')

    def test_higher_confirmations(self):
        self.new['items'][0]['policy']['minimumConfirmations'] = 13
        self.assertTrue(self.result()['planCompatible'])
        self.assertEqual(self.result()['changes'][0]['kind'], 'policy_strengthened')

    def test_drop_finality_even_with_more_confirmations(self):
        self.new['items'][0]['policy'].update(requireFinalized=False, minimumConfirmations=100)
        self.assertFalse(self.result()['planCompatible'])
        self.assertEqual(len(self.result()['changes']), 2)

    def test_require_finality(self):
        self.old['items'][0]['policy']['requireFinalized'] = False
        self.raw = json.dumps(self.old).encode()
        self.pin = hashlib.sha256(self.raw).hexdigest()
        self.assertTrue(self.result()['planCompatible'])

    def test_removed(self):
        self.new['items'].pop()
        self.assertFalse(self.result()['planCompatible'])
        self.assertEqual(self.result()['changes'][0]['kind'], 'transaction_removed')

    def test_added(self):
        self.old['items'].pop()
        self.raw = json.dumps(self.old).encode()
        self.pin = hashlib.sha256(self.raw).hexdigest()
        self.assertFalse(self.result()['planCompatible'])
        self.assertEqual(self.result()['changes'][0]['kind'], 'transaction_added')

    def test_reorder_not_weakening(self):
        self.new['items'].reverse()
        result = self.result()
        self.assertTrue(result['planCompatible'])
        self.assertTrue(result['orderChanged'])
        self.assertEqual(result['changes'], [])

    def test_case_alias_same_transaction(self):
        p = self.new['items'][0]['policy']
        p['transactionHash'] = '0x' + p['transactionHash'][2:].upper()
        self.assertTrue(self.result()['planCompatible'])

    def test_pin_change_and_path_change(self):
        for field, value in (('sha256', self.old['items'][1]['sha256']),
                             ('evidence', 'missing/evidence.json')):
            with self.subTest(field=field):
                self.new = copy.deepcopy(self.old)
                self.new['items'][0][field] = value
                result = self.result()
                self.assertFalse(result['planCompatible'])
                self.assertEqual(result['changes'][0]['kind'], 'evidence_reference_changed')

    def test_duplicate_alias_rejects(self):
        self.new['items'].append(copy.deepcopy(self.new['items'][0]))
        with self.assertRaises(d.Error):
            self.result()

    def test_bad_policy_types(self):
        for field, value in (('minimumConfirmations', True), ('requireFinalized', 1),
                             ('minimumConfirmations', 0), ('minimumConfirmations', 1000001)):
            with self.subTest(field=field, value=value):
                self.new = copy.deepcopy(self.old)
                self.new['items'][0]['policy'][field] = value
                with self.assertRaises(d.Error):
                    self.result()

    def test_ambiguous_json_both_sides(self):
        for bad in (b'{"version":1,"version":1}', b'{"x":NaN}', b'\xff', b'{}'):
            with self.subTest(bad=bad):
                with self.assertRaises(d.Error):
                    d.compare(bad, self.raw, hashlib.sha256(bad).hexdigest())
                with self.assertRaises(d.Error):
                    d.compare(self.raw, bad, self.pin)

    def test_byte_bound(self):
        for bad in (bytearray(self.raw), b' ' * 90001):
            with self.assertRaises(d.Error):
                d.compare(self.raw, bad, self.pin)

    def test_invalid_pin(self):
        with self.assertRaises(d.Error):
            d.compare(self.raw, self.raw, 'bad')

    def test_no_evidence_or_network_calls_no_mutation(self):
        original = copy.deepcopy(self.new)
        with patch.object(d.b.k, 'review_file', side_effect=AssertionError('evidence')):
            with patch.object(d.b.k.p.s.RPC, 'call', side_effect=AssertionError('network')):
                self.assertTrue(self.result()['planCompatible'])
        self.assertEqual(self.new, original)

    def test_cli_demo_and_overrides(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(d.main(['--demo']), 0)
        self.assertTrue(json.loads(out.getvalue())['planCompatible'])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(d.main(['--demo', '--baseline', 'x']), 2)
            self.assertEqual(d.main(['--baseline', 'x']), 2)

    def test_cli_decline_and_safe_paths(self):
        scratch = Path('test/scratch/settlement-plan-diff')
        scratch.mkdir(parents=True, exist_ok=True)
        old, new = scratch / 'old.json', scratch / 'new.json'
        old.write_bytes(self.raw)
        self.new['items'][0]['policy']['requireFinalized'] = False
        new.write_text(json.dumps(self.new))
        args = ['--baseline', str(old), '--proposed', str(new), '--baseline-sha256', self.pin]
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(d.main(args), 1)
        self.assertEqual(json.loads(out.getvalue())['state'], 'plan_review_required')
        link = scratch / 'link.json'
        if link.is_symlink():
            link.unlink()
        link.symlink_to(old.resolve())
        for path in ('../x', '/absolute', '.hidden', str(link), str(scratch)):
            with self.subTest(path=path), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(d.main(['--baseline', path, '--proposed', str(new),
                                         '--baseline-sha256', self.pin]), 2)

    def test_unknown_fields(self):
        self.new['approval'] = True
        with self.assertRaises(d.Error):
            self.result()


if __name__ == '__main__':
    unittest.main()
