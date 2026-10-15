#!/usr/bin/env python3
"""Compare a proposed settlement batch plan with an independently pinned baseline."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location(
    'diff_batch', Path(__file__).resolve().parent.parent / 'settlement-batch' / 'batch.py')
b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b)
Error = b.Error
DEMO_SHA256 = '42674d1260722da43083cd8289840de5543dfc9f97625302ba448585083e5faf'
LIMITATIONS = ('Plan comparison only; evidence is not opened or replayed. A pass is not '
               'transaction settlement, payment approval or authorization. Retain the baseline '
               'hash independently. Replacing baseline and hash defeats this check. '
               'A stricter policy may require newly captured evidence before batch replay.')


def digest(raw):
    if type(raw) is not bytes or len(raw) > b.k.LIMIT:
        raise Error('bounded exact bytes required')
    return hashlib.sha256(raw).hexdigest()


def compare(old_raw, new_raw, baseline_sha256):
    expected = b.k.pin(baseline_sha256)
    actual = digest(old_raw)
    proposed = digest(new_raw)
    result = {'planCompatible': False, 'state': 'baseline_pin_mismatch',
              'baselineSha256': actual, 'expectedBaselineSha256': expected,
              'proposedSha256': proposed, 'evidenceChecked': False,
              'limitations': LIMITATIONS}
    # Do not interpret a replaced baseline, even if it is malformed JSON.
    if actual != expected:
        return result
    old = b.validate(b.k.p.s.strict_json(old_raw))
    new = b.validate(b.k.p.s.strict_json(new_raw))
    before = {row['policy']['transactionHash']: row for row in old}
    after = {row['policy']['transactionHash']: row for row in new}
    changes = []
    blocking = False
    for tx in sorted(before.keys() | after.keys()):
        if tx not in after:
            changes.append({'transactionHash': tx, 'kind': 'transaction_removed', 'blocking': True})
            blocking = True
            continue
        if tx not in before:
            changes.append({'transactionHash': tx, 'kind': 'transaction_added', 'blocking': True})
            blocking = True
            continue
        left, right = before[tx], after[tx]
        for field in ('minimumConfirmations', 'requireFinalized'):
            a, z = left['policy'][field], right['policy'][field]
            if a != z:
                weaker = z < a
                changes.append({'transactionHash': tx, 'kind': 'policy_weakened' if weaker else
                                'policy_strengthened', 'field': field, 'before': a, 'after': z,
                                'blocking': weaker})
                blocking |= weaker
        # Both pin and path are deliberate review boundaries. A relocation is
        # reported conservatively even if bytes would be equal; never open them.
        for field in ('sha256', 'evidence'):
            if left[field] != right[field]:
                changes.append({'transactionHash': tx, 'kind': 'evidence_reference_changed',
                                'field': field, 'blocking': True})
                blocking = True
    result.update(planCompatible=not blocking,
                  state='plan_unchanged_or_stricter' if not blocking else 'plan_review_required',
                  baselineCount=len(old), proposedCount=len(new), changes=changes,
                  orderChanged=[r['policy']['transactionHash'] for r in old] !=
                               [r['policy']['transactionHash'] for r in new])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--baseline')
    parser.add_argument('--proposed')
    parser.add_argument('--baseline-sha256')
    args = parser.parse_args(argv)
    try:
        if args.demo:
            if args.baseline or args.proposed or args.baseline_sha256:
                raise Error('demo refuses overrides')
            path = (Path(__file__).resolve().parent.parent / 'settlement-batch' /
                    'demo-manifest.json').relative_to(Path.cwd())
            old = b.k.load_bytes(path)
            result = compare(old, old, DEMO_SHA256)
            result['demoNote'] = 'Unchanged plan for two retained real ZTO transactions; no fresh chain assertion.'
        else:
            if not args.baseline or not args.proposed or not args.baseline_sha256:
                raise Error('baseline, proposed and independent baseline hash required')
            b.k.pin(args.baseline_sha256)
            result = compare(b.k.load_bytes(args.baseline), b.k.load_bytes(args.proposed),
                             args.baseline_sha256)
        encoded = json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False)
        if len(encoded.encode('ascii')) > 100000:
            raise Error('report exceeds 100 KB')
        print(encoded)
        return 0 if result['planCompatible'] else 1
    except (Error, ValueError, TypeError, KeyError, OSError, RecursionError):
        print(json.dumps({'planCompatible': False, 'state': 'input_error',
                          'reason': 'Invalid bounded plans, paths or baseline pin'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
