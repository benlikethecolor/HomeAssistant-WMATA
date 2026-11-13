# Release verification — 4.6.2

Verified November 12, 2026. No release was published and the release-preparation changes were not deployed to the running HA instance.

| Check | Result |
| --- | --- |
| Python suite on HA 2026.11.1 (stable image at verification time) | 32 passed |
| Packaged clean installation | Passed rail, bus, map and journey config/options flows |
| Packaged version-1 upgrade | Passed migration, key/interval preservation and numbered-entity removal |
| Frontend registration and static routes | Passed in extracted-archive HA setup |
| Entry unload/reload | Passed |
| Card tests with happy-dom | 12 passed |
| Ruff lint and formatting | Passed |
| Git whitespace check | Passed |
| Official hassfest container | Passed; 1 integration, 0 invalid |
| Live WMATA subscription | Rail catalog, bus routes, all three network endpoints and Court House predictions passed |
| Geometry reproducibility | All three generated JSON files matched bundled assets exactly |
| Documentation | Local links checked; board/map illustrations captured with sample data |
| Integration ZIP | 23 files; CRC and required assets passed |
| Authenticated HACS validator | Deferred to GitHub Actions on push, by maintainer choice |

The local HACS container could not run its authenticated checks without a GitHub token. The configured HACS workflow runs when pushed. That result remains required before publication.

The minimum supported HA version is now 2026.11.1, matching the version actually verified. CI tests that version and the stable image; at verification time these resolve to the same HA release.

Clean-install and upgrade tests use fixture API responses in temporary configurations and isolated containers. They do not change production configuration. Live API checks used the existing subscription without printing or saving its key. Browser illustrations use sample arrivals/positions rather than private HA dashboard data. Card tests simulate Leaflet and HA interactions; they do not replace a final browser check on a release installation.

Validated ZIP SHA-256:

    1855238446bff3168d4fde1638cd610472255f8dde5bd05ed45cc6db4500095a

Build it again with tools/build_release.py. ZIP metadata may change its hash when rebuilt; the content and required-file checks are the reproducible checks.
