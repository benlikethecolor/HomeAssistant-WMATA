# HomeAssistant-WMATA

Integration to connect with the WMATA API to report upcoming trains/buses at local stops. 

<p align="center"><img src="https://github.com/benlikethecolor/HomeAssistant-WMATA/blob/main/docs/images/Sensor%20Samples.png?raw=true" width="70%"></p>

## Installation

To install this integration, you need the following:

- WMATA API key
- Metro station ID

Instructions on how to get these values are below. 

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

## Setting Up Multiple Stations

If you want to have trains for multiple stations setup, follow these steps:

1. Go to "Settings" > "Integrations" > "WMATA"
2. Select "Add Hub"
3. Enter your API key again, along with the new station ID
4. Select "Submit"

After this is completed, you should see the new entities appear for the new station, like the below. 

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

## Future Improvments?

- Change the way that this is setup, so that you only need one station ID for stations with multiple codes. Just enter one or the other, have the code just search for both while you're there
- Currently not setup for buses, this will be a future improvement. 

## Thanks

- WMATA for providing this API
- [@walrus416](https://github.com/walrus416) for making a [similar integration](https://github.com/walrus416/ha-wmata/tree/master) as a starting point
- [@msp1974](https://github.com/msp1974) for providing [helpful integration examples](https://github.com/msp1974/HAIntegrationExamples)
