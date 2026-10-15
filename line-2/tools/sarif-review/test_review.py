"""Offline SARIF interoperability and boundary regressions; fixtures in scratch."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('sarif_review', Path(__file__).with_name('review.py'))
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class Reader:
    def __init__(self, files):
        self.files, self.reads = files, []

    def read_bytes(self, name):
        self.reads.append(name)
        return self.files[name]


class SarifTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = review.dependencies()
        cls.reader, cls.source, cls.engine, cls.rules = cls.context.dependencies()
        Path('test/scratch').mkdir(parents=True, exist_ok=True)

    def report(self, contract, document, names=('c.json', 'd.json'), **pins):
        reader = Reader(dict(zip(names, (contract, document))))
        report = self.context.inspect(reader, self.source, self.engine, self.rules,
                                      *names, **pins)
        return report, reader

    def run_value(self, contract, document, **kwargs):
        report, reader = self.report(contract, document, **kwargs)
        return review.render(report)['runs'][0], report, reader

    def test_all_original_errors_and_order_retained(self):
        c = 'line-2/tools/json-contract/report.contract.json'
        d = 'line-2/tools/rule-locator/report.invalid.json'
        original = self.context.inspect(*self.context.dependencies(), c, d)
        before = copy.deepcopy(original)
        log = review.render(original)
        run = log['runs'][0]
        self.assertEqual(len(run['results']), 3)
        for result, error in zip(run['results'], original['errors']):
            self.assertEqual(result['properties']['diagnostic'],
                             {k: v for k, v in error.items() if not k.endswith('_context')})
            self.assertEqual(result['ruleId'], run['tool']['driver']['rules'][result['ruleIndex']]['id'])
            self.assertEqual(result['relatedLocations'][0]['id'], 1)
        region = run['results'][0]['locations'][0]['physicalLocation']['region']
        self.assertEqual((region['byteOffset'], region['byteLength']), (92, 5))
        self.assertEqual(original, before)
        self.assertEqual(log['version'], '2.1.0')

    def test_saved_zto_policy_offline_and_pinned_artifacts(self):
        c = 'shared/payment-evidence/policy.contract.json'
        d = 'shared/payment-evidence/example.policy.json'
        with patch.object(socket, 'socket', side_effect=AssertionError('no network')):
            report = self.context.inspect(*self.context.dependencies(), c, d)
            run = review.render(report)['runs'][0]
        self.assertTrue(run['properties']['structurallyValid'])
        self.assertEqual(run['results'], [])
        self.assertTrue(run['invocations'][0]['executionSuccessful'])
        for artifact, name in zip(run['artifacts'], (d, c)):
            raw = Path(name).read_bytes()
            self.assertEqual(artifact['hashes']['sha-256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(artifact['length'], len(raw))

    def test_unicode_codepoint_columns_not_utf16_or_bytes(self):
        c = '{"type":"object","properties":{"🐸":{"type":"integer"}}}'.encode()
        d = '{\r\n\t"🐸": "日"\r\n}'.encode()
        run, _, _ = self.run_value(c, d)
        self.assertEqual(run['columnKind'], 'unicodeCodePoints')
        region = run['results'][0]['locations'][0]['physicalLocation']['region']
        self.assertEqual((region['startLine'], region['startColumn'], region['endColumn']), (2, 7, 10))
        self.assertEqual(d[region['byteOffset']:region['byteOffset']+region['byteLength']], '"日"'.encode())

    def test_missing_value_explicit_parent_anchor(self):
        c = b'{"type":"object","required":["x"],"properties":{"x":{"type":"integer"}}}'
        run, _, _ = self.run_value(c, b'{\n "other": 1\n}')
        result = run['results'][0]
        loc = result['locations'][0]
        self.assertEqual(loc['properties'], {'kind': 'missing_value_parent_anchor', 'anchorPath': ''})
        self.assertEqual(loc['physicalLocation']['region']['byteLength'], 15)
        self.assertIn('region selects its parent object', result['message']['text'])

    def test_null_is_present_token(self):
        run, _, _ = self.run_value(b'{"type":"string"}', b'null')
        loc = run['results'][0]['locations'][0]
        self.assertEqual(loc['properties']['kind'], 'value')
        self.assertEqual(loc['physicalLocation']['region']['byteLength'], 4)

    def test_uri_percent_encoding_keeps_filename_not_url(self):
        run, _, _ = self.run_value(b'{"type":"integer"}', b'"x"',
                                  names=('schema #?.json', 'https:evil/🐸 %23.json'))
        self.assertEqual(run['artifacts'][0]['location']['uri'], 'https%3Aevil/%F0%9F%90%B8%20%2523.json')
        self.assertEqual(run['artifacts'][1]['location']['uri'], 'schema%20%23%3F.json')
        self.assertEqual(run['results'][0]['locations'][0]['physicalLocation']['artifactLocation']['index'], 0)
        self.assertEqual(run['results'][0]['relatedLocations'][0]['physicalLocation']['artifactLocation']['index'], 1)

    def test_same_file_once_and_one_artifact(self):
        reader = Reader({'same.json': b'{"type":"object"}'})
        report = self.context.inspect(reader, self.source, self.engine, self.rules,
                                      'same.json', 'same.json')
        self.assertEqual(reader.reads, ['same.json'])
        self.assertEqual(len(review.render(report)['runs'][0]['artifacts']), 1)

    def test_deterministic_without_machine_metadata(self):
        report, _ = self.report(b'{"type":"integer"}', b'"bad"')
        a, b = review.encode(review.render(report)), review.encode(review.render(report))
        self.assertEqual(a, b)
        invocation = json.loads(a)['runs'][0]['invocations'][0]
        self.assertEqual(invocation, {'executionSuccessful': True})

    def test_ascii_control_and_markup_safe_json_text(self):
        c = b'{"type":"object","additionalProperties":false}'
        d = json.dumps({'\x1b[31m\u202e</script>': 1}).encode()
        run, _, _ = self.run_value(c, d)
        encoded = review.encode(run)
        self.assertTrue(encoded.isascii())
        self.assertNotIn('\x1b', encoded)
        self.assertIn('\\u001b', encoded)
        self.assertIn('\\u202e', encoded)
        self.assertNotIn('markdown', run['results'][0]['message'])

    def test_pins_reject_changed_whitespace(self):
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            self.report(b'{"type":"null"}', b'null\n', document_sha256=hashlib.sha256(b'null').hexdigest())

    def test_bad_contract_or_pin_prevents_document_read(self):
        reader = Reader({'c': b'{"bad":true}'})
        with self.assertRaises(ValueError):
            self.context.inspect(reader, self.source, self.engine, self.rules, 'c', 'unread')
        self.assertEqual(reader.reads, ['c'])
        reader.reads.clear()
        with self.assertRaises(ValueError):
            self.context.inspect(reader, self.source, self.engine, self.rules, 'c', 'unread',
                                 contract_sha256='not-a-pin')
        self.assertEqual(reader.reads, [])

    def test_malformed_sources_reject(self):
        for raw in (b'{', b'{"a":1,"a":2}', b'NaN', b'1e999', b'"\xff"'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.report(b'{"type":"string"}', raw)

    def test_complete_output_bound_no_partial_stdout(self):
        report, _ = self.report(b'{"type":"integer"}', b'"bad"')
        out, err = io.StringIO(), io.StringIO()
        with patch.object(review, 'MAX_OUTPUT_BYTES', 100), patch.object(self.context, 'inspect', return_value=report), \
                patch.object(review, 'dependencies', return_value=self.context), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = review.main(['c', 'd'])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), '')
        self.assertEqual(json.loads(err.getvalue())['status'], 'input_or_output_error')

    def test_real_many_errors_not_silently_dropped(self):
        report, _ = self.report(b'{"type":"array","items":{"type":"integer"}}',
                                json.dumps(['bad'] * 100).encode())
        run = review.render(report)
        self.assertEqual(len(run['runs'][0]['results']), 100)
        with self.assertRaisesRegex(ValueError, 'no report emitted'):
            review.encode(run)

    def test_cli_exits_and_inputs_unchanged(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as root:
            c, d = Path(root)/'c.json', Path(root)/'d.json'
            c.write_bytes(b'{"type":"integer"}')
            for raw, expected in ((b'2', 0), (b'"bad"', 1), (b'{', 2)):
                d.write_bytes(raw)
                result = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('review.py')),
                                         c.relative_to(Path.cwd()).as_posix(),
                                         d.relative_to(Path.cwd()).as_posix()], capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
                if expected == 2:
                    self.assertEqual(result.stdout, '')
                    self.assertIn('input_or_output_error', result.stderr)
                else:
                    self.assertEqual(result.stderr, '')
                    self.assertEqual(json.loads(result.stdout)['runs'][0]['properties']['structurallyValid'], expected == 0)
                self.assertEqual(c.read_bytes(), b'{"type":"integer"}')
                self.assertEqual(d.read_bytes(), raw)

    def test_workspace_reader_refuses_symlinks_and_special_paths(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as root:
            target, link = Path(root)/'target.json', Path(root)/'link.json'
            target.write_bytes(b'null')
            link.symlink_to(target.name)
            for name in (str(link), '../outside.json', '.hidden', str(Path.cwd()/'outside.json'), str(target.parent)):
                with self.subTest(name=name), self.assertRaises((ValueError, OSError)):
                    self.context.inspect(self.reader, self.source, self.engine, self.rules,
                                         'line-2/tools/json-contract/report.contract.json', name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
