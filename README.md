# nypd-commanding-officers

Weekly scrape of the current commanding officer of every NYPD precinct (78),
Housing PSA (9), and Transit District (12), from the official command pages on
[nyc.gov/nypd](https://www.nyc.gov/site/nypd/bureaus/patrol/precincts-landing.page).

`commanding_officers.csv` holds the latest scrape; **git history is the
archive** — each commit is a point-in-time snapshot, and diffs between commits
show CO changes (transfers, promotions in place, new appointments). The
`scraped_date` column is deliberately omitted so commits only occur on real
changes.

Runs Mondays 11:00 UTC via GitHub Actions. A run that parses fewer than 90 of
the 99 commands fails instead of committing, so a nyc.gov redesign shows up as
a red run rather than a corrupted archive.

Part of a family of NYPD data archives: [nypdonline-officer-profiles](https://github.com/jjhall77/nypdonline-officer-profiles)
(daily officer roster) and [nycgov-ccrb-mos-histories](https://github.com/jjhall77/nycgov-ccrb-mos-histories)
(CCRB complaint records).
