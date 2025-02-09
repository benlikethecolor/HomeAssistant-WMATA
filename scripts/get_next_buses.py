import json
import os
import requests


api_key = os.environ['wmata_api']

HEADERS = {
    "api_key": api_key
}


def get_next_buses(bus_stop:str):
    output = requests.get(
        headers=HEADERS,
        url="http://api.wmata.com/NextBusService.svc/json/jPredictions?StopID=%s" % bus_stop
    )

    print(json.dumps(output.json(), indent=4))


def main():
    bus_stop = input('Enter your bus stop ID:\n')
    
    get_next_buses(bus_stop=bus_stop)


if __name__ == '__main__':
    main()
