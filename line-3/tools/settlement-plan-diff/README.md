# Settlement plan change review

Compare a proposed batch plan against an independently retained exact-byte
SHA-256 of a baseline plan. Detect accidental or hostile weakening before
replaying Ethereum transaction evidence. Python 3.9+ standard library, offline.

From the repository root, one command shows it working:

```sh
python3 -B line-3/tools/settlement-plan-diff/plan_diff.py --demo
```

Tried locally: exits 0 with `plan_unchanged_or_stricter` for the inherited
plan containing two real historical ZTO transactions. Both require 12
confirmations and finality. No chain observation was collected this round.
All 20 new tests pass, including lowering confirmations, dropping finality
while increasing confirmations, duplicate aliases and baseline substitution.

For your own plans:

```sh
python3 -B line-3/tools/settlement-plan-diff/plan_diff.py --baseline path/to/baseline.json --proposed path/to/proposed.json --baseline-sha256 YOUR_INDEPENDENTLY_RETAINED_64_HEX_SHA256
```

Use the settlement-batch version-1 plan format. Full validation of both plans
precedes comparison. Each has 1–32 unique normalized transaction hashes,
visible workspace-relative evidence paths, lowercase SHA-256 pins, and exact
policy fields. A baseline hash mismatch returns before parsing the baseline.
Both exact input byte hashes appear in the report; JSON formatting changes are
visible in hashes but do not constitute weaker policy.

The transaction set and evidence references must stay the same. Lowering any
confirmation threshold or changing required finality from true to false blocks
compatibility. A stronger constraint cannot compensate for a weaker one.
Increasing confirmations or requiring finality is compatible. Reordering is
reported but compatible; transaction-hash case normalizes. Additions, removals,
pin replacements and path relocations all require explicit review, even if a
path relocation would lead to identical bytes. All changes are reported in
transaction-hash order, including changes after the first blocking change.
No report presents a compatible subset as a compatible whole.

Exit 0: `planCompatible` true. Exit 1: change review required or baseline pin
mismatch. Exit 2: malformed/oversized input, unsafe path or unavailable file.
There is deliberately no `accepted` settlement field. **This checks plans,
not evidence**: it never opens referenced evidence, evaluates receipts or
establishes settlement. Run settlement-batch separately after approving the
plan; stricter policies can require newly captured matching-policy evidence.
No automatic baseline update, payment authorization or persistent deduplication.

Both plan files are limited to 90,000 bytes; JSON output to 100,000 ASCII bytes.
The inherited safe reader refuses symlinks at every component, hidden paths,
traversal, absolute paths, directories and special files. Strict JSON refuses
duplicate keys and nonfinite values. All reads are workspace-relative to the
current directory. Retain the baseline hash independently: replacing both it
and the baseline defeats change detection. Bundled hashes demonstrate use,
not independent custody or authenticated authorship.

Tests:

```sh
python3 -B -m unittest discover -s line-3/tools/settlement-plan-diff -p 'test_*.py' -v
```

Reuses unchanged sibling settlement-batch, pinned-position, tx-position,
payment-witness and settlement-check Python modules; all are ordinary files.
The demo also needs settlement-batch/demo-manifest.json. No dependencies to
install. No wallet, key, environment variables, external files, signing,
transaction sending, posting, payments or deployment.
