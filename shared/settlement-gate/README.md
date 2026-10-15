# Retained plan and settlement gate

One offline decision combines Line 2's explicit JSON structural contracts with
Line 3's retained plan comparison and pinned transaction-position replay.
It checks the exact proposed bytes it compared, and requires the entire batch
rather than accepting the rows that happen to pass. Python standard library only.

From the repository root:

```sh
python3 -B shared/settlement-gate/gate.py shared/settlement-gate/baseline.json shared/settlement-gate/baseline.json --baseline-sha256 751fa0b816bfee7a209166f8844365b629bcc5a0bbedf090dd9b3755f330f5db
```

Tried: `plan_and_settlement_match`, two accepted historical real ZTO transactions.
The existing evidence asserts finality and at least 12 confirmations. No new
chain observation was collected. The hashes, receipts and positions come from
Line 3's saved Ethereum observations, copied unchanged. Only evidence paths in
the example plan were relocated. The example pin demonstrates usage; it is not
independently controlled approval. `provenance.json` maps every vendor/fixture
copy to its original path and SHA-256.

For real work, supply your separately reviewed baseline and proposed version-1
batch plans, and retain the baseline SHA-256 outside the evidence's custody.
Inputs must be visible relative regular files beneath the current workspace;
symlinks, parent/hidden paths, special files and files over 90,000 bytes reject.
Copy the entire `settlement-gate` folder; no line folders or packages are needed.
The demo's evidence paths assume its original `shared/settlement-gate` location
under the working directory. If relocating that layout, deliberately review and
rewrite the plan's evidence paths and retain its new exact hash.

The gate first pins the baseline, then reports structural diagnostics by JSON
Pointer, refuses weakened policies or changed transaction/evidence references,
and finally replays all pinned evidence. Reordered items and stricter policies
can pass plan review; **stricter does not mean settled**. A transcript captured
with the old policy can fail replay under the new one. This is tested explicitly.
Malformed duplicate JSON keys and duplicate transaction aliases reject. The
same captured proposed bytes feed both review stages, avoiding a plan-file
replacement between comparison and replay. It never updates the baseline.

Exit 0 means all gates passed, 1 means review required, and 2 means invalid input
or evidence. Output is complete ASCII JSON at most 100,000 bytes including the
newline; overflow rejects the whole report. No partial acceptance. Run:

```sh
python3 -B shared/settlement-gate/test_gate.py
```

All 14 integration tests pass, including disabled network, real saved evidence,
weaker/stricter policies, missing/replaced evidence, baseline replacement,
complete transaction sets, exact bytes, immutability, bounds and CLI exits.
The checks and demo also pass in a detached copy without the line folders.

These are historical provider assertions, not consensus or trie proofs. A pass
says nothing about payment amount, recipient ownership, present freshness,
signing authority or cross-run duplicate settlement. Replacement of both the
baseline and its retained hash defeats protection. No wallet, signing, payment,
posting, deployment, environment lookup or external file access is needed.
