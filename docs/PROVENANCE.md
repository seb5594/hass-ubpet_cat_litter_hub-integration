# Source provenance and release scope

The [HACS review](https://github.com/hacs/default/pull/13798#pullrequestreview-5928093514)
identified upstream-derived implementation that the earlier rewrite had not
removed. The previous statement that release 2026.11.09.1 was fully covered by
MIT was not supported. The reply in
[CrazzyBerg/upet-hass#8](https://github.com/CrazzyBerg/upet-hass/issues/8) came
from `royalgardist`, not the repository owner `CrazzyBerg`; it is not treated as
permission for the owner's code. No permission is inferred for the other forks.

The 2026.11.18.1 candidate replaces the remaining platform implementations with
shared measurement adapters and a pure setting planner. `CloudHTTP` handles
signed exchange separately from the account client's authentication and caching
policy. The former switch classes, sensor helpers, time classes and duplicated
setting write paths are removed. Registry IDs, wire fields, protocol parameters
and storage compatibility are retained as interface data. The original research
sources remain credited in [SOURCES.md](SOURCES.md).

The [German audit](LIZENZPRUEFUNG.md) explains the scope and implementation choices.
[Pinned snapshots](../.github/provenance/sources.json), a
[repeatable comparison report](../.github/provenance/overlap-report.json), and the
[distribution inventory](../.github/provenance/distribution.json) make the review
reproducible. Matching thresholds are not copyright rules. A zero-match report
does not establish independent authorship or legal clearance. The authors had
access to upstream source; this is not represented as a clean-room process.

The MIT notice accompanies the project implementation and original artwork in
this source snapshot. It does not relicense third-party implementations or
retroactively resolve the status of older commits and archives. The four brand
PNGs are rendered from the project's self-contained `assets/cat-litter-hub.svg`.
External dependencies retain their own licenses and are not vendored in the ZIP.

The candidate no longer distributes `vendor_app_keys.json` or loads signing
keys from bundled files. Existing entries preserve their locally stored key.
New entries require a key the user is authorized to use for the selected app
and region. A generally available official third-party issuance process has
not been verified. This access question is separate from copyright in the
integration source; MIT does not grant rights to vendor services or trademarks.

PR #13798 must remain a draft until the replacement has been reviewed, the new
release has passed the required workflows, and its actual archive has been
checked. No upstream license grant or HACS approval is claimed here.
