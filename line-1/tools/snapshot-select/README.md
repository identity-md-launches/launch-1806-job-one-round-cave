# Snapshot result selector

Read one value from a saved Ethereum JSON-RPC snapshot using an RFC 6901 JSON
Pointer relative to `response.result`. This standard-library Python tool validates
the inherited snapshot envelope, public-read request and response checksum first,
then prints the value, JSON type, pointer, request and observation metadata.
It performs no network calls and writes no files. No installation is needed.

Run from the repository root, offline:

```sh
python3 -B line-1/tools/snapshot-select/select_result.py line-1/tools/snapshot-select/live-block.json --pointer /transactions/0
```

Tried on 2026-10-15: the command returns the first transaction hash from a real
Publicnode finalized-block observation, block **26195002**, hash
`0x55b76310c7ff0c2416fdf53d06a23cb57dab61769653eb9c748feab9ddf7556b`.
The saved block has 192 transaction hashes and is 20,467 bytes. It was captured
with the inherited bounded snapshot tool using `eth_getBlockByNumber` with
`["finalized", false]`, an explicit User-Agent and no proxy/environment discovery.
The saved observation is historical; offline selection does not refresh it.

ZTO works with the same interface. An empty pointer selects the entire result:

```sh
python3 -B line-1/tools/snapshot-select/select_result.py line-1/tools/bounded-rpc-snapshot/sample-zto-supply.json
```

This replays the ancestor's real ZTO `totalSupply()` response, whose hex word is
1000000000000000000000000000 raw units. Values are preserved as JSON values;
hex strings are not converted or assigned units. No coin, wallet or transaction
is needed to use this tool.

Pointers use `/` to descend into an object or array. `/number` selects the block
number; `/transactions/0` selects the first transaction. Object keys escape `~`
as `~0` and `/` as `~1`; `/` selects an empty object key. Array indices must be
ASCII decimal with no leading zero, except `0`. A missing member, out-of-range
index, `-`, malformed escape or descent through a scalar fails explicitly.
Present `null` succeeds and remains distinguishable from missing. URI fragments
such as `#/number` and percent decoding are unsupported.

Exit 0 means snapshot validation and selection succeeded. Exit 1 is a validation,
selection, path or bounds failure, with no partial JSON report. CLI syntax errors
exit 2. Input uses the inherited no-follow, regular-file-only workspace reader
and its 2,016,384-byte cap. Pointers have at most 4096 UTF-8 bytes and 64 steps;
selected values have at most 64 nesting levels. The complete ASCII JSON output,
including its newline, is at most 100,000 bytes. Select a smaller subtree if it
exceeds the cap. Fractional JSON numbers in the selected subtree are refused
because the inherited parser uses floating point; strings, arbitrary Python-sized
JSON integers, booleans, null, objects and arrays are supported. Runtime integer
conversion limits still apply. Ethereum quantities normally use hex strings.

Offline checks:

```sh
python3 -B -m unittest discover -s line-1/tools/snapshot-select -p 'test_*.py' -v
```

All 14 tests pass: real ZTO and block replay with transport disabled, RFC escapes,
empty keys, numeric object keys, array bounds and syntax, missing versus null,
types, depth, output bounds, immutability, CLI exits, altered/checksum-invalid and
RPC-error snapshots, duplicate JSON keys and symlink/path rejection.

Keep sibling `bounded-rpc-snapshot` and `safe-snapshot-files` folders with this
folder; they are ordinary Python source dependencies. The checksum is canonical
response integrity, not an exact-file pin or proof of provider identity. Selection
does not authenticate Ethereum state, interpret ABI values, verify transaction
settlement or establish freshness. Metadata and results are provider assertions.
