# Report build notes

- Audience: technical.
- Delivery mode: portable HTML.
- Required section mapping: title; answer-first technical summary; provenance and file findings; scope/definitions; methodology; limitations/robustness; recommended next steps; further questions.
- Chart contract: compare the share of current `review.verdict=revise` items across the four upstream sources. Takeaway: the status is concentrated in HL (157/600, 26.2%), but the verdict is sometimes stale and must not be interpreted as a current semantic error rate. Family: single-series categorical bar. Rows: four sources. Measure: revise items / selected items. Palette: single-root, no redundant color encoding. Final surface: canonical portable report chart.
- Table rationale: provenance, structural checks, QA states, and confirmed exceptions require exact lookup, so tables remain the primary evidence.
- Browser QA: packaging and structural verification passed. Enhanced Chromium viewport/source-interaction QA did not run because no compatible local Chromium headless shell was available.
