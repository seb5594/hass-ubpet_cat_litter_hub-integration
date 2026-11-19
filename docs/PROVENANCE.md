# Source provenance and release scope

The [HACS review](https://github.com/hacs/default/pull/13798#pullrequestreview-5928093514)
identified upstream-derived implementation that the earlier rewrite had not
removed. The previous statement that release 2026.11.09.1 was fully covered by
MIT was not supported. The reply in
[CrazzyBerg/upet-hass#8](https://github.com/CrazzyBerg/upet-hass/issues/8) came
from `royalgardist`, not the repository owner `CrazzyBerg`; it is not treated as
permission for the owner's code. No permission is inferred for the other forks.
The maintainer confirms that no official permission has been obtained; the
chosen resolution is replacement of the unlicensed implementations, rather
than relying on an outstanding grant.

The 2026.11.19.1 candidate replaces the remaining platform implementations with
shared measurement adapters and a pure setting planner. `CloudHTTP` handles
signed exchange separately from the account client's authentication and caching
policy. The former switch classes, sensor helpers, time classes and duplicated
setting write paths are removed. Registry IDs, wire fields, protocol parameters
and storage compatibility are retained as interface data. The regression
contracts cover 95 entity identities, 83 values, all 41 sensors' attributes and
30 prior HTTP requests, including paths, JSON payloads, headers and signatures.
`http_profile.json` records compatibility header data; it contains no signing key.
The original research
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

The predefined app-level values are retained in `vendor_app_keys.json` so a
new installation does not require users to obtain an app key. Explicit input
and saved entry credentials take precedence. The values were restored unchanged
from the public project snapshot recorded in
[vendor-data.json](../.github/provenance/vendor-data.json). They are classified
as third-party application data and explicitly excluded from the project's MIT
grant in the archive's LICENSE-SCOPE.txt and distribution inventory.

Source availability, a separate file and matching hashes do not establish a
manufacturer grant. Manufacturer permission has not been verified; applicable
service terms remain a separate question. The [German app-data notes](APP_SCHLUESSEL.md)
record this limitation without presenting the bundled values as legally cleared.
The [switch review](SCHALTER.md) explains the replacement of the classes named
in the HACS review and the 32 frozen on/off request comparisons.

PR #13798 must remain a draft until the replacement has been reviewed, the new
release has passed the required workflows, and its actual archive has been
checked. No upstream license grant or HACS approval is claimed here.
