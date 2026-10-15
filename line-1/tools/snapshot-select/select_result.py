#!/usr/bin/env python3
"""Select a result value from a validated portable Ethereum snapshot, offline."""
import argparse
import json
from pathlib import Path
import re
import runpy
import sys

B = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                       'bounded-rpc-snapshot' / 'snapshot.py'))
MAX_POINTER = 4096
MAX_DEPTH = 64
MAX_OUTPUT = 100_000


class SelectionError(ValueError):
    pass


def tokens(pointer):
    if not isinstance(pointer, str) or len(pointer.encode('utf-8')) > MAX_POINTER:
        raise SelectionError('pointer must be a string of at most 4096 UTF-8 bytes')
    if pointer == '':
        return []
    if not pointer.startswith('/'):
        raise SelectionError('use an empty pointer or one starting with /; URI fragments are unsupported')
    pieces = pointer[1:].split('/')
    if len(pieces) > MAX_DEPTH:
        raise SelectionError('pointer exceeds 64 steps')
    decoded = []
    for piece in pieces:
        if re.search(r'~(?![01])', piece):
            raise SelectionError('invalid JSON Pointer escape; use ~0 or ~1')
        decoded.append(piece.replace('~1', '/').replace('~0', '~'))
    return decoded


def select(value, pointer):
    for step, token in enumerate(tokens(pointer), 1):
        if type(value) is dict:
            if token not in value:
                raise SelectionError(f'object member missing at step {step}')
            value = value[token]
        elif type(value) is list:
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise SelectionError(f'noncanonical array index at step {step}')
            # Compare text before int conversion, including arbitrarily long tokens.
            last = str(len(value) - 1)
            if not value or len(token) > len(last) or (len(token) == len(last) and token > last):
                raise SelectionError(f'array index out of range at step {step}')
            value = value[int(token)]
        else:
            raise SelectionError(f'cannot descend through scalar at step {step}')
    return value


def value_type(value, depth=0):
    if depth > MAX_DEPTH:
        raise SelectionError('selected value exceeds 64 nesting levels')
    types = {type(None): 'null', bool: 'boolean', int: 'integer',
             str: 'string', list: 'array', dict: 'object'}
    if type(value) not in types:
        raise SelectionError('fractional JSON numbers are unsupported; preserve quantities as strings')
    if isinstance(value, (list, dict)):
        for child in (value.values() if isinstance(value, dict) else value):
            value_type(child, depth + 1)
    return types[type(value)]


def report(snapshot, pointer):
    value = select(snapshot['response']['result'], pointer)
    return {'schema': 'line1-snapshot-selection-v1',
            'request': snapshot['request'],
            'rpc_url': snapshot['rpc_url'],
            'captured_at_utc': snapshot['captured_at_utc'],
            'response_sha256': snapshot['response_sha256'],
            'result_pointer': pointer, 'value_type': value_type(value), 'value': value,
            'meaning': 'Selected saved provider response; not a state proof or freshness check.'}


def render(report_value):
    raw = json.dumps(report_value, ensure_ascii=True, allow_nan=False,
                     separators=(',', ':')) + '\n'
    if len(raw.encode('ascii')) > MAX_OUTPUT:
        raise SelectionError('selection report exceeds 100000 bytes; select a smaller value')
    return raw


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', help='visible relative workspace snapshot path')
    parser.add_argument('--pointer', default='', help='RFC 6901 pointer relative to response.result')
    args = parser.parse_args(argv)
    try:
        tokens(args.pointer)
        snapshot = B['verify_snapshot'](args.snapshot)
        sys.stdout.write(render(report(snapshot, args.pointer)))
        return 0
    except (SelectionError, B['SnapshotError'], ValueError, OSError,
            RecursionError, TypeError, OverflowError) as exc:
        print('snapshot-select: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
