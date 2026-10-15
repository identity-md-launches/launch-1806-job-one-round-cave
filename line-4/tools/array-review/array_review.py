#!/usr/bin/env python3
"""Review ordered EIP-712 array words offline; never signs or sends anything."""
import argparse
import json
import re
import sys

from typed_digest import (ARRAY, Encoder, TypedDataError, digest, keccak256,
                          load_workspace_json, parse_hex, valid_type, validate_tree)

MAX_REPORT_BYTES = 100_000
MAX_ARRAYS = 128
MAX_WORDS = 512
PATH = re.compile(r'^/(domain|message)(/([A-Za-z_][A-Za-z0-9_]*|0|[1-9][0-9]*))+$')
_UNSET = object()


def render(report):
    text = json.dumps(report, ensure_ascii=True, indent=2) + '\n'
    if len(text.encode('ascii')) > MAX_REPORT_BYTES:
        raise TypedDataError('array review exceeds 100000-byte output limit')
    return text


def expected_arrays(policy, encoder):
    """Expectations pin words directly, without deriving them from the request."""
    validate_tree(policy)
    if not isinstance(policy, dict) or set(policy) != {'arrays'} or not isinstance(policy['arrays'], list):
        raise TypedDataError('expectations need exactly an arrays list')
    if len(policy['arrays']) > MAX_ARRAYS:
        raise TypedDataError('too many expected arrays')
    found, word_count = {}, 0
    for row in policy['arrays']:
        if not isinstance(row, dict) or set(row) != {'path', 'declaredType', 'elementWords'}:
            raise TypedDataError('each expected array needs path, declaredType and elementWords')
        path, kind, words = row['path'], row['declaredType'], row['elementWords']
        if not isinstance(path, str) or not PATH.fullmatch(path) or path in found:
            raise TypedDataError('expected paths must be unique canonical array paths')
        if (not isinstance(kind, str) or len(kind) > 256 or not ARRAY.fullmatch(kind)
                or not valid_type(kind, encoder.types)):
            raise TypedDataError('expected declaredType must be an array type')
        if not isinstance(words, list):
            raise TypedDataError('expected elementWords must be a list')
        word_count += len(words)
        if word_count > MAX_WORDS:
            raise TypedDataError('expected arrays exceed 512 element words')
        array = ARRAY.fullmatch(kind)
        if array.group(2) and len(words) != int(array.group(2)):
            raise TypedDataError('expected words do not fit fixed array length')
        found[path] = {'declaredType': kind,
                       'elementWords': ['0x' + parse_hex(w, 32).hex() for w in words]}
    return found


def review(data, policy=_UNSET, expected_digest=None):
    hashes = digest(data)  # Validate every declaration/value before producing output.
    encoder = Encoder(data['types'])
    wanted = expected_arrays(policy, encoder) if policy is not _UNSET else None
    expected_hash = parse_hex(expected_digest, 32) if expected_digest is not None else None
    arrays, total_words = [], 0

    def visit(kind, value, path):
        nonlocal total_words
        array = ARRAY.fullmatch(kind)
        if array:
            total_words += len(value)
            if len(arrays) >= MAX_ARRAYS or total_words > MAX_WORDS:
                raise TypedDataError('review exceeds 128 arrays or 512 element words')
            inner = array.group(1)
            words = [encoder.value_word(inner, item) for item in value]
            positions = {}
            for index, word in enumerate(words):
                positions.setdefault(word.hex(), []).append(index)
            row = {'path': path, 'declaredType': kind, 'elementType': inner,
                   'length': len(value), 'elementWords': ['0x' + w.hex() for w in words],
                   'arrayHash': '0x' + keccak256(b''.join(words)).hex(),
                   'repeatedWordPositions': [indices for indices in positions.values() if len(indices) > 1]}
            arrays.append(row)
            render({'arrays': arrays})
            for index, child in enumerate(value):
                visit(inner, child, path + '/' + str(index))
        elif kind in encoder.types:
            for field in encoder.types[kind]:
                visit(field['type'], value[field['name']], path + '/' + field['name'])

    visit('EIP712Domain', data['domain'], '/domain')
    visit(data['primaryType'], data['message'], '/message')
    report = {'reviewVersion': 1, **hashes, 'arrays': arrays,
              'arrayExpectationProvided': wanted is not None,
              'digestExpectationProvided': expected_hash is not None,
              'interpretation': 'Element words are ordered, zero-based, and always 32 bytes. '
              'Array hashes are Keccak-256 of concatenated element words, without a length prefix. '
              'Nested arrays contribute hashes; structs contribute hashStruct. Repeated words are '
              'observations, not errors or proof of duplicate raw values. Array expectations pin '
              'every observed path, declared array type and ordered word; they do not pin scalar '
              'fields outside arrays or complete schema. Use a separately controlled complete '
              'digest and schema for those checks. No match authorizes signing or payment.'}
    if wanted is not None:
        actual = {r['path']: {'declaredType': r['declaredType'], 'elementWords': r['elementWords']}
                  for r in arrays}
        report.update(unexpectedArrays=sorted(actual.keys() - wanted.keys()),
                      missingArrays=sorted(wanted.keys() - actual.keys()),
                      changedArrays=sorted(p for p in actual.keys() & wanted.keys() if actual[p] != wanted[p]))
        report['arraysMatchExpected'] = actual == wanted
    if expected_hash is not None:
        report['digestMatchesExpected'] = hashes['digest'][2:] == expected_hash.hex()
    report['checksPass'] = (None if wanted is None and expected_hash is None else
                            report.get('arraysMatchExpected', True) and report.get('digestMatchesExpected', True))
    render(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', help='typed-data JSON beneath cwd')
    parser.add_argument('--expect', help='separately prepared array words JSON beneath cwd')
    parser.add_argument('--digest-expect', help='separately retained 32-byte complete digest')
    args = parser.parse_args(argv)
    try:
        data = load_workspace_json(args.input)
        policy = load_workspace_json(args.expect) if args.expect is not None else _UNSET
        report = review(data, policy, args.digest_expect)
        print(render(report), end='')
        return 1 if report['checksPass'] is False else 0
    except (ValueError, OSError, RecursionError) as exc:
        print('array-review: ' + json.dumps(str(exc), ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
