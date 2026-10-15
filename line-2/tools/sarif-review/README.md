# Offline JSON contract SARIF export

Produce SARIF 2.1.0 for a JSON deliverable checked against an explicit structural
contract. Editors and CI viewers can associate each violation with its exact
document region and the rejecting rule's region in the contract. This tool
recomputes diagnostics from caller-supplied files; it does not trust an incoming
report to choose paths, validity or source locations.

From the repository root, see the saved real ZTO-first payment policy pass:

```sh
python3 -B line-2/tools/sarif-review/review.py shared/payment-evidence/policy.contract.json shared/payment-evidence/example.policy.json
```

Tried locally: exit **0**, an empty `results` array, `structurallyValid: true`
and exact SHA-256 hashes of both captured files. The actual output is retained
in `zto-policy.sarif`. This checks the saved policy's shape, not a payment,
balance, authorization or current chain state. No new coin is needed.

To see rejection and source navigation:

```sh
python3 -B line-2/tools/sarif-review/review.py line-2/tools/json-contract/report.contract.json line-2/tools/rule-locator/report.invalid.json
```

Tried locally: exit **1**, all **three** inherited diagnostics retained, in the
same order. The string `"yes"` has document byte offset **92**, byte length **5**;
its related location identifies the contract's `"boolean"` token. See the actual
`invalid-report.sarif`. This intentionally invalid example is a rejection fixture,
not evidence of a failed real build. Redirect stdout yourself to retain a report;
the program does not create files or upload anything.

## SARIF mapping

- `ruleId` is `json-contract/` plus the inherited rule name. `ruleIndex` resolves
  into a deterministic descriptor list; every result has level `error`.
- Primary `locations` identify document tokens. `relatedLocations` identify the
  exact rejecting contract rule. Missing values select their containing object,
  with `missing_value_parent_anchor`, `anchorPath` and an explicit message;
  they never claim coordinates for a nonexistent token. Present null has its
  own token region.
- `columnKind` is `unicodeCodePoints`. Lines and columns are one-based; tabs count
  as one code point. End coordinates are exclusive. UTF-8 `byteOffset` and
  `byteLength` independently identify the original bytes, including CRLF and
  escaped source spellings. No conversion to UTF-16 is implied.
- Artifact URIs are workspace-relative, percent-encoded paths, preserving literal
  spaces, `%`, `#`, `?`, non-ASCII and colon characters as filename data.
  Each artifact records original byte length and a `sha-256` hash. Equal input
  paths are captured once and share one artifact entry.
- `properties.diagnostic` preserves every inherited diagnostic field except the
  optional context excerpts. It includes both complete source spans, document
  and rule pointers, observed value preview and rejecting constraint preview.
  These previews retain the ancestor's explicit truncation flags.
- A completed validation has `executionSuccessful: true` even when the document
  violates its contract. Run properties separately state structural validity
  and the complete error count. No fixes, suppression, machine metadata,
  execution command, timestamps or source-file contents are attached.

Exit **0** means structurally valid, **1** means structural violations, **2** means
input, contract, pin, parsing or output failure. Exit 2 writes a small ASCII JSON
error to stderr and leaves stdout empty, so a failure cannot resemble a clean
SARIF run. The whole encoded output must fit **100,000 bytes**, including its
newline. Overflow rejects the entire report rather than dropping diagnostics.

Optional `--contract-sha256 HASH` and `--document-sha256 HASH` compare separately
retained lowercase hashes before interpreting the same captured bytes. Hashes
identify bytes; they do not authenticate the author or establish approval.

## Verification and limits

```sh
python3 -B line-2/tools/sarif-review/test_review.py
```

All **16 tests passed**: diagnostic preservation, SARIF references, exact byte
slices, Unicode/CRLF columns, missing/null distinction, URI encoding, shared
capture, deterministic output, control characters, pins, malformed inputs,
whole-output rejection, CLI exits, immutability, no-follow paths and real saved
ZTO policy with network transport disabled. The inherited source-context's
**20 tests** and source-locator's **16 tests** also passed.

Both retained examples were additionally validated, with URI format checking,
against the [official OASIS SARIF 2.1.0 schema](https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json).
That one-time development check used an already available schema validator;
it is not a runtime or test-suite dependency. No package was installed. No
specific editor, CI uploader or browser was exercised; consumers differ in
support for related locations, Unicode columns and custom properties. Report
strings are JSON-escaped plain `text`, not markdown, but viewers remain
responsible for displaying decoded untrusted strings safely.

Python 3.10+ and its standard library suffice at runtime and for the tests.
Run on POSIX with no-follow opens, keeping the unchanged `source-context`,
`source-locator`, `rule-locator`, `bounded-contract` and `json-contract` sibling
folders. Explicit inputs must be visible relative workspace regular files of
at most 1,000,000 bytes. Symlinks, hidden/parent/absolute paths and special files
reject. The implementation reads no environment and uses no network.

This is the inherited limited contract language, not full JSON Schema.
Regexes must be trusted; byte/output limits are not a CPU sandbox. Structural
validity does not establish semantic truth, provenance or financial approval.
The `$schema` URL is informational and is never fetched by this program.
