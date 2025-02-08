# HomeAssistant-WMATA

Integration to connect with the WMATA API to report upcoming trains/buses at local stops. 

<p align="center"><img src="https://github.com/benlikethecolor/HomeAssistant-WMATA/blob/main/docs/images/Train%20Samples.png?raw=true" width="70%"></p>
<p align="center"><img src="https://github.com/benlikethecolor/HomeAssistant-WMATA/blob/main/docs/images/Bus%20Samples.png?raw=true" width="70%"></p>

## Installation

To install this integration, you will need to have HACS installed. If you do not have HACS installed, download it by [following the instructions here](https://hacs.xyz/docs/setup/download/).

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

## Setup

To setup this integration, you will need these values:

- WMATA API key
- Metro Station ID or Bus Stop ID

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

Similar to the metro station ID process, there's no good way to get your bus stop ID. The easiest way is to check your bus stop, the sign will show a 7 digit number on the bottom right that is the bus stop ID. 

Another option is to use the script in this repository in /lib/get_closest_bus_stop.py. If you run this, you'll enter your latitude and longitude and it will show you the closest bus stops. One of these options should be able to get you the bus stop ID you're looking for. 

## Setting Up Multiple Stations/Stops

If you want to have buses/trains for multiple stations setup, follow these steps:

1. Go to "Settings" > "Integrations" > "WMATA"
2. Select "Add Hub"
3. Enter your API key again, along with the new station/stop ID
4. Select "Submit"

After this is completed, you should see the new entities appear for the new station, like the below:
<p align="center"><img src="https://github.com/benlikethecolor/HomeAssistant-WMATA/blob/main/docs/images/Multiple%20Stations%20Sensors.png?raw=true" width="50%"></p>

## Dashboards

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

### Mushroom

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
```

## Future Improvements

- Change the way that this is setup so that you only need one station ID for stations with multiple codes. Just enter one or the other, have the code just search for both while you're there
- Make a better interactive way to find your bus stop ID when initializing the integration

## Thanks

- WMATA for providing this API
- [@walrus416](https://github.com/walrus416) for making a [similar integration](https://github.com/walrus416/ha-wmata/tree/master) as a starting point
- [@msp1974](https://github.com/msp1974) for providing [helpful integration examples](https://github.com/msp1974/HAIntegrationExamples)
