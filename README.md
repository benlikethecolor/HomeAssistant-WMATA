# WMATA for Home Assistant

Metrorail and Metrobus arrivals in Home Assistant, with a board for each station or stop and a map of trains across the system. You can also save a filtered journey, such as Red Line trains to Shady Grove, and use its arrival time in automations.

Requires **Home Assistant 2024.12.5 or newer**. If you're updating from the old numbered sensors, see [Upgrading](#upgrading).

## Installation

1. Get a key from the [WMATA developer portal](https://developer.wmata.com/). You'll need an active subscription to the APIs you want to use:

   | Feature | APIs |
   | --- | --- |
   | Rail arrivals | Rail Station Information, Real-Time Rail Predictions |
   | Bus arrivals | Bus Route and Stop Methods, Real-Time Bus Predictions |
   | Train map | Train Positions, including Standard Routes and Track Circuits |
   | Station arrivals on the map | Real-Time Rail Predictions |

2. In HACS, add `https://github.com/benlikethecolor/HomeAssistant-WMATA` as a custom repository with category **Integration**, install WMATA, and restart Home Assistant. For a manual install, copy `custom_components/wmata` into your HA configuration's `custom_components` folder.
3. Go to **Settings → Devices & services → Add integration → WMATA**, enter your key, and choose Metrorail, Metrobus, or Systemwide train map.
4. For rail, choose a station. For bus, enter the seven-digit stop ID from [busETA](https://buseta.wmata.com/) or the stop sign. Add another WMATA entry for each station or stop; choose a saved key instead of typing it again. Transfer stations include both sets of platforms.
5. Refresh your browser, edit a dashboard, and add **WMATA Station Board** or **WMATA train map**. Choose the sensor by name in the card editor. Both cards are included with the integration, so there's no separate frontend download.

## Arrival boards

Each station or stop gets one Arrivals sensor. Its value is the number of minutes until the next train or bus, and its `arrivals` attribute holds the full list. A value of `0` means arriving or boarding; `unknown` means there's no numeric estimate, and `unavailable` means the data couldn't be fetched.

![Example station board](docs/images/station-board-v4.jpg)

In the card editor, choose the station by name. You don’t need to look up a station code. New entities have readable IDs; existing entities keep their IDs. Here’s a YAML example for Metro Center, which serves Red, Orange, Blue, and Silver:

~~~yaml
type: custom:wmata-station-card
entity: sensor.wmata_metro_center_arrivals
max_rows: 8
~~~

Use the filters on the card to choose lines and destinations. To save a filter in YAML:

~~~yaml
type: custom:wmata-station-card
entity: sensor.wmata_metro_center_arrivals
title: Orange to New Carrollton
lines: [OR]
destinations: [D13]
show_filters: false
~~~

Destinations are the train's final stop, not an intermediate station you want to visit. For example, choose New Carrollton for eastbound Orange trains. See the [station codes](docs/METRO_STATION_CODES.md) for YAML destination values.

| Option | Default | Values |
| --- | --- | --- |
| `entity` | Required | Station, stop, or journey sensor |
| `title` | Station/journey name | Custom title |
| `max_rows` | `8` | 1–30 |
| `show_filters` | `true` | Show line/route and destination filters |
| `show_updated` | `true` | Show when arrivals were updated |
| `appearance` | `standard` | `standard`, `daylight`, `orbit`, `bento` |
| `lines` | All | Rail codes, e.g. `[BL, SV]` |
| `routes` | All | Bus route IDs, e.g. `[D34]` |
| `destinations` | All | Station codes, e.g. `[D13]` |

Direction labels depend on the station and route. A Glenmont train, for example, is southbound at Dupont Circle and northbound at Union Station. If its direction can't be determined, the card says so.

## Automations and optional sensors

For a simple “a train is coming” automation, open the station’s device page, show its disabled entities, and enable **Train due soon** (or **Bus due soon**). It turns on when an arrival is within five minutes, including arriving and boarding trains. Change the threshold under **Configure → Polling and arrival settings**.

For example, after enabling it at Gallery Place:

~~~yaml
alias: Metro train approaching
triggers:
  - trigger: state
    entity_id: binary_sensor.wmata_gallery_pl_chinatown_train_due_soon
    to: "on"
actions:
  - action: notify.mobile_app_your_phone
    data:
      message: A train is due at Gallery Place within five minutes.
mode: single
~~~

Choose the entity by its displayed name in the automation editor, or replace the example ID with yours. This fires when the sensor changes to on, rather than once for every train while it stays on.

Rail stations also offer disabled-by-default arrival sensors for each line and direction. At Metro Center, enable **Orange eastbound arrival**, then use a numeric-state trigger below 6. These report minutes and need no saved journey or template. Optional **Next destination**, **Next line/route**, **Arrival count**, and **Last update** sensors are available too. They all share the board’s polling.

For more specific filters, use **Configure → Add a journey**. Give it a name and choose lines, final destinations, or direction. For example, save “Red to Shady Grove” at Dupont Circle. Its sensor reports minutes until the next matching train. For buses, choose routes and direction; direction numbers vary by route, so check the board’s `direction` and `direction_id` attributes if you’re unsure. Multiple choices in one filter match either choice; separate filters must all match.

The map's Trains sensor is a train count, so use a station sensor for arrival automations.

## Train map

Add a Systemwide train map entry, then add its card. Click a train for details or a station for upcoming arrivals. You don't need a separate integration entry for each station on the map.

![Example train map](docs/images/train-map-v4.jpg)

~~~yaml
type: custom:wmata-train-map
entity: sensor.wmata_network_trains
view: geographic
theme_mode: auto
height: 850
~~~

| Option | Default | Values |
| --- | --- | --- |
| `entity` | Suggested automatically | Network Trains sensor |
| `view` | `geographic` | `geographic` for OpenStreetMap, or `diagram` for the official map |
| `theme_mode` | `auto` | `auto`, `dark`, or `light` |
| `dark_mode` | Unset | Boolean override of `theme_mode` |
| `height` | `750` | 250–1600 pixels; you can also drag to resize |
| `zoom` | `1` | Diagram zoom, 1–4 |
| `tile_url` | OSM tiles | Custom tile URL template |
| `tile_attribution` | OSM attribution | Attribution for your tile provider |

Train positions are estimates based on track circuits, not GPS. Some trains may be reported on circuits that can't be placed on the map. The refresh timestamp shows the last successful update.

The geographic view needs internet access for map tiles. Rail geometry and the official diagram are included locally; [map sources and attribution](custom_components/wmata/GEO_SOURCES.md) are listed separately.

## Upgrading

Version 4 replaces the numbered train/bus sensors with one Arrivals sensor per station or stop. **Old entity references in dashboards and automations need to be updated.**

Back up HA before updating. Your API keys, stations, stops, and polling intervals are kept, but the old numbered entities and global line/route filters are removed. After restarting HA, find the new Arrivals sensors under WMATA, add the new cards, and create journeys for any filtered automations.

If you previously added both codes for a transfer station, both entries will now show all its platforms. You can remove the duplicate once you've updated its references. To roll back, restore both the old integration files and your HA backup.

## If something isn't working

- **Key rejected:** check that your WMATA subscription is active and covers the APIs above. Creating a developer account alone isn't enough.
- **Card missing:** restart HA and refresh the browser. Remove any old WMATA JavaScript resources you added manually.
- **Empty arrivals:** check service hours, station/stop selection, and filters.
- **Blank basemap:** check whether your browser can reach the tile provider.
- **Unavailable sensor:** check **Settings → System → Logs** for WMATA errors. You can change the key through **Reconfigure** and the polling interval through **Configure → Polling and arrival settings**. Changing a shared key updates its other entries after checking that the new key works for them. The default is 30 seconds; increase it if you're hitting API limits.

When reporting an issue, include your HA and integration versions, station or stop, and relevant logs. You can download diagnostics from the WMATA entry’s menu under **Settings → Devices & services**. Diagnostics include status and counts, leaving out keys, selected locations, and journey names. Review any logs or screenshots before attaching them.

For tests, packaging, and map maintenance, see [Development](docs/DEVELOPMENT.md).

Thanks to [walrus416](https://github.com/walrus416/ha-wmata) for the original inspiration and [msp1974](https://github.com/msp1974/HAIntegrationExamples) for the integration examples.
