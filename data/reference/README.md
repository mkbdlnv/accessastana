# Reference data (committed to git)

`population_control.csv` holds official population control totals for calibrating
Kontur cells (Phase 0, decision A).

- A row with an empty `district` is a city total.
- A row with a `district` must use exactly the OSM district `name`, e.g.
  `Есіл ауданы`.
- If **all** districts of a city have rows, calibration is done per district:
  each cell is multiplied by `official_district / kontur_district`. Otherwise
  every cell is multiplied by `official_city / kontur_city`.

Only add numbers that come from a citable official publication, and put that
publication in the `source` column. As of 2026-11-16 we have not found an
official per-district table, so only the city total is present.
