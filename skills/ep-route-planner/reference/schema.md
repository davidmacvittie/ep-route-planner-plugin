# Trip data file (one JSON file per move)

`scripts/build_packet.py trip.json out.pdf` reads this file. `examples/dc-atlas.json` is a complete example. Text fields may use `<b>`, `<br/>` and `<font color="#hex">`. Image paths are relative to the JSON file. Verdict levels are `GREEN`, `AMBER` or `RED`. Color names: `navy`, `blue`, `amber`, `green`, `purple`, `red`, `slate`, or a `#hex` value.

| Key | What it holds |
|---|---|
| `meta` | `code_name`, `date_label` (header, like "Fri Nov 20, 2026"), `header_tag` (right side of the header; empty for a real move), `doc_title`, `author`, `footer` |
| `cover` | `title`, `intro`, `facts` ([label, text] rows), `overall` {`level`, `why`}, `timeline`, `drive_times_note`, `watch_outs` |
| `cover.timeline[]` | `kind` (`stop` or `drive`), `badge` and `badge_color` (stops only), `time`, `text`, `verdict` (empty for none) |
| `cover.watch_outs[]` | `icon` (`warn`, `event`, `hospital`, `police`, `fire`, `secure`, `car`), `text` |
| `weather` | `source`, `day`, `date`, `high`, `low`, `tag` (say "NORMAL FOR THE DATE, NOT A FORECAST" when it isn't one), `sunset`, `dark`, `lines[]` {`tone`: `note`, `muted` or `impact`, `text`} |
| `trip_map` | `title`, `image`, `legend` ([color, label] pairs), `caption` |
| `events` | `title`, `note`, `rows` ([what, where, effect on us]) |
| `legs[]` | one per drive, see below |
| `stops[]` | one page per place, in driving order, see below |
| `medical` | `from` (short stop names, one column each), `rows` ([place, type, one time per stop, check]; type `Police`, `Fire`, `Secure venue` or a text with "Trauma" gets an icon), `times_note`, `runs_title`, `runs[]` {`head`, `sub`, `steps[]`}, `runs_note`, `kit_note` |
| `recon` | `intro`, `rows` ([#, where, confirm]), `day_of[]`, `code_words` ([word, means]), `code_note`, `comms_down[]`, `rally_summary`, `confidence[]` |
| `driver_card` | `title`, `moves` ([time, move, primary, alternate]), `points` ([stop, car stops, backup, rally point]), `medical`, `comms`, `red_spots[]` |
| `forms` | `recon_routes` (prefilled rows: [route, planned min, "", planned mi]), `recon_spots` (rows: [spot or stop]) |
| `terms` | optional [term, meaning] rows to replace the default key terms on page 1 |

## A leg

| Key | What it holds |
|---|---|
| `title`, `depart` | "Willard to The Anthem", "5:30 PM" |
| `map_image` | leg map: primary blue, alternate amber, numbered red spots |
| `primary`, `alternate` | [route in words, distance, drive time] |
| `shared` | how much road the two routes share |
| `spots` | [number or "", where, why it matters, if blocked go]; a number makes it a red spot row |
| `closures_source`, `closures[]` | where and when closures were read, then one line each |
| `verdict` | [level, why] |
| `strip` | `primary` and `alternate` routes, `primary_notes` and `alternate_notes` |

A strip route: `title` ("Leg 1 primary: Willard > The Anthem"), `line` (full geometry as [lon, lat]), `meters`, `minutes`, `depart`, `arrive`, `source` (like "Mapbox Directions, read Nov 9."), `events[]`. Each event has `at` (`start` or `end`) or `pt` ([lon, lat]), `side` (`L`, `R`, `S` for straight-on, or empty), `label`, `sub`, `text`, and optionally `cp` ("CP2: call in") and `red` (spot number). If the routing tool gives no turn coordinates, `turns(line)` in `scripts/strip.py` reads each turn's `pt` and `side` from the geometry.

Strip notes are [head, body, icon], where icon is `["spot", n]`, a kind like `warn` or `hospital`, or null.

## A stop

`kicker` ("STOP 1  |  ARRIVE ABOUT 5:43 PM, DEPART 8:00 PM"), `title`, `image` (overhead view with lettered pins), `caption` (what each letter means and the image source), `overview`, `rows` ([item, detail, source] for entrances, drop-off, pick-up, car hold, backup point, rally point), `verdict` [level, why], `handoff[]`, `flag` (optional amber note).
