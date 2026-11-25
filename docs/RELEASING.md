# Testing and releasing WMATA

Development work stays on a feature branch until it is ready for review. Changing
manifest.json does not publish anything. A tag starts the release workflow;
that workflow creates a **draft**, never a public release.

## Beta channel

Use matching versions such as `3.1.0-beta.1` in manifest.json and CARD_VERSION,
and a tag such as `v3.1.0-beta.1`. Beta tags must point to a commit on `main` or
`beta`; stable tags must point to `main`. All compatibility tests, frontend
checks, HACS, and hassfest still run. Draft beta releases are marked prerelease
and explicitly do not replace GitHub's latest stable release. Publish a draft
only after reviewing its ZIP and notes. HACS users must opt into prereleases;
normal users should stay on the latest stable version.

Do not create a tag merely to share work in progress. Use a branch or draft PR.

## Before a beta

- [ ] All four HA compatibility jobs, frontend tests, lint, HACS, and hassfest pass.
- [ ] Install the ZIP in a separate HA instance; keep production on its current version.
- [ ] Check an original 1.x rail entry, a 2.x bus entry, and a current entry upgrade.
- [ ] Check boards at a transfer station, journeys, commutes, bus stops, and both map views.
- [ ] Try depart-at and arrive-by trips, overnight service, and a date outside the GTFS feed.
- [ ] Check elevator warnings, outage filtering, and an unavailable elevator feed.
- [ ] Verify stale alerts recover and a successful empty feed clears old alerts.
- [ ] Check desktop, phone-width layout, dark/light modes, and keyboard controls.
- [ ] Update examples and explain changed automation behavior in the release notes.

## Before stable

- [ ] Complete the beta checklist and resolve reported regressions.
- [ ] Leave an isolated instance running for at least 48 hours, spanning overnight service.
- [ ] Restart that instance and reload entries; confirm entities and saved settings survive.
- [ ] Review Health entities and diagnostics for repeated errors or throttling.
- [ ] Remove the prerelease suffix in both versions and run validation again.
- [ ] Confirm the tag's commit is on main, the ZIP is attached, and notes include upgrade steps.
- [ ] Publish the checked draft. Verify GitHub's latest stable release and HACS download.

The offline resilience tests advance through repeated failures and recovery quickly;
they do not substitute for a real overnight or multi-day run. For a read-only
48-hour monitor, enable the Health entity in the test instance and run:

```sh
python tools/monitor_soak.py --url http://127.0.0.1:18124 \
  --token-file /path/to/test-instance-token --hours 48 \
  --entities sensor.wmata_metro_center_health > soak.ndjson
```

The monitor writes only selected health fields, not tokens, station boards,
coordinates, or incident descriptions. Keep its output local. It does not restart
HA, change settings, or recover failures automatically.
