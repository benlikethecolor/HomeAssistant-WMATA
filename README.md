# HomeAssistant-WMATA

Integration to connect with the WMATA API to report upcoming trains/buses at local stops. 

<!-- [![Stars](https://img.shields.io/github/stars/benlikethecolor/HomeAssistant-WMATA)](#) -->
[![Last commit](https://img.shields.io/github/last-commit/benlikethecolor/HomeAssistant-WMATA)](#)

<p align="center"><img src="https://github.com/benlikethecolor/HomeAssistant-WMATA/blob/main/docs/images/Tile.png?raw=true" width="80%"></p>

## Installation

To install this integration, you will need to have HACS installed. If you do not have HACS installed, download it by [following the instructions here](https://hacs.xyz/docs/use/download/download/).

After HACS is installed, you should be able to click this button to install this integration:

[![Open Bubble Card on Home Assistant Community Store (HACS).](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=benlikethecolor&repository=WMATA&category=integration)

If the above doesn't work, here's the manual installation steps:

1. Open HACS in Home Assistant
2. Select the three dots in the upper right, and select "Custom repositories"
3. In the popup, enter the URL of this page in the "Repository" spot, select the type as "Integration", and select "Add"
4. Within HACS, search for WMATA
5. Click the WMATA entry, and select "Download"
6. Now, setup the integration by going to "Settings" > "Devices & services"
7. Select "Add integration"
8. Search for "WMATA"
9. Enter your WMATA API key and metro station ID/bus stop ID
10. Select "Submit", and you should see the sensors appear!

### Getting a WMATA API Key

To get a WMATA API key, follow these steps:

1. Sign up for a new [WMATA developer account here](https://developer.wmata.com/)
2. After your account is created, go to "Products", and select "Default Tier"
3. On this page, enter the name of your new API key (ex: "Home assistant"), agree to the terms of use, and select "Subscribe"
4. After your key is created, it will show you your API key, enter that in the installation steps

If you ever lose or forget your API details, you can find it [on your profile](https://developer.wmata.com/profile) under "Subscriptions". 

### Getting Your Metro Station ID

Unfortunately there's no good way to see a list of all of the bus station stop or metro station codes online outside of using the API. I've provided a list of the [metro station codes in this file](https://github.com/benlikethecolor/HomeAssistant-WMATA/blob/main/docs/METRO_STATION_CODES.md). Simply open it, find your local metro station, and add the code next to it. 

**IMPORTANT NOTE:** if you see that your "local" metro station has two entries, make sure to pick the entry with the line you want. For example, say your local metro station is "Metro Center", and you ride the orange line. In this case, you would select the station code "C01", not "A01". 

### Getting Your Bus Stop ID

To get your Bus Stop ID, use WMATA's [busETA](https://buseta.wmata.com/) website to locate your stop. The Bus Stop ID is a 7-digit code. Alternatively, the sign physically placed by your bus stop should have the ID printed on the bottom-right.

## Setting Up Multiple Stations/Stops

If you want to have buses/trains for multiple stations setup, follow these steps:

1. Go to "Settings" > "Integrations" > "WMATA"
2. Select "Add Hub"
3. Enter your API key again, along with the new station/stop ID
4. Select "Submit"

After this is completed, you should see the new entities appear for the new station, like the below:
<p align="center"><img src="https://github.com/benlikethecolor/HomeAssistant-WMATA/blob/main/docs/images/Multiple%20Stations%20Sensors.png?raw=true" width="50%"></p>

## Dashboards

### Tile Card

If you use tile card, here's a quick sample I've created using this integration.

<p align="center"><img src="https://github.com/benlikethecolor/HomeAssistant-WMATA/blob/main/docs/images/Tile.png?raw=true" width="80%"></p>

```yaml
type: tile
  entity: sensor.wmata_g01_train_1
  features_position: bottom
  vertical: false
  state_content:
    - state
    - Line
    - Destination
```

### Bubble Card

If you use bubble card, here's a quick sample I've created using this integration. 

<p align="center"><img src="https://github.com/benlikethecolor/HomeAssistant-WMATA/blob/main/docs/images/Bubble%20Card.png?raw=true" width="90%"></p>

```yaml
type: custom:bubble-card
card_type: button
button_type: name
name: Train 1
icon: mdi:train
sub_button:
  - entity: sensor.wmata_a01_train_1_destination
    show_name: false
    show_state: true
  - entity: sensor.wmata_a01_train_1_line
    show_state: true
  - entity: sensor.wmata_a01_train_1_time
    show_state: true
    show_attribute: false
    show_name: false
    show_last_changed: false
    show_background: true
    state_background: true
```
### Mushroom Template Badge

The [Mushroom package](https://github.com/piitaya/lovelace-mushroom) allows you to make a nice [Mushroom Template badge](https://github.com/piitaya/lovelace-mushroom/blob/main/docs/badges/template.md) like so:

![Badge image](docs/images/Badge.png)

```yaml
type: custom:mushroom-template-badge
content: >-
  {% set bus_times = states.sensor | selectattr('entity_id', 'search',
  'wmata_STOP_ID_bus_') | map(attribute='state') | list %}

  {{ bus_times | reject('equalto', 'unknown') | map('regex_replace', '^(.+)$',
  '\\1m') | join(' • ') }}
icon: mdi:bus
color: green
visibility:
  - condition: state
    entity: sensor.wmata_STOP_ID_bus_1
    state_not:
      - unavailable
      - unknown
label: Next buses
entity: sensor.wmata_STOP_ID_bus_1
tap_action:
  action: more-info
```

<!-- ### Mushroom

If you use mushroom, here's a quick sample I've created using this integration. 

<p align="center"><img src="https://github.com/benlikethecolor/HomeAssistant-WMATA/blob/main/docs/images/Mushroom.png?raw=true" width="80%"></p>

```yaml
type: horizontal-stack
cards:
  - type: custom:mushroom-entity-card
    entity: sensor.wmata_a01_train_1_destination
  - type: custom:mushroom-entity-card
    entity: sensor.wmata_a01_train_1_line
  - type: custom:mushroom-entity-card
    entity: sensor.wmata_a01_train_1_time
``` -->

## Future Improvements

- Change the way that this is setup so that you only need one station ID for stations with multiple codes. Just enter one or the other, have the code just search for both while you're there
- Make a better interactive way to find your bus stop ID when initializing the integration

## Thanks

- WMATA for providing this API
- [@walrus416](https://github.com/walrus416) for making a [similar integration](https://github.com/walrus416/ha-wmata/tree/master) as a starting point
- [@msp1974](https://github.com/msp1974) for providing [helpful integration examples](https://github.com/msp1974/HAIntegrationExamples)
