#!/usr/bin/env python3
"""Emit offline JSON contract diagnostics as SARIF 2.1.0 on stdout."""
import argparse
import json
from pathlib import Path
import sys
import types
from urllib.parse import quote

MAX_OUTPUT_BYTES = 100_000


def dependencies():
    # Fixed repository code only. Caller input is read by the inherited
    # descriptor-relative no-follow reader, never by Python's module importer.
    source = Path(__file__).absolute().parent.parent / 'source-context' / 'show.py'
    relative = source.relative_to(Path.cwd()).as_posix()
    # Reuse the established safe bootstrap without importing arbitrary inputs.
    # The descriptor traversal follows the existing sibling bootstrap.
    import os
    import stat
    if any(not p or p.startswith('.') for p in relative.split('/')):
        raise ValueError('run inside the workspace containing the sibling tools')
    directory = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    leaf = None
    try:
        parts = relative.split('/')
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                       dir_fd=directory)
        if not stat.S_ISREG(os.fstat(leaf).st_mode):
            raise ValueError('trusted sibling must be a regular file')
        chunks, remaining = [], 1_000_001
        while remaining:
            chunk = os.read(leaf, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        code = b''.join(chunks)
        if len(code) > 1_000_000:
            raise ValueError('trusted sibling exceeds byte limit')
    finally:
        if leaf is not None:
            os.close(leaf)
        os.close(directory)
    module = types.ModuleType('sarif_source_context')
    module.__file__ = str(source)
    exec(compile(code, str(source), 'exec'), module.__dict__)
    return module


def physical(location, artifact_index):
    present = location['present']
    span = location['value'] if present else location['anchor']['value']
    start, end = span['start'], span['end']
    return {
        'physicalLocation': {
            'artifactLocation': {'uri': quote(location['file'], safe='/'),
                                 'index': artifact_index},
            'region': {'startLine': start['line'], 'startColumn': start['column'],
                       'endLine': end['line'], 'endColumn': end['column'],
                       'byteOffset': start['byte_offset'],
                       'byteLength': end['byte_offset'] - start['byte_offset']}},
        'properties': {'kind': 'value' if present else 'missing_value_parent_anchor',
                       **({} if present else {'anchorPath': location['anchor']['path']})}}


def render(report):
    """Map every inherited error, preserving order and its full diagnostic data."""
    rule_names = sorted({error['rule'] for error in report['errors']})
    rules = [{'id': 'json-contract/' + rule, 'name': rule,
              'shortDescription': {'text': 'JSON structural contract: ' + rule}}
             for rule in rule_names]
    artifacts, indices = [], {}
    for role in ('document', 'contract'):
        identity = report['sources'][role]
        name = identity['file']
        if name not in indices:
            indices[name] = len(artifacts)
            artifacts.append({'location': {'uri': quote(name, safe='/')},
                              'length': identity['bytes'],
                              'hashes': {'sha-256': identity['sha256']}})
    results = []
    for error in report['errors']:
        primary = physical(error['document_source'], indices[report['sources']['document']['file']])
        related = physical(error['contract_source'], indices[report['sources']['contract']['file']])
        related['id'] = 1
        related['message'] = {'text': 'Rejecting contract rule at ' + error['contract_path']}
        # Missing values deliberately select the containing object, and the
        # diagnostic explicitly says so. No invented missing-token coordinates.
        message = error['message'] + '; JSON Pointer ' + json.dumps(error['path'], ensure_ascii=True)
        if not error['document_source']['present']:
            message += '; missing value: region selects its parent object'
        results.append({'ruleId': 'json-contract/' + error['rule'],
                        'ruleIndex': rule_names.index(error['rule']), 'level': 'error',
                        'message': {'text': message}, 'locations': [primary],
                        'relatedLocations': [related],
                        'properties': {'diagnostic': {
                            k: v for k, v in error.items() if not k.endswith('_context')}}})
    return {'version': '2.1.0',
            '$schema': 'https://json.schemastore.org/sarif-2.1.0.json',
            'runs': [{'tool': {'driver': {'name': 'Offline JSON contract reviewer',
                                        'version': '1.0.0', 'rules': rules}},
                      'columnKind': 'unicodeCodePoints', 'artifacts': artifacts,
                      'invocations': [{'executionSuccessful': True}],
                      'results': results,
                      'properties': {'structurallyValid': report['valid'],
                                     'errorCount': report['error_count'],
                                     'sources': report['sources'],
                                     'limitedContractLanguage': True}}]}


def encode(value):
    pieces, size = [], 0
    for chunk in json.JSONEncoder(ensure_ascii=True, allow_nan=False, indent=2).iterencode(value):
        size += len(chunk)
        if size + 1 > MAX_OUTPUT_BYTES:
            raise ValueError('complete SARIF exceeds 100,000 bytes; no report emitted')
        pieces.append(chunk)
    return ''.join(pieces) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', help='trusted relative workspace contract')
    parser.add_argument('document', help='relative workspace JSON document')
    parser.add_argument('--contract-sha256')
    parser.add_argument('--document-sha256')
    args = parser.parse_args(argv)
    try:
        context = dependencies()
        report = context.inspect(*context.dependencies(), args.contract, args.document,
                                 args.contract_sha256, args.document_sha256)
        output = encode(render(report))
        sys.stdout.write(output)
        return 0 if report['valid'] else 1
    except (ValueError, OSError, RecursionError, KeyError, IndexError) as exc:
        sys.stderr.write(json.dumps({'status': 'input_or_output_error',
                                     'error': str(exc)[:1000]}, ensure_ascii=True) + '\n')
        return 2


if __name__ == '__main__':
    sys.exit(main())
