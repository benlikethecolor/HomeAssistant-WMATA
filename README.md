# HomeAssistant-WMATA

WORK IN PROGRESS

Integration to connect with the WMATA API to report upcoming trains/buses at local stops. 

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

Unfortunately there's no good way to see a list of all of the bus station stop or metro station codes online outside of using the API. I've provided a list of the [metro station codes in this file](https://github.com/benlikethecolor/HomeAssistant-WMATA/blob/main/METRO_STATION_CODES.md). Simply open it, find your local metro station, and add the code next to it. 

**IMPORTANT NOTE:** if you see that your "local" metro station has two entries, make sure to pick the entry with the line you want. For example, say your local metro station is "Metro Center", and you ride the orange line. In this case, you would select the station code "C01", not "A01". 


## Thanks

- WMATA for providing this API
- [@walrus416](https://github.com/walrus416) for making a [similar integration](https://github.com/walrus416/ha-wmata/tree/master) as a starting point
- [@msp1974](https://github.com/msp1974) for providing [helpful integration examples](https://github.com/msp1974/HAIntegrationExamples)
