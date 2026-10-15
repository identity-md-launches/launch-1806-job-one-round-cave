"""Regression tests for complete plan/evidence gating; no network required."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

import gate as g

HERE = Path(__file__).resolve().parent
PIN = '751fa0b816bfee7a209166f8844365b629bcc5a0bbedf090dd9b3755f330f5db'


class GateTests(unittest.TestCase):
    def setUp(self):
        self.raw = (HERE/'baseline.json').read_bytes()
        self.plan = json.loads(self.raw)

    def run_plan(self, plan):
        return g.review(self.raw, (json.dumps(plan)+'\n').encode(), PIN)

    def test_real_zto_evidence_offline(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('network disabled')):
            r = g.review(self.raw, self.raw, PIN)
        self.assertTrue(r['accepted'])
        self.assertTrue(r['evidenceChecked'])
        self.assertEqual(r['settlementReview']['acceptedCount'], 2)
        self.assertEqual(r['settlementReview']['manifestSha256'], PIN)

    def test_weaker_finality_never_opens_evidence(self):
        self.plan['items'][0]['policy']['requireFinalized'] = False
        with patch.object(g.plans.b, 'review_manifest_bytes', side_effect=AssertionError('replayed')):
            r = self.run_plan(self.plan)
        self.assertFalse(r['accepted'])
        self.assertFalse(r['evidenceChecked'])
        self.assertEqual(r['state'], 'plan_review_required')

    def test_stricter_plan_is_not_settlement_acceptance(self):
        self.plan['items'][0]['policy']['minimumConfirmations'] = 1000000
        r = self.run_plan(self.plan)
        self.assertTrue(r['planReview']['planCompatible'])
        self.assertTrue(r['evidenceChecked'])
        self.assertFalse(r['accepted'])

    def test_structural_diagnostics_locate_all_violations(self):
        self.plan['items'][0]['policy']['minimumConfirmations'] = True
        self.plan['items'][1]['policy']['requireFinalized'] = 'yes'
        with patch.object(g.plans.b, 'review_manifest_bytes', side_effect=AssertionError('replayed')):
            r = self.run_plan(self.plan)
        self.assertEqual(r['state'], 'structural_review_required')
        self.assertEqual([e['path'] for e in r['structure']['diagnostics']['proposed']],
                         ['/items/0/policy/minimumConfirmations', '/items/1/policy/requireFinalized'])
        self.assertFalse(r['evidenceChecked'])

    def test_pin_mismatch_precedes_parse(self):
        with patch.object(g.plans.b.k.p.s, 'strict_json', side_effect=AssertionError('parsed')):
            r = g.review(b'bad baseline', b'bad proposed', PIN)
        self.assertEqual(r['state'], 'baseline_pin_mismatch')
        self.assertFalse(r['accepted'])

    def test_reorder_preserves_entire_set(self):
        self.plan['items'].reverse()
        r = self.run_plan(self.plan)
        self.assertTrue(r['accepted'])
        self.assertTrue(r['planReview']['orderChanged'])

    def test_removal_addition_pin_or_path_replacement_block(self):
        changes = []
        p = copy.deepcopy(self.plan);p['items'].pop();changes.append(p)
        p = copy.deepcopy(self.plan);p['items'][0]['sha256'] = p['items'][1]['sha256'];changes.append(p)
        p = copy.deepcopy(self.plan);p['items'][0]['evidence'] = 'missing.json';changes.append(p)
        p = copy.deepcopy(self.plan);p['items'][0]['policy']['transactionHash'] = '0x'+'12'*32;changes.append(p)
        for p in changes:
            with self.subTest(plan=p), patch.object(g.plans.b, 'review_manifest_bytes', side_effect=AssertionError('replayed')):
                self.assertFalse(self.run_plan(p)['accepted'])

    def test_duplicate_transaction_cannot_hide(self):
        self.plan['items'].append(copy.deepcopy(self.plan['items'][0]))
        with self.assertRaises(ValueError): self.run_plan(self.plan)

    def test_matching_plan_does_not_hide_replaced_evidence(self):
        real = g.plans.b.k.load_bytes
        def replaced(name):
            raw = real(name)
            return raw + b'\n' if str(name).endswith('evidence-1.json') else raw
        with patch.object(g.plans.b.k, 'load_bytes', side_effect=replaced):
            r = g.review(self.raw, self.raw, PIN)
        self.assertFalse(r['accepted'])
        self.assertEqual(r['settlementReview']['acceptedCount'], 1)
        self.assertEqual(len(r['settlementReview']['items']), 2)

    def test_complete_proposed_bytes_replayed_once(self):
        new = json.dumps(self.plan, separators=(',', ':')).encode()
        with patch.object(g.plans.b, 'review_manifest_bytes', wraps=g.plans.b.review_manifest_bytes) as replay:
            r = g.review(self.raw, new, PIN)
        replay.assert_called_once_with(new)
        self.assertEqual(r['proposedSha256'], hashlib.sha256(new).hexdigest())
        self.assertTrue(r['accepted'])

    def test_cli_exits_and_baseline_capture_once(self):
        name = str((HERE/'baseline.json').relative_to(Path.cwd()))
        with contextlib.redirect_stdout(io.StringIO()) as out, patch.object(g.plans.b.k, 'load_bytes', wraps=g.plans.b.k.load_bytes) as read:
            self.assertEqual(g.main([name, name, '--baseline-sha256', PIN]), 0)
        self.assertTrue(json.loads(out.getvalue())['accepted'])
        self.assertEqual([c.args[0] for c in read.call_args_list].count(name), 1)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(g.main([name, 'absent.json', '--baseline-sha256', 'bad']), 2)
            self.assertEqual(g.main([name, 'absent.json', '--baseline-sha256', '1'*64]), 1)
            self.assertEqual(g.main([name, 'absent.json', '--baseline-sha256', PIN]), 2)

    def test_cli_unsafe_paths_refused(self):
        name = str((HERE/'baseline.json').relative_to(Path.cwd()))
        for bad in ('../outside.json', '/absolute', '.hidden', name+'/child'):
            with self.subTest(path=bad), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(g.main([bad, name, '--baseline-sha256', PIN]), 2)

    def test_bounds_strict_json_null_and_unknown_fields(self):
        for raw in (b'null',b'{"version":1,"version":1}',b'{"items":NaN}',b' '*90001):
            with self.subTest(raw=raw[:40]):
                try: r = g.review(self.raw, raw, PIN)
                except ValueError: continue
                self.assertFalse(r['accepted'])
        self.plan['unknown'] = True
        self.assertEqual(self.run_plan(self.plan)['state'], 'structural_review_required')

    def test_immutable_and_whole_output_bound(self):
        before = copy.deepcopy(self.plan)
        self.run_plan(self.plan)
        self.assertEqual(self.plan, before)
        text = g.render({'ok':True})
        with patch.object(g, 'MAX_OUTPUT', len(text.encode())-1):
            with self.assertRaises(ValueError): g.render({'ok':True})
            with self.assertRaises(ValueError): g.review(self.raw,self.raw,PIN)


if __name__ == '__main__':
    unittest.main(verbosity=2)
