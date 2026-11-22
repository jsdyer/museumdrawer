# Museum Drawer

A static, accessible cabinet of real GBIF occurrence records around Langley, British Columbia and Halifax, Nova Scotia. Historic preserved specimens sit beside modern records, with enough provenance to examine how collecting and digitization shape the view.

<!-- coolcode:guide -->
Choose Langley or Halifax, then compare historic preserved specimens (1700–1999) with modern records (2000 onward). Up to 300 records per time band are retained; these capped API-order samples are not representative surveys. Filter by taxon, source, licence or coordinate quality, inspect an attributed record card, and export the selection. The coarse map and decade chart show only the selected capture’s retained records, not every GBIF match or a population trend.
<!-- /coolcode:guide -->

## What is included

| Region | Latitude | Longitude |
| --- | --- | --- |
| Langley | 49.02–49.20° N | 122.80–122.52° W |
| Halifax | 44.56–44.74° N | 63.70–63.45° W |

The rectangular query areas match Mushroom Calendar and are not municipal boundaries. `country=CA` and `hasCoordinate=true` limit records to Canada and public interpreted coordinates. No credentials are required. Queries cover all kingdoms.

- Historic means `basisOfRecord=PRESERVED_SPECIMEN`, year 1700–1999. Three time bands: 1700–1899, 1900–1949, 1950–1999.
- Modern means any basis of record from 2000 through the collection year. Three time bands: 2000–2009, 2010–2019, 2020 through collection year.
- Each time band requests at most three pages of 100 records in GBIF’s default order. Maximum 900 retained records per region/era, 3,600 total. Unused capacity is not redistributed. This prevents a large recent dataset from entirely excluding older eras, but **does not make the sample representative**.
- Each cohort has a separate full-query count and each time band retains its count, query URL, fetched-page URLs, stable-count flag, completeness flag and duplicate count. Counts can change while pages are collected. Duplicate GBIF IDs are removed; records may still represent duplicate underlying observations in different datasets.
- The official baseline uses the time bands above. Unpublished development captures are excluded; future scheduled captures retain this documented collection method. A method change must be identified explicitly and must not be interpreted as ecological or source-record change.

Every chart, map, source proportion, card and CSV uses the filtered retained sample. Full matching counts are labelled separately. Different record types, collector effort, geographic access, taxonomic interests, repeated visits, source ordering and digitization all affect the comparison. A missing species or decade is not evidence of absence. Name counts are distinct interpreted taxon strings, not a validated species inventory. The modern cohort includes specimens as well as human and machine observations and other record types.

## Coordinates, quality and rights

The collector keeps only a 0.02° rounded grid centre (roughly 1–2 km); it does not archive original latitude/longitude, verbatim localities, or private locations. A nonempty GBIF `informationWithheld` or `dataGeneralizations` field suppresses the map point entirely. Maps are offline coordinate plots with a labelled city reference point and coordinate axes; no remote map tiles are requested. Generalization can shift a point slightly outside a query edge. Source coordinate uncertainty is retained separately and is not the uncertainty of the rounded map grid.

The spatial-quality control excludes the explicitly listed coordinate flags in `scripts/collect.py`. It does not exclude every GBIF flag, and no-flags does not imply complete accuracy. The ≤1 km control additionally requires reported nonnegative uncertainty of at most 1,000 metres, excluding unknown values. All record flags are visible on the record card.

Each record carries its source dataset ID and link, GBIF occurrence link, data licence and catalogue metadata. The snapshot also preserves dataset titles, publisher registry IDs and GBIF-provided citation text. CC0, CC BY and CC BY-NC data are differentiated. Respect the licence shown for each source, including noncommercial restrictions where applicable. CSV contains source attribution and licence fields but deliberately omits coordinates. CSV cells are quoted and spreadsheet formula prefixes are neutralized.

Software is MIT licensed; this does not relicense GBIF-mediated data. Reuse the data under each source’s stated terms. Follow original GBIF dataset links for full citation and download provenance; this small search-API capture is not a GBIF DOI-bearing occurrence download.

## Dates and retention

- `event_date` / year: when the organism was recorded or collected.
- `captured_at`: when this collection began. A refresh is not a simultaneous transaction across all GBIF pages.
- `built_at`: when the static site was assembled; this never substitutes for source capture dates.

Every successful collection produces an immutable `data/snapshots/<UTC timestamp>-<sha256 prefix>.json`, even if records repeat. `data/history.json` carries SHA-256 checksums and dates. The build validates all retained captures and checksums and confirms that the current capture is archived. Snapshots contain normalized public fields, not full raw API responses. `data/index.json` is a small freshness/coverage endpoint for the hub. The archive selector opens the retained JSON captures locally. Git also preserves every committed snapshot; neither collector nor build deletes old captures.

Refresh is scheduled monthly on the 5th at **09:43 UTC**. A manual workflow run can request refresh. The first main-branch build also collects automatically if no saved dataset exists. Collection and validation must succeed before current data changes are committed and a deployment proceeds; failure preserves the last successful deployment. GitHub may suspend schedules on inactive public repositories after 60 days. Older source records may disappear, be corrected or shift API position; capture differences are not ecological change.

## Privacy

All search, map-cell and filter changes run locally. Loading the site requests static app and data files plus CoolCode’s aggregate visit counter; filter values are never sent to GBIF. Following a source link contacts that external provider. No search terms, preferences or user inputs are stored. The browser needs no API key or secrets.

## Development and publication

```sh
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

The default build is offline and uses only Python’s standard library. To refresh from public GBIF endpoints, run `python3 scripts/collect.py` explicitly. `tests/browser_smoke.py` tests filter interactions, map cells, cards, CSV, snapshots and mobile overflow at a project subpath in CI. It uses the template’s test-only Playwright dependency.

Source is in `web/`, collector/archive code in `scripts/`, and tests in `tests/`. Keep relative URLs for GitHub Pages at `/museumdrawer/`. No CNAME is needed. CI checks pull requests and publishes successful main builds. The shared CoolCode hub owns discovery; `tool.json` is its catalogue record.

## Primary references

- [GBIF Occurrence API](https://techdocs.gbif.org/en/openapi/v1/occurrence): pagination and public search parameters. The provider permits up to 300 rows per page and a 100,000 row offset ceiling; our collector deliberately uses lower bounds.
- [GBIF API conventions](https://techdocs.gbif.org/en/openapi/): paging and range queries.
- [GBIF issue definitions](https://techdocs.gbif.org/en/data-use/occurrence-issues-and-flags): interpretation flags and their limits.
- [GBIF terms and licences](https://www.gbif.org/terms).
- [Fossil Neighbours](https://coolcode.ca/fossilneighbours/) and [Mushroom Calendar](https://coolcode.ca/mushroomcalendar/) for related local explorations.
