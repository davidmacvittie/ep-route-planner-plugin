# Trip data file (one JSON file per move)

`scripts/build_packet.py trip.json out.pdf` reads this file. `examples/dc-atlas.json` is a complete example. Text fields may use `<b>`, `<br/>` and `<font color="#hex">`. Image paths are relative to the JSON file. Verdict levels are `GREEN` or `AMBER`. The skill never sets `RED`; that is the team's call after the advance drive, and the builder changes any `RED` to `AMBER` with a warning. Color names: `navy`, `blue`, `amber`, `green`, `purple`, `red`, `slate`, or a `#hex` value.

| Key | What it holds |
|---|---|
| `meta` | `code_name`, `date_label` (header, like "Fri Nov 20, 2026"), `header_tag` (right side of the header; empty for a real move), `doc_title`, `author`, `footer` |
| `inputs` | What the user gave, shown in the cover's General info area: `code_name`, `date`, `start_time`, `cars`, `greeter` (who meets the car at the event site, or empty), `routes` (routes per leg; empty shows "2 (default)"), `risk` (empty shows "Medium (default)"; for reviewers only, nothing else changes with it), `stops` ([label, text] rows: "Start / end", "Stop 1" and so on) |
| `cover` | `title`, `intro` (one short line), `overall` {`level`, `why`}, `timeline`, `drive_times_note`, `watch_outs`. `facts` ([label, text] rows) is used only when there is no `inputs`. |
| `cover.timeline[]` | `kind` (`stop` or `drive`), `verdict` (empty for none). A stop row has `badge`, optional `badge_color` (otherwise it follows the verdict), `time`, and `text` with the name and one key fact only ("<b>Carnegie Hall:</b> 8 PM concert starts"). A drive row has `text` with the drive time only ("3 min, 8 with buffer"). |
| `cover.watch_outs[]` | `icon` (`warn`, `event`, `hospital`, `police`, `fire`, `secure`, `car`), `text` |
| `weather` | `source`, `day`, `date`, `high`, `low`, `tag` (say "NORMAL FOR THE DATE, NOT A FORECAST" when it isn't one), `sunset`, `dark`, `lines[]` {`tone`: `note`, `muted` or `impact`, `text`} |
| `trip_map` | `title`, `image`, `legend` ([color, label] pairs), `caption`. The builder adds a QR code per place from the route lines: start, the end of each leg, skipping a place already listed. |
| `events` | `title`, `note`, `rows` ([what, where, effect on us], the full list), `key` (two or three short lines shown under the trip map: "<b>Radio City, 8 PM show:</b> crowd at 6th Ave as leg 2 passes."; if missing, the first three rows are used) |
| `legs[]` | one per drive, see below |
| `stops[]` | one per place, in driving order, see below. No stop pages: each overhead goes on its leg's map page. |
| `medical` | `from` (short stop names, one column each), `rows` ([place, type, one time per stop, check]; type `Police`, `Fire`, `Secure venue` or a text with "Trauma" gets an icon), `times_note`, `runs_title`, `runs[]` {`head`, `sub`, `steps[]`}, `runs_note`, `kit_note` |
| `recon` | `intro_short` (one line under the title), `rows` ([#, where, confirm], each a tick line), `day_of[]`, `comms_checks[]` (short tick lines; if missing, built from `code_words` and `comms_down`), `code_words` ([word, means]), `comms_down[]`, `confidence[]` (three lines: verified, estimated, not checked). `intro`, `code_note` and `rally_summary` are no longer printed. |
| `forms` | `recon_routes` (prefilled rows: [route, planned min, "", planned mi]), `recon_spots` (rows: [spot or stop]) |
| `terms` | optional [term, meaning] rows to replace the default key terms on page 1 |

## A leg

| Key | What it holds |
|---|---|
| `title`, `depart` | "Willard to The Anthem", "5:30 PM". The place names on the trip map page come from the title split on " to "; set `start_name` and `end_name` if the title isn't in that form. `dropoff_view` {`look_at`: [lon, lat]} aims the Street View code for this leg's drop-off: set `look_at` to the geocoded building or entrance for every leg. The point is on `primary.line`, set back 12 to 30 m from its end along the last straight stretch, and the heading faces `look_at`. Without `look_at` it looks square at the curb on the right (left when the arrive event's text says "on the left"). Optional `pt` and `heading` override by hand. |
| `map_image`, `map_routes` | leg map: primary blue, alternate amber, alternate 2 teal, numbered red spots. `map_routes` is how many routes the image shows (2 or 3). With 3 routes, draw a fresh map that includes the teal line; never reuse a 2-route image. The builder warns if `alternate2` is set and `map_routes` is under 3. |
| `primary`, `alternate`, `alternate2` | [route in words, distance, drive time]; the leg page shows distance and drive time only. `alternate2` only when 3 routes were asked for. |
| `shared`, `spots`, `closures_source`, `closures[]` | optional working notes; not printed on the leg page. Every spot, choke point and closure must also be in the strip notes. |
| `verdict` | [level, why] |
| `strip` | `primary` and `alternate` routes with `primary_notes` and `alternate_notes`; add `alternate2` and `alternate2_notes` for a third route. The place codes on the trip map page come from the first and last points of `primary.line`. Each route's own code (on its strip page) is built from its `line` and `events`. |

A strip route: `title` ("Leg 1 primary: Willard > The Anthem"), `line` (full geometry as [lon, lat]), `meters`, `minutes`, `depart`, `arrive`, `source` (like "Mapbox Directions, read Nov 9."), `events[]`. Each event has `at` (`start` or `end`) or `pt` ([lon, lat]), `side` (`L`, `R`, `S` for straight-on, or empty), `label`, `sub`, `text`, and optionally `cp` ("CP2: call in") and `red` (spot number). Optional `waypoints` on the route ([[lon, lat], ...], at most 3) replaces the points the builder picks for the route code; use it when a directions check through the picked points leaves the route. If the routing tool gives no turn coordinates, `turns(line)` in `scripts/strip.py` reads each turn's `pt` and `side` from the geometry.

Strip notes are [head, body, icon], where icon is `["spot", n]`, a kind like `warn` or `hospital`, or null.

## A stop

`title` (name, then address after a comma; the part before the comma labels the overhead), optional `short_name`, `image` (overhead view with lettered pins D, B, R), `points` (one short line: D, B and R in a few words, then who meets the car at D and when). `caption`, `kicker`, `overview`, `rows`, `verdict`, `handoff` and `flag` are no longer printed; put anything still to confirm on the checklist (`recon.rows`).

A leg may set `stop` (index into `stops`) to choose which overhead its map page shows. By default leg n shows the stop it drops off at; on a one-way trip the start's overhead also goes on leg 1.
