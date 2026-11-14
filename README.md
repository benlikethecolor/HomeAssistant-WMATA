# WMATA for Home Assistant

Live Metrorail and Metrobus arrivals for the Washington, DC area, in Home Assistant. Every station or bus stop you add gets an arrivals sensor and a departure-board card for your dashboard. You can also track your commute as travel-time sensors, plan trips between any two stations, and watch a live map of the trains running across the system.

![Station board card](docs/images/station-board.jpg)

*The station board, shown with `appearance: standard`.*

This is a hobby project. It isn't affiliated with or endorsed by WMATA.

## What you need

- Home Assistant 2024.12.5 or newer
- [HACS](https://hacs.xyz/docs/use/download/download/), unless you'd rather copy the files over yourself
- A free WMATA API key, which takes a couple of minutes to get

If you're coming from the old numbered sensors (`sensor.wmata_a01_train_1` and so on), read [Upgrading from 2.x](#upgrading-from-2x) before you update. Those entities go away.

## Getting an API key

1. Create an account at [developer.wmata.com](https://developer.wmata.com/).
2. Open **Products**, pick **Default Tier**, give the subscription a name ("Home Assistant" is fine), and click **Subscribe**.
3. Copy the primary key from your [profile page](https://developer.wmata.com/profile). It stays there if you need it again.

The default tier is free and includes the rail, bus, and train position APIs this integration calls. An account on its own isn't enough, though. Without a subscription you don't have a key, and setup will tell you the key was rejected.

## Installing

[![Open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=benlikethecolor&repository=HomeAssistant-WMATA&category=integration)

The button does the following for you:

1. In HACS, open the three-dot menu and choose **Custom repositories**.
2. Add `https://github.com/benlikethecolor/HomeAssistant-WMATA` with the type **Integration**.
3. Search for WMATA, download it, and restart Home Assistant.

No HACS? Download the [latest release](https://github.com/benlikethecolor/HomeAssistant-WMATA/releases/latest), copy `custom_components/wmata` into the `custom_components` folder of your Home Assistant config directory, and restart.

## Setting it up

[![Add the WMATA integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=wmata)

1. Go to **Settings → Devices & services → Add integration** and search for WMATA.
2. Paste your API key and choose what you're adding: a Metrorail station, a Metrobus stop, a commute between two stations, or the systemwide train map.
3. For rail, pick your station from the list. For a bus stop, move the pin on the map to where you catch the bus and submit. You'll get the closest stops with their routes and distance, nearest first. The pin starts at your Home Assistant home location.

For a commute, pick your home and work stations instead. Run through setup once for each thing you want. After the first one you can reuse the key you already saved instead of pasting it again.

You don't need station codes, and you don't need to know which platform your train leaves from. Transfer stations such as Metro Center and L'Enfant Plaza appear once in the list and cover all of their lines.

If you already know a bus stop's seven-digit ID, you can type it in and skip the map. It's printed on the sign at the stop, and [busETA](https://buseta.wmata.com/) shows it too. That's also the way to tell apart two stops with the same name on opposite sides of a street. The map search sends the pin's coordinates to WMATA to find stops, and nothing else.

### Adding the cards

The dashboard cards come with the integration, so there's nothing else to install and no resource to register. After the restart, reload your browser tab, edit a dashboard, and search for "WMATA" in the card picker:

| Card | What it's for |
| --- | --- |
| WMATA Station Board | Arrivals at one station or stop, or along a saved journey |
| WMATA Trip Planner | Working out a trip between any two Metro stations |
| WMATA Train Map | Where the trains are right now |

All three have a visual editor. The YAML in the sections below is there if you prefer it.

### The two setups most people want

**The next trains at my station.** Add your station, add a WMATA Station Board card, and pick the station in the card's editor. That's the whole thing. If you only care about trains heading one way, tap a direction chip on the card, such as Eastbound, or [pin the filter in YAML](#station-board).

**My commute.** Add a **Commute between two stations** entry with your home and work stations. Then add a WMATA Trip Planner card. It picks up the two stations by itself, plans the trip as soon as it loads, and has a **Reverse trip** button for the way home. The entry also gives you [travel-time sensors](#commute) for automations.

## Station board

Each station or stop has one sensor named Arrivals, for example `sensor.wmata_metro_center_arrivals`. Its state is the number of minutes until the next train or bus, and the whole board is in its `arrivals` attribute.

- `0` means a train is arriving or boarding.
- `unknown` means WMATA isn't predicting anything right now, which is normal overnight.
- `unavailable` means the request to WMATA failed.

```yaml
type: custom:wmata-station-card
entity: sensor.wmata_metro_center_arrivals
max_rows: 8
```

The chips along the top of the card filter by line and by direction of travel, and the dropdown under them filters by destination. Direction chips appear when trains are leaving in more than one direction. If you'd rather have a card that always shows the same thing, put the filter in YAML and hide the chips:

```yaml
type: custom:wmata-station-card
entity: sensor.wmata_metro_center_arrivals
title: Orange to New Carrollton
lines: [OR]
destinations: [D13]
show_filters: false
```

A destination is where the train ends its run, not where you get off. For an eastbound Orange Line train that's New Carrollton, even if you're only going as far as Eastern Market. YAML wants station codes for destinations, and they're all in [the station code list](docs/METRO_STATION_CODES.md).

| Option | Default | What it does |
| --- | --- | --- |
| `entity` | required | An Arrivals sensor or a saved journey |
| `title` | station or journey name | Heading shown on the card |
| `max_rows` | `8` | How many arrivals to list, 1 to 30 |
| `appearance` | `native` | `native`, `standard`, `minimal`, `glass`, or `daylight` |
| `show_filters` | `true` | Show the line, direction, and destination filters |
| `show_updated` | `true` | Show when the board last refreshed |
| `lines` | all | Rail line codes, such as `[BL, SV]` |
| `routes` | all | Bus routes, such as `[D34]` |
| `destinations` | all | Station codes, such as `[D13]` |
| `directions` | all | Rail directions, such as `[Eastbound]` |
| `show_destination_eta` | `true` | Journeys only: show the estimated arrival at your destination |
| `show_transfer_predictions` | `true` | Journeys only: show live boards for each transfer |
| `transfer_rows` | `3` | Trains listed per transfer, 1 to 10 |
| `transfer_buffer` | `3` | Minutes you want for changing platforms, 1 to 30 |

About `appearance`: the default, `native` (called "Home Assistant" in the editor), borrows the fonts, colors, and corners of the built-in cards, so it follows whatever theme you use. `standard` is the bolder departure-board look in the screenshot above. `minimal` drops the borders and headings, `glass` is translucent, and `daylight` switches between a light and a dark look with sunrise and sunset, regardless of your HA theme. All three cards take the same values.

Direction labels are worked out from where the train is and where it's going. That means the same Glenmont train is southbound at Dupont Circle and northbound at Union Station. When a direction can't be worked out, the card says so instead of guessing.

## Trip planner

This card plans a trip between any two Metro stations. It works two ways.

**As a commute card.** Give it both stations and it plans the trip the moment it loads, with the search fields tucked away. **Reverse trip** flips it for the way home, and **Change stations** brings the search back.

```yaml
type: custom:wmata-trip-planner
entity: sensor.wmata_commute_to_metro_center_travel_time
origin: Foggy Bottom-GWU
destination: Metro Center
reverse_after: "12:00"
```

`reverse_after` is optional. From that time of day the card starts on the return trip, and a dashboard that stays open all day flips over by itself when the time comes. Pressing **Reverse trip** overrides it until then. Keep the quotes around the time.

**As a planner.** Leave the stations out, type any two into the From and To fields, and press **Plan trip**. Nothing is saved and no entities are created.

| Option | Default | What it does |
| --- | --- | --- |
| `entity` | required | Any WMATA rail station, commute, or train map sensor. The card borrows that entry's API key |
| `origin`, `destination` | none | Station names. With both set, the card plans on its own |
| `reverse_after` | none | Time of day, such as `"12:00"`, to switch to the return trip |
| `show_form` | `false` for a commute | Keep the station search visible on a commute card |
| `transfer_buffer` | `3` | Minutes you want for changing platforms, 1 to 30 |
| `appearance` | `native` | Same values as the station board |
| `title` | "My commute" or "Metro trip planner" | Heading shown on the card |

Which entity you pick doesn't limit the stations you can search. It only decides whose API key is used.

The planner looks at routes with up to three transfers and puts the one that gets you there earliest on top, even when another route has fewer changes. Open **Compare routes** to see the alternatives and how much later each one arrives. Tap a route to look at it in detail, and **Use fastest option** takes you back to the automatic pick.

A few things worth knowing about the times:

- Live predictions are used wherever WMATA has them. They only reach so far ahead, so later connections come from the published timetable and are marked **Schedule estimate**. If the arrival time depends on one of those, it's labeled **Schedule-based arrival**.
- `transfer_buffer` is how long you want for getting between platforms. Raising it can change which route comes out fastest.
- Trips start on the platform. Walking to the station isn't counted.
- Routes with a leg that can't be estimated are listed last and never called fastest.

The card refreshes every 30 seconds while it's on screen.

## Commute

A **Commute between two stations** entry turns the same estimate into sensors, so automations can use it without a dashboard being open. You get three for each direction, named after where the trip ends:

| Sensor | What it tells you |
| --- | --- |
| **To Metro Center travel time** | Minutes from now until you'd arrive, including the wait for the train |
| **To Metro Center next train** | Minutes until the train you'd take leaves |
| **To Metro Center arrival** | The estimated arrival time |

They follow the fastest route at that moment, with the same rules as the trip planner card. The travel time sensor's attributes say which route that is, how many transfers it has, and whether any part of it relies on the timetable (`schedule_estimate`). When there isn't enough information for an honest estimate, the sensors read `unknown`.

```yaml
alias: Slow commute warning
triggers:
  - trigger: numeric_state
    entity_id: sensor.wmata_commute_to_metro_center_travel_time
    above: 35
conditions:
  - condition: time
    after: "07:00:00"
    before: "09:00:00"
    weekday: [mon, tue, wed, thu, fri]
actions:
  - action: notify.mobile_app_your_phone
    data:
      message: >
        Metro to work is taking
        {{ states('sensor.wmata_commute_to_metro_center_travel_time') }} minutes right now.
mode: single
```

A commute entry makes one request to WMATA per refresh, however many stations the routes pass through. The polling interval and the minutes allowed for changing platforms are under the entry's **Configure**.

## Train map

Add the **Systemwide train map** entry through the same setup as a station, then add the WMATA Train Map card. Click a train to see its line and destination, or a station to see what's arriving there. Stations on the map don't need their own entries.

![Train map card](docs/images/train-map.jpg)

```yaml
type: custom:wmata-train-map
entity: sensor.wmata_network_trains
view: geographic
height: 850
```

| Option | Default | What it does |
| --- | --- | --- |
| `entity` | found automatically | The map entry's Trains sensor |
| `view` | `geographic` | `geographic` draws on OpenStreetMap, `diagram` uses the official system map |
| `theme_mode` | `auto` | `auto`, `dark`, or `light` map colors |
| `dark_mode` | unset | `true` or `false`; overrides `theme_mode` |
| `height` | `750` | Card height in pixels, 250 to 1600. You can also drag the card's edge |
| `zoom` | `1` | Starting zoom for the diagram view, 1 to 4 |
| `appearance` | `native` | Frame style, same values as the station board |
| `tile_url` | OpenStreetMap | Tile URL template, if you'd rather use another provider |
| `tile_attribution` | OpenStreetMap credit | Attribution text for that provider |

WMATA reports which section of track a train is occupying, not GPS coordinates, so positions are approximate. Now and then a train is reported on track that can't be placed on the map, and it's left off rather than drawn somewhere misleading.

The geographic view downloads map tiles, so your browser needs internet access for it. The rail lines and the system diagram are bundled with the integration. Where they came from is in [GEO_SOURCES.md](custom_components/wmata/GEO_SOURCES.md).

The Trains sensor is a count of trains on the network. For automations about your own commute, use a station's sensors.

## Automations

The easiest trigger is the **Train due soon** binary sensor (**Bus due soon** at a bus stop). It's disabled by default, so open the station under **Settings → Devices & services → WMATA**, show the disabled entities, and enable it. It turns on whenever something is five minutes away or less, including trains that are arriving or boarding.

```yaml
alias: Metro train approaching
triggers:
  - trigger: state
    entity_id: binary_sensor.wmata_gallery_pl_chinatown_train_due_soon
    to: "on"
actions:
  - action: notify.mobile_app_your_phone
    data:
      message: A train is five minutes or less from Gallery Place.
mode: single
```

This fires when the sensor flips to on, so you get one notification rather than one per train while it stays on. To change the five minutes, or how often WMATA is polled, open the station's **Configure → Polling and arrival settings**.

Rail stations also have a disabled-by-default sensor for each line and direction, such as **Orange eastbound arrival** at Metro Center. Enable the one you care about and use a numeric state trigger ("below 6") on it. No templates needed.

A few more optional sensors exist for use with the built-in cards: **Next destination**, **Next line** (or **Next route** for buses), **Arrival count**, and **Last update**. All of them read from the board's existing data, so enabling them doesn't add API calls.

## Saved journeys

A journey is a named, filtered view of a station's board with its own sensor. It's for when you want a trip shown on that station's own board, with its transfer boards underneath. If you mostly want to know how long the trip takes, a [commute](#commute) is simpler. There are two kinds of journey, both under the station's **Configure** menu.

### Station-to-station

Choose **Add a station-to-station journey** on the station you leave from, then pick where you're going. You'll see the suggested route before anything is saved. Union Station to Huntington, for example, comes out as Red to Gallery Place, then Yellow. The suggestion goes for the fewest transfers first and the fewest stops second.

The journey's sensor counts down to the next train you can board at the origin, so it works in automations the same way an Arrivals sensor does.

Select the journey in a Station Board card and you get more than the origin board:

- An estimated arrival time at your destination, as both time on the train ("station to station") and time from now, which adds your wait for the first train.
- A live board for each transfer station, with the connection you're likely to make highlighted.
- **Use this train** on any origin departure, if you want to plan around a later train. It only affects that card, and **Use next train** puts it back. If the train you picked drops off the board, the card asks you to choose again.

The estimates follow the same rules as the trip planner: live predictions first, the timetable for later connections (marked **Schedule estimate**), and three minutes to change platforms unless you set `transfer_buffer` or **Minutes to change platforms** in the editor. Delays and service changes can throw them off. When there isn't enough information for an honest estimate, the card shows the time as unknown.

### Custom arrival filter

Choose **Add a custom arrival filter** to save a filter by line, final destination, and direction of travel, or by route and direction for buses. Bus direction numbers differ from route to route. If you're not sure which is which, look at the `direction` and `direction_id` values in the board's `arrivals` attribute.

Both kinds can be changed or removed later from the same menu.

## Upgrading from 2.x

Version 3 replaces the numbered train and bus sensors with one Arrivals sensor per station or stop. Dashboards and automations that use the old entities will need to be pointed at the new ones.

1. Back up Home Assistant.
2. Update through HACS and restart.
3. Your API keys, stations, stops, and polling intervals carry over. The numbered entities are removed.
4. Add the new cards, and set up a journey or filter for anything that used to depend on a specific numbered sensor.

If you had added both codes for a transfer station (A01 and C01 for Metro Center, say), you'll now have two entries that each show every platform. Delete one of them once nothing refers to it.

To go back, restore the backup along with the old integration files.

## Troubleshooting

**The key is rejected.** Check your [WMATA profile](https://developer.wmata.com/profile) to make sure there's an active subscription and that you copied the whole key.

**The cards aren't in the picker.** Restart Home Assistant, then do a hard refresh of the browser tab. If you ever added a WMATA JavaScript file as a dashboard resource by hand, remove it.

**The board is empty.** Check that the station is open and that you haven't filtered everything out, on the card or in the journey.

**The map background is blank.** Your browser can't reach the tile server. The diagram view works offline.

**A sensor is unavailable.** Look for WMATA entries in **Settings → System → Logs**. If the key changed, update it with **Reconfigure** on any entry. Other entries using the same key are updated at the same time. If you're running into rate limits, raise the polling interval from its default of 30 seconds under **Configure → Polling and arrival settings**.

When you [open an issue](https://github.com/benlikethecolor/HomeAssistant-WMATA/issues), include your Home Assistant version, the integration version, and what the logs say. **Download diagnostics** in the entry's three-dot menu produces a file with status and counts only. It leaves out your key, your stations, and your journey names. Do look over any logs or screenshots yourself before posting them.

## Contributing

Notes on running the tests, cutting a release, and rebuilding the map data are in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Thanks

- WMATA, for making this data available
- [@walrus416](https://github.com/walrus416), whose [ha-wmata](https://github.com/walrus416/ha-wmata) was the starting point
- [@msp1974](https://github.com/msp1974), for the [integration examples](https://github.com/msp1974/HAIntegrationExamples)
- [@wtadler](https://github.com/wtadler), for the bus stop ID tips
