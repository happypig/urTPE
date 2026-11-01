# tasks — land-core-slug-fallback

## 1. Test-writing group (red first; all checked before any implementation task)

- [x] 1.1 `tests/test_slug_fallback.py`:
      (a) an anchor with `land_count: null` and a member carrying 1 yields a slug
      ending `等1筆` (no `?`);
      (b) the fallback scans by 編號 order — the newest member with a count wins
      when several carry one;
      (c) no member with a count keeps `?` AND appends the review flag to the
      anchor;
      (d) an anchor with a count is unaffected (no fallback, no flag);
      (e) the two real broken identities' shapes reproduce: 寶清段一小段51-13
      (anchor null, member 1) and 崇仁新村青年段一小段711-3 (anchor null, member 2)
      resolve to `等1筆` and `等2筆` respectively.

## 2. Implementation (after group 1 is fully checked)

- [x] 2.1 `urtpe/merge.py`: `slug_for(anchor, family=None)` — the count
      fallback scan (anchor, then members by 編號 ascending); the `?` branch
      returns (slug, True) semantics or sets a module-level helper the caller
      reads.
- [x] 2.2 `urtpe/merge.py` `merge()`: pass the family to `slug_for`; append the
      review flag to the anchor's `review_flags` when no member carries a count.

## 3. Acceptance

- [ ] 3.1 Full suite green; `slug_for` call-compatibility preserved.
- [ ] 3.2 `openspec validate` passes; both boards updated with the before/after
      id map (等?筆 → 等1筆 / 等2筆); commit.
