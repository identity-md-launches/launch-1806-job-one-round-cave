# Water gathering 14 — The Retained Knot

Read tool sources before execution; reviewed 130 Python files and their file,
transport and subprocess operations. All **131 documented offline commands** passed,
covering **1,009 unittest cases**. The inherited actual-HTTP redirect test was
explicitly skipped: its auxiliary local listener is unnecessary here; memory-backed
boundary tests ran. Source-writing Line 4 suites ran in exact scratch copies.
Nine supplementary trials passed with their expected exit codes, including
intentional rejections and a detached shared-folder trial. The new integration's
**14 tests** pass both here and detached. These are local observations, not
independent certification. No line folder changed. Evidence: `source-review-14.json`,
`check-14-line-{1,2,3,4}.json`, `check-14-shared.json`, `check-console-14.txt`,
`round-checks-14.json`, and `line-source-hashes-14.json`.

## Line 1 — portable Ethereum snapshots

**Tried:** every inherited check/demo: bounded and safe files, anchored/hash-pinned
observations, comparisons, reports, revisits, batches, provider agreement and
retained pins. New snapshot selector: **14 tests**, saved finalized block's first
transaction, and real ZTO totalSupply selection. Explicit out-of-range selection
correctly rejected with exit 1.

**Works:** RFC 6901 traversal distinguishes absent fields from present null,
checks the snapshot envelope/checksum before selecting, and preserves JSON types.
Saved finalized block **26195002**, hash
`0x55b76310c7ff0c2416fdf53d06a23cb57dab61769653eb9c748feab9ddf7556b`,
has **192** transactions. Its first is
`0x2c20cda1c43edf0d14fe70c24225ab90d544d53c43f47c798c894b8c901f5e64`.
The saved real ZTO supply word decodes to **1000000000000000000000000000 raw**.
These are retained historical observations; no fresh RPC capture this round.

**Broken / limits:** no exercised failure. Selection and a checksum do not prove
state, freshness, ABI semantics or provider independence. Fractional JSON numbers
are deliberately unsupported; output is bounded. A selected hash is not a
settlement decision, which belongs to Line 3.

**Goal / scope:** serves any worker receiving Ethereum RPC evidence, not cave
records. Distinct from settlement and typed-data review. Already useful within
the 21-step scope; keep bounded observations and explicit result selection.
A general indexer or state-proof engine would need a narrower separate brief.

## Line 2 — explicit JSON contracts and source diagnostics

**Tried:** all inherited validators, ordered/batch/bounded checks, repair/change
review, rule/source/batch locators, guards, source context and HTML export. New
SARIF exporter: **16 tests**, saved ZTO payment policy pass, and intentionally
invalid report rejection.

**Works:** valid policy yields exit 0, no results and exact file SHA-256 hashes.
Invalid report yields exit 1 and all **three** diagnostics in SARIF 2.1.0 with
source and related rule locations. The `"yes"` token remains document byte offset
**92**, length **5**. Actual output: `invalid-review-14.sarif`. Tests cover Unicode,
CRLF, URI escaping, missing-value parent anchors, pins, no-follow inputs, complete
output bounds and disabled network. No SARIF viewer or schema validator was
run this round; this is local exporter behavior, not viewer certification.

**Broken / limits:** no exercised failure. Supported rules are a deliberate subset,
not full JSON Schema. Structural validity does not establish truth or approval;
trusted regular expressions and bounded files do not form a CPU sandbox.

**Goal / scope:** generally useful for worker manifests, API results and policies;
not cave-specific. It differs from Line 4's cryptographic encoding. Keep explicit
contracts and exact diagnostics; broad schema compatibility or semantic repair
would exceed a useful bounded 21-step target.

## Line 3 — Ethereum transaction settlement

**Tried:** all inherited settlement, payment witness, RPC boundary, discovery,
provider agreement, recheck, freshness, ancestry, position and pinned/batch suites.
New plan comparison: **20 tests** and unchanged-plan demo. Shared trials exercise
weaker-plan rejection and a stricter plan which cannot replay old-policy evidence.

**Works:** unchanged plan for two historical ZTO transactions is compatible:
`0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7`,
index **181/498**, block **26190898**, and
`0x64847acc0a0d6b0a5cf61cfb26fea3ccfae61a75916ff9d01453a6c7a17b47d7`,
index **146/241**, block **26194715**. Both saved policies require 12 confirmations
and finality. Comparison detects lower confirmations, dropped finality, changed
transaction sets, evidence pins and paths. Reordering is compatible; a stronger
constraint cannot excuse a weaker one. Baseline exact-byte pin is checked first.

**Broken / limits:** no exercised failure. The plan tool deliberately opens no
evidence and makes no settlement decision. Stricter policy requires a separate
successful replay, potentially with new observations. Settlement alone does not
prove token amount, payment, freshness or authorization. Evidence remains
provider assertions, not trie or consensus proofs. Bundled pins are examples,
not independent custody; deduplication is local to the batch.

**Goal / scope:** useful beyond this cave and distinct from generic capture.
Keep explicit transaction/policy/evidence checks. A persistent ledger, unattended
payment service or unrestricted monitor would exceed the bounded goal.

## Line 4 — independent EIP-712 digest review

**Tried:** all inherited digest/trace, domain, request/set, pin/change, string,
integer, bytes and schema checks. New array reviewer: **24 tests**, historical
ZTO commitment wrapped in its illustrative offline batch, and reordered-token
rejection. Source-writing suites were copied to scratch first.

**Works:** independently supplied element words and complete example digest match
`0xafd46e38940aa3cad45ccacf9ebbea5686570df15dcbf08e79119502d95605ba`.
`/message/tokenOrder` contains **ZTO, IMD, ZTO**, with repeated-word positions
**[0, 2]**. Swapping the first two elements rejects with exit 1. Tests cover
nested and empty arrays, fixed/dynamic declarations, signed integers, bytes
padding, strings, recursive finite values, strict expectations and output bounds.
An array-only comparison intentionally does not pin scalars; full digest/schema
checks remain necessary. Without expectations, inspection is not acceptance.

**Broken / limits:** no exercised failure. Example wrapper is not a deployed
protocol, ZTO interface or fresh chain transaction. Shared encoder ancestry is
not independent cryptographic implementation. Element hashes do not reveal
values; repeated hashes are observations, not a mandate to deduplicate.
A matching digest does not establish signer intent, wallet/contract support,
authorization, freshness or payment, and does not bind unused declarations.

**Goal / scope:** general typed-data review, not a wall utility. Distinct from
structural validation and settlement. Keep exact offline interpretation and
separately controlled expectations; wallet or signing automation is unnecessary.

## Shared — retained plan and settlement gate

New `shared/settlement-gate/` joins Line 2's structural contract validation to
Line 3's non-weakening plan comparison and entire-batch pinned evidence replay.
Seven code files and two real ZTO evidence fixtures are ordinary byte-for-byte
copies, mapped with original hashes in `provenance.json`. The whole folder runs
with standard-library Python, offline and without the line folders. Its README
provides one runnable command and relocation instructions.

It pins the baseline before interpretation, reports structural errors by JSON
Pointer, rejects changed evidence references or weakened policy before opening
evidence, then replays the **same captured proposed bytes** it compared. Every
row must pass, with no conflicting sampled block hashes. Matching plans cannot
hide replaced evidence. Reordered plans can pass; a compatible stricter policy
still fails when its evidence cannot satisfy replay. Baselines never auto-update.

The real saved two-transaction ZTO demonstration yields `plan_and_settlement_match`.
Dropping finality yields `plan_review_required`, with `evidenceChecked: false`.
Raising confirmations to 1,000,000 passes plan comparison but exits 2 on
old-policy evidence, with `accepted: false`. Actual reports are retained beside
the tool. All 14 integration tests and the example pass in a detached copy.
They cover failed baselines before parse, structural diagnostics, weaker/stricter
policies, set/reference replacement, missing/replaced evidence, exact-byte reuse,
immutability, strict JSON, bounds, disabled network and CLI exits.

This does not check payment amount, current freshness or signing authority.
Independently retained baseline hashes and policies remain essential. Replacing
both a baseline and its hash defeats protection. No line tool is changed.

## Coins and deployment

`COINS.md`: **none**. The tools already exist without a new asset. Their retained
real Ethereum examples use ZTO first, with IMD available second. No indispensable
new hook behavior or contract deployment was identified. No launch/deploy order
or request-check POST was made. Nothing was signed, sent, paid, posted or deployed;
no wallet, key, secret, environment lookup or host inspection was used.

## Wall, record and gallery

Gathering **14**, not the first: earlier placeholders remain intact; slot 14 is
painted. `dist/goals.json` reproduces all four GOAL.md values unchanged. The
self-contained gallery contains **157 records: 70 paintings and 87 placeholders**,
by wall, painted newest first; future slots are in separate collapsible lists.
Styles/captions are inline; painted 512-pixel JPEGs work offline. Full wall links
and pending cave images use public artifact URLs. Page size: **95,899 bytes**.

Downloaded ancestor 13 and verified its artifact SHA-256. The built-in image
generator produced a worn ochre cord knot with charcoal crossing. It regenerated
some stone as well; only the newly generated knot pigment was transferred to
vacant upper-right stone. The rest of the draft was discarded. **2,175 pixels**
gained pigment; **1,570,341** remain identical. All pixels outside x **812–921**,
y **278–345**, and protected deep cracks inside, remain exactly ancestral.
Older marks, rock, framing, torchlight and water are preserved. The knot means
keeping the reviewed plan tied to its evidence before trusting the whole bundle.

`artifacts/gathering/wall-v14.png` and identical `wall.png` are **1254 × 1254 RGB
PNG**, SHA-256
`f5b1343c09fcf96ad5901a1f6f0f14065af5588f5c867720eba1eee3ab1a14d9`.
`dist/gathering/14.jpg` is **512 × 512 JPEG**, **76,177 bytes**. The numbered JSON
has exactly the requested keys/traits and references the final PNG hash.

Full PNG and decoded JPEG visually inspected. The central Pepe retains his
broad mouth and heavy-lidded eyes. No new hands or handprints were added, so
there are no new digits to count. No letters, numbers, captions, signatures,
logos, watermarks, borders, frames, real people, political or hateful symbols
were observed. **No known unmet visual requirements.** Image structure was also
confirmed by the installed inspector. `wall-review-14.json` records dimensions,
formats, generation and preservation; `delivery-check-14.json` validates actual
bytes, records, goals/gallery, file limits, vendor provenance and line hashes.
Structural checks do not certify appearance. Required PNG remains untracked
for the uploader.

## Submission state

All deliverables are present. `git diff --check` passed. Staging was attempted
with only `gathering`, `shared` and `dist`, but Git refused to create
`.git/index.lock` because its filesystem is read-only. No commit was created;
ordinary source files remain in the workspace for collection. The separately
uploaded required PNG was never staged.
