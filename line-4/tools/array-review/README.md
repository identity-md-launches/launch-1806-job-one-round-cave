# Offline EIP-712 array reviewer

Inspect array order before trusting a typed-data digest. This standalone Python
standard-library tool exposes every array in the domain and message, including
arrays nested inside structs or other arrays. It reports the declared type,
zero-based element words, length, array hash and positions of repeated words.
It never signs, sends, connects to a wallet, reads secrets or uses the network.

From the repository root, one command shows a successful check:

```sh
python3 -B line-4/tools/array-review/array_review.py line-4/tools/array-review/zto-batch.json --expect line-4/tools/array-review/zto-arrays.json --digest-expect 0xafd46e38940aa3cad45ccacf9ebbea5686570df15dcbf08e79119502d95605ba
```

What happened: `checksPass`, `arraysMatchExpected` and `digestMatchesExpected`
were true. `/message/evidence` contains one struct hash. `/message/tokenOrder`
contains ZTO, IMD, ZTO and reports repeated positions `[0, 2]`. Substituting
`zto-reordered.json` rejects with exit 1: the first two addresses were swapped.
Actual accepted and rejected reports are saved as `example-match.json` and
`example-rejection.json`. Without expectations, exit 0 means inspection completed;
`checksPass` is null, not an acceptance decision. Invalid input exits 2 and emits
no partial report. Diagnostics escape control characters.

The example wraps an unchanged historical ZTO payment commitment in a new
**illustrative offline batch**. It is not a transaction, a deployed protocol, a
ZTO contract interface, or a fresh chain observation. The expected struct word
comes from the ancestor's saved report; address words are the literal public
addresses left-padded to 32 bytes. `provenance.json` records exact source hashes.
The batch digest was calculated here and retained for demonstration. These
bundled expectations are not independently controlled approval.

## Bring independent expectations

Copy this folder as ordinary files anywhere; no sibling tools or packages are
required. Run from the directory containing your request and expectation files:

```sh
python3 -B array_review.py request.json --expect arrays.json --digest-expect 0xYOUR_SEPARATELY_RETAINED_64_HEX_DIGITS
```

Replace the illustrative digest argument with a real complete digest. Prepare
the expectation separately, from the intended request and a separately reviewed
calculation, rather than copying words from an untrusted incoming report:

```json
{"arrays":[{"path":"/message/items","declaredType":"uint256[]","elementWords":["0x0000000000000000000000000000000000000000000000000000000000000007"]}]}
```

Every observed array path must appear exactly once, including intermediate and
empty nested arrays. Extra/missing paths reject. Paths start at `/domain` or
`/message`, followed by declared field names and canonical zero-based indices.
Array entries in the expectation may be in any order; **element order matters**.
Only these three fields are permitted per entry. Words must be exactly 32-byte
hex strings; hex case is normalized. `{"arrays":[]}` explicitly expects no arrays;
null or missing `arrays` is an error. Fixed lengths must match the word count.
`--digest-expect` may also be used alone; the report states which comparisons
were supplied. Every supplied comparison must pass.

Per [EIP-712](https://eips.ethereum.org/EIPS/eip-712#definition-of-encodedata),
the array hash is Keccak-256 of concatenated element words, **without a length
prefix**. Each word is 32 bytes; nested arrays contribute their hashes, structs
their `hashStruct`, strings/bytes their content hash. Signed integers are sign
extended and fixed bytes right padded. The tool exposes those actual words;
it does not apply ABI dynamic-offset encoding or sort/deduplicate elements.

## Limits and interpretation

Array agreement alone does not pin scalar values outside arrays, unused types,
or full schema. For example, changing a nonce outside arrays still passes array
comparison; a separately retained complete digest catches it. Changing a struct
declaration behind an empty array may leave its element words unchanged: use
the line's schema reviewer for complete declaration comparison. Fixed and dynamic
arrays with identical elements have the same array hash; this tool also compares
the declared array type. Repeated words are observations, not errors, proof of
duplicate raw values, or a reason to remove elements. Hashes hide the original
values. Matching does not establish contract support, signer intent, authorization,
payment, replay safety or freshness. The inherited encoder is not a second
independent cryptographic implementation.

Inputs use the ancestor's bounded no-symlink workspace reader: regular UTF-8
JSON files beneath cwd, at most 65,536 bytes, duplicate keys/floats/nonfinite
values rejected, finite containers and bounded nesting/types/fields. No hidden
paths or parent traversal. Both CLI files use this reader. API callers receive
the same tree/schema/value validation. Reports are capped at 100,000 ASCII bytes
including the newline, with at most 128 arrays and 512 element words across all
levels. Larger valid requests fail closed; no partial review is emitted. Work
limits do not provide a general CPU sandbox.

Run the behavior and CLI tests:

```sh
python3 -B -m unittest discover -s line-4/tools/array-review -p 'test_*.py' -v
```

All 24 tests passed locally, including explicit word preimages, the published
empty Keccak vector, ordering, nested/fixed/dynamic/recursive arrays, domain
arrays, structs, strings/bytes/padding, repeated words, strict expectations,
complete-digest binding, output bounds, disabled network and CLI file boundaries.
The same tests pass with only this folder in a detached workspace copy.
