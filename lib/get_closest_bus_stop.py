import json
import os
import requests


api_key = os.environ['wmata_api']

HEADERS = {
    "api_key": api_key
}


def get_closest_bus_stop(latitude:str, longitude:str, radius:str):
    output = requests.get(
        headers=HEADERS,
        url="http://api.wmata.com/Bus.svc/json/jStops?Lat=%s&Lon=%s&Radius=%s" % (latitude, longitude, radius)
    )

    print(json.dumps(output.json(), indent=4))


def main():
    latitude = input('Enter your latitude:\n')
    longitude = input('Enter your longitude:\n')
    
    get_closest_bus_stop(
        latitude=latitude,
        longitude=longitude,
        radius="500"
    )


if __name__ == '__main__':
    main()
