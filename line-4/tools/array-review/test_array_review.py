"""Ordered array commitments, strict expectations, CLI and offline boundaries."""
import copy
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from array_review import review, render
from typed_digest import TypedDataError, digest, keccak256, load_workspace_json, loads_bounded

HERE = Path(__file__).resolve().parent
EXPECTED = '0xafd46e38940aa3cad45ccacf9ebbea5686570df15dcbf08e79119502d95605ba'


def word(n):
    return '0x' + (n % (1 << 256)).to_bytes(32, 'big').hex()


def request(kind='uint256[]', values=None):
    return {'types': {'EIP712Domain': [], 'Batch': [{'name': 'items', 'type': kind}]},
            'primaryType': 'Batch', 'domain': {},
            'message': {'items': [7, 8, 7] if values is None else values}}


def policy(kind='uint256[]', words=None):
    return {'arrays': [{'path': '/message/items', 'declaredType': kind,
                        'elementWords': [word(7), word(8), word(7)] if words is None else words}]}


class ArrayTests(unittest.TestCase):
    def test_historical_wrapper(self):
        result = review(load_workspace_json(HERE/'zto-batch.json'),
                        load_workspace_json(HERE/'zto-arrays.json'), EXPECTED)
        self.assertTrue(result['checksPass'])
        self.assertEqual(result['arrays'][1]['repeatedWordPositions'], [[0, 2]])

    def test_explicit_words_and_hash_preimage(self):
        result = review(request(), policy())
        row = result['arrays'][0]
        self.assertEqual(row['elementWords'], [word(7), word(8), word(7)])
        raw = b''.join(n.to_bytes(32, 'big') for n in (7, 8, 7))
        self.assertEqual(row['arrayHash'], '0x' + keccak256(raw).hex())
        self.assertNotEqual(row['arrayHash'], '0x' + keccak256((3).to_bytes(32, 'big') + raw).hex())
        self.assertTrue(result['checksPass'])

    def test_reorder_and_length_changes_reject(self):
        for values in ([8, 7, 7], [7, 8], [7, 8, 7, 7], []):
            result = review(request(values=values), policy())
            self.assertFalse(result['checksPass'])
            self.assertEqual(result['changedArrays'], ['/message/items'])

    def test_fixed_dynamic_same_array_word_different_declaration(self):
        dynamic, fixed = review(request()), review(request('uint256[3]'))
        self.assertEqual(dynamic['arrays'][0]['arrayHash'], fixed['arrays'][0]['arrayHash'])
        self.assertNotEqual(dynamic['digest'], fixed['digest'])
        self.assertFalse(review(request('uint256[3]'), policy())['checksPass'])

    def test_empty_keccak_published_vector(self):
        result = review(request(values=[]), policy(words=[]))
        self.assertTrue(result['checksPass'])
        self.assertEqual(result['arrays'][0]['arrayHash'],
                         '0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470')

    def test_nested_arrays_all_levels_and_repeated_inner_hash(self):
        result = review(request('uint256[][3]', [[7], [], [7]]))
        rows = result['arrays']
        self.assertEqual([r['path'] for r in rows],
                         ['/message/items', '/message/items/0', '/message/items/1', '/message/items/2'])
        self.assertEqual(rows[0]['elementWords'], [r['arrayHash'] for r in rows[1:]])
        self.assertEqual(rows[0]['repeatedWordPositions'], [[0, 2]])
        self.assertEqual(rows[2]['length'], 0)

    def test_nested_expectations_must_include_every_path(self):
        data = request('uint256[][]', [[7]])
        first_hash = '0x' + keccak256((7).to_bytes(32, 'big')).hex()
        expected = policy('uint256[][]', [first_hash])
        result = review(data, expected)
        self.assertFalse(result['checksPass'])
        self.assertEqual(result['unexpectedArrays'], ['/message/items/0'])
        expected['arrays'].append({'path': '/message/items/0', 'declaredType': 'uint256[]', 'elementWords': [word(7)]})
        self.assertTrue(review(data, expected)['checksPass'])

    def test_struct_words_and_arrays_within_structs(self):
        data = request('Item[]', [{'sub': [7]}, {'sub': []}])
        data['types']['Item'] = [{'name': 'sub', 'type': 'uint256[]'}]
        result = review(data)
        self.assertEqual([r['path'] for r in result['arrays']],
                         ['/message/items', '/message/items/0/sub', '/message/items/1/sub'])
        th = keccak256(b'Item(uint256[] sub)')
        sub = keccak256((7).to_bytes(32, 'big'))
        self.assertEqual(result['arrays'][0]['elementWords'][0], '0x'+keccak256(th+sub).hex())

    def test_string_bytes_words_and_no_unicode_normalization(self):
        strings = review(request('string[]', ['abc', 'abc', 'a\u200bbc']))['arrays'][0]
        self.assertEqual(strings['elementWords'][0], '0x'+keccak256(b'abc').hex())
        self.assertEqual(strings['repeatedWordPositions'], [[0, 1]])
        blobs = review(request('bytes[]', ['0x616263', '0x']))['arrays'][0]
        self.assertEqual(strings['elementWords'][0], blobs['elementWords'][0])
        self.assertFalse(review(request('bytes[]', ['0x616263']),
                                policy('string[]', [strings['elementWords'][0]]))['checksPass'])

    def test_signed_int_and_fixed_bytes_padding(self):
        signed = review(request('int8[]', [-1, -128]))['arrays'][0]
        self.assertEqual(signed['elementWords'], [word(-1), word(-128)])
        fixed = review(request('bytes2[]', ['0xabcd']))['arrays'][0]
        self.assertEqual(fixed['elementWords'], ['0xabcd'+'00'*30])

    def test_finite_recursive_values(self):
        data = {'types': {'EIP712Domain': [], 'Node': [{'name': 'children', 'type': 'Node[]'}]},
                'primaryType': 'Node', 'domain': {}, 'message': {'children': [{'children': []}]}}
        self.assertEqual(len(review(data)['arrays']), 2)

    def test_domain_arrays_are_inspected(self):
        data = request()
        data['types']['EIP712Domain'] = [{'name': 'custom', 'type': 'bool[]'}]
        data['domain'] = {'custom': [True, False]}
        result = review(data, policy())
        self.assertEqual(result['arrays'][0]['path'], '/domain/custom')
        self.assertEqual(result['unexpectedArrays'], ['/domain/custom'])

    def test_no_arrays_is_explicit_not_disabled(self):
        data = load_workspace_json(HERE/'zto-payment.json')
        self.assertTrue(review(data, {'arrays': []})['checksPass'])
        self.assertIsNone(review(data)['checksPass'])
        result = review(data, policy())
        self.assertFalse(result['checksPass'])
        self.assertEqual(result['missingArrays'], ['/message/items'])

    def test_scalar_outside_arrays_requires_complete_digest(self):
        data = request()
        data['types']['Batch'].append({'name': 'nonce', 'type': 'uint256'})
        data['message']['nonce'] = 1
        old = digest(data)['digest']
        data['message']['nonce'] = 2
        self.assertTrue(review(data, policy())['checksPass'])
        self.assertFalse(review(data, policy(), old)['checksPass'])
        self.assertFalse(review(data, expected_digest=old)['checksPass'])

    def test_expected_list_order_irrelevant_word_case_normalized(self):
        data = load_workspace_json(HERE/'zto-batch.json')
        wanted = load_workspace_json(HERE/'zto-arrays.json')
        wanted['arrays'].reverse()
        for row in wanted['arrays']:
            row['elementWords'] = ['0x'+w[2:].upper() for w in row['elementWords']]
        self.assertTrue(review(data, wanted, '0x'+EXPECTED[2:].upper())['checksPass'])

    def test_invalid_policies_fail_closed(self):
        invalid = [None, [], {}, {'arrays': None}, {'arrays': [], 'extra': 1}]
        for field, value in [('path', '/message/items/01'), ('path', '../items'),
                             ('path', None), ('declaredType', 'uint'), ('declaredType', 'Missing[]'),
                             ('declaredType', 'uint256[0]'), ('elementWords', None),
                             ('elementWords', ['0x07']), ('elementWords', [True])]:
            bad = policy(); bad['arrays'][0][field] = value; invalid.append(bad)
        bad = policy();bad['arrays'].append(copy.deepcopy(bad['arrays'][0]));invalid.append(bad)
        bad = policy();bad['arrays'][0]['extra'] = 1;invalid.append(bad)
        invalid.append(policy('uint256[2]'))
        for bad in invalid:
            with self.subTest(policy=bad), self.assertRaises((ValueError, TypeError)):
                review(request(), bad)

    def test_invalid_values_unused_declarations_and_cycles_reject(self):
        invalid = [request(values=[True]), request('uint8[]', [256]), request('uint256[2]', [7])]
        bad = request();bad['types']['Unused'] = [{'name':'x','type':'Missing'}];invalid.append(bad)
        bad = request();bad['message']['items'].append(bad['message']);invalid.append(bad)
        for bad in invalid:
            with self.subTest(data=repr(bad)[:80]), self.assertRaises(ValueError):
                review(bad)

    def test_word_and_array_limits(self):
        with self.assertRaisesRegex(TypedDataError, '512 element words'):
            review(request(values=list(range(513))))
        with self.assertRaisesRegex(TypedDataError, '512 element words'):
            review(request(), policy(words=[word(1)]*513))
        with self.assertRaisesRegex(TypedDataError, '128 arrays'):
            review(request('uint256[][]', [[] for _ in range(128)]))
        with self.assertRaisesRegex(TypedDataError, 'too many expected arrays'):
            review(request(), {'arrays': [{}]*129})

    def test_output_limit_includes_final_newline(self):
        text = render({'x': 'y'})
        with patch('array_review.MAX_REPORT_BYTES', len(text.encode('ascii'))):
            self.assertEqual(text, render({'x': 'y'}))
        with patch('array_review.MAX_REPORT_BYTES', len(text.encode('ascii'))-1):
            with self.assertRaisesRegex(TypedDataError, 'output limit'):
                render({'x': 'y'})
        with patch('array_review.MAX_REPORT_BYTES', 10):
            with self.assertRaises(TypedDataError): review(request())

    def test_strict_json_reader(self):
        for raw in (b'{"arrays":[],"arrays":[]}', b'NaN', b'1.0', b'"\\ud800"'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): loads_bounded(raw)

    def test_no_network_and_no_mutation(self):
        data, wanted = request(), policy()
        before = copy.deepcopy((data, wanted))
        with patch.object(socket, 'socket', side_effect=AssertionError('network disabled')):
            report = review(data, wanted)
        report['arrays'][0]['elementWords'].clear()
        self.assertEqual((data, wanted), before)


class CliTests(unittest.TestCase):
    def call(self, input='zto-batch.json', *args):
        return subprocess.run([sys.executable, '-B', str(HERE/'array_review.py'), str(HERE/input),
                               *map(str, args)], capture_output=True, text=True, timeout=20)

    def test_accept_reject_inspect(self):
        for name, code in [('zto-batch.json', 0), ('zto-reordered.json', 1)]:
            result = self.call(name, '--expect', HERE/'zto-arrays.json', '--digest-expect', EXPECTED)
            self.assertEqual(result.returncode, code, result.stderr)
            self.assertEqual(json.loads(result.stdout)['checksPass'], code == 0)
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(json.loads(result.stdout)['checksPass'])

    def test_bad_digest_escapes_error_and_no_partial_stdout(self):
        result = self.call('zto-batch.json', '--digest-expect', 'bad\x1b[31m')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertNotIn('\x1b', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_null_duplicate_unsafe_policy_files(self):
        with tempfile.TemporaryDirectory(prefix='array-tests-', dir=HERE) as name:
            folder = Path(name); bad = folder/'bad.json'
            for raw in (b'null', b'{"arrays":[],"arrays":[]}'):
                bad.write_bytes(raw)
                result = self.call('zto-batch.json', '--expect', bad)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, '')
            link = folder/'linked.json';link.symlink_to(HERE/'zto-arrays.json')
            for path in (link, '../outside.json'):
                result = self.call('zto-batch.json', '--expect', path)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
