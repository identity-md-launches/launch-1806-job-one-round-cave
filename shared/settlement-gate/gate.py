#!/usr/bin/env python3
"""Check a retained settlement plan and replay its pinned evidence, offline."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MAX_OUTPUT = 100_000


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, HERE / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


plans = module('gate_plan_diff', 'vendor/settlement-plan-diff/plan_diff.py')
contracts = module('gate_contracts', 'vendor/json_contract.py')
# Fixed, reviewed protocol shape; incoming plans cannot select or relax this.
POLICY = {'type': 'object', 'required': ['transactionHash', 'minimumConfirmations', 'requireFinalized'],
          'additionalProperties': False, 'properties': {
              'transactionHash': {'type': 'string', 'pattern': '^0x[0-9a-fA-F]{64}$'},
              'minimumConfirmations': {'type': 'integer', 'minimum': 1, 'maximum': 1000000},
              'requireFinalized': {'type': 'boolean'}}}
ITEM = {'type': 'object', 'required': ['evidence', 'sha256', 'policy'],
        'additionalProperties': False, 'properties': {
            'evidence': {'type': 'string', 'minLength': 1},
            'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'policy': POLICY}}
CONTRACT = contracts.prepare({'type': 'object', 'required': ['version', 'items'],
    'additionalProperties': False, 'properties': {
        'version': {'type': 'integer', 'enum': [1]},
        'items': {'type': 'array', 'minItems': 1, 'maxItems': 32, 'items': ITEM}}})
LIMITATIONS = ('Historical provider assertions only, not consensus or trie proofs. '
    'Retain the baseline hash independently. No payment amount, freshness, ownership, '
    'signing authority or cross-run deduplication. Compatible stricter plans can still '
    'fail evidence replay. No baseline is updated and nothing is sent.')


def render(report):
    text = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + '\n'
    if len(text.encode('ascii')) > MAX_OUTPUT:
        raise ValueError('complete gate report exceeds 100000 bytes')
    return text


def review(old_raw, new_raw, baseline_pin):
    """Use the SAME captured proposed bytes for comparison and evidence replay."""
    plans.b.k.pin(baseline_pin)
    actual = plans.digest(old_raw)
    proposed_hash = plans.digest(new_raw)
    result = {'accepted': False, 'state': 'baseline_pin_mismatch',
              'baselineSha256': actual, 'proposedSha256': proposed_hash,
              'expectedBaselineSha256': baseline_pin, 'evidenceChecked': False,
              'limitations': LIMITATIONS}
    # Do not interpret unpinned baseline bytes or open any evidence on rejection.
    if actual != baseline_pin:
        return result
    before = plans.b.k.p.s.strict_json(old_raw)
    after = plans.b.k.p.s.strict_json(new_raw)
    diagnostics = {'baseline': contracts.validate(before, CONTRACT),
                   'proposed': contracts.validate(after, CONTRACT)}
    result['structure'] = {'valid': not any(diagnostics.values()), 'diagnostics': diagnostics}
    if not result['structure']['valid']:
        result['state'] = 'structural_review_required'
        render(result)
        return result
    comparison = plans.compare(old_raw, new_raw, baseline_pin)
    result['planReview'] = comparison
    if not comparison['planCompatible']:
        result['state'] = 'plan_review_required'
        render(result)
        return result
    evidence = plans.b.review_manifest_bytes(new_raw)
    # review_manifest_bytes validates the same entire plan and checks every row.
    result.update(evidenceChecked=True, settlementReview=evidence,
                  accepted=evidence['accepted'],
                  state='plan_and_settlement_match' if evidence['accepted'] else
                        'input_error' if evidence['state'] == 'input_error' else 'settlement_review_required')
    render(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', help='visible workspace-relative baseline plan')
    parser.add_argument('proposed', help='visible workspace-relative proposed plan')
    parser.add_argument('--baseline-sha256', required=True, help='independently retained baseline hash')
    args = parser.parse_args(argv)
    try:
        plans.b.k.pin(args.baseline_sha256)
        # Capture baseline once. Reject pin before opening proposed plan.
        old = plans.b.k.load_bytes(args.baseline)
        if hashlib.sha256(old).hexdigest() != args.baseline_sha256:
            result = {'accepted': False, 'state': 'baseline_pin_mismatch',
                      'evidenceChecked': False,
                      'actualSha256': hashlib.sha256(old).hexdigest(),
                      'expectedBaselineSha256': args.baseline_sha256}
        else:
            new = old if args.proposed == args.baseline else plans.b.k.load_bytes(args.proposed)
            result = review(old, new, args.baseline_sha256)
        sys.stdout.write(render(result))
        return 0 if result['accepted'] else 2 if result['state'] == 'input_error' else 1
    except (ValueError, OSError, TypeError, KeyError, RecursionError):
        sys.stdout.write('{"accepted":false,"state":"input_error","evidenceChecked":false}\n')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
