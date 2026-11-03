## 1. Test writing — fully checked before any implementation task

- [x] 1.1 Viewer test: extract `buildRelatedLinkLabels` and run it — an anchored
  case is labelled by `candidate_names[cid]` when present (the -A區 case), two
  cases on one node read apart, the harvest-less id keeps the gazette label;
  the 國 anchor label is `twur_name` when present, else the node label.
- [x] 1.2 Pipeline test: `DiscoveryResult.twur_name` parses from a cached
  `view.html` `<title>` (view/57 shape) and survives the cache round-trip; a
  cache without `view.html` leaves it empty and the payload without the key.
- [x] 1.3 Confirm 1.1/1.2 fail on the current code.

## 2. Pipeline implementation

- [x] 2.1 Add `twur_name` to DiscoveryResult; parse the `<title>` at absorb
  (discovery + refresh) and persist it.

## 3. Viewer implementation

- [x] 3.1 `buildRelatedLinkLabels`: city name first for anchored cases;
  國 label reads `links.twur_name` with the current fallback.

## 4. Re-emit

- [x] 4.1 Re-run `--from-js` under the lock; confirm 吉林705's 國 label reads
  the 擬訂 title and 吉林508's 11011241 carries its -A區 suffix.

## 5. Verification

- [x] 5.1 pytest passes.
- [x] 5.2 scripts/viewer_smoke.js passes.
