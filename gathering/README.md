# Water gathering 14 — The Retained Knot

[REPORT.md](REPORT.md) covers all four lines, checks, limitations and wall review.
[COINS.md](COINS.md) records **none**: ZTO first and IMD second suffice.
The new [retained plan and settlement gate](../shared/settlement-gate/README.md)
combines structural contracts, non-weakening plan comparison and pinned batch
settlement replay. It works offline without the line folders or external packages.

From the repository root:

```sh
python3 -B gathering/run_checks_14.py
python3 -B gathering/check_round_14.py
python3 -B gathering/build_gallery.py
python3 -B gathering/check_delivery_14.py
```

Tried: 131 commands and 1,009 unittest cases passed (one documented inherited
auxiliary-server test skipped); nine supplementary trials passed with expected
exits. New integration: 14 tests pass here and detached, including historical
real ZTO evidence, weakened-plan rejection and compatible-but-unreplayable stricter
policy. No new chain capture, installation, signing or transaction sending.

Wall: `artifacts/gathering/wall-v14.png`, identical `wall.png`, 1254 × 1254 RGB PNG.
Record: `dist/gathering/14.json`, adjacent 512 × 512 JPEG below 100 KB. Built-in
imagegen supplied the worn ochre knot; only its new pigment was added to vacant
ancestral rock, leaving all pixels outside the patch identical. Full PNG and
decoded JPEG inspected; no known unmet visual requirements and no new hands.
The gallery includes 70 paintings and 87 placeholders. All line folders remain
unchanged. Required PNG is untracked for separate upload.
