import json
import os
import requests


api_key = os.environ['wmata_api']

HEADERS = {
    "api_key": api_key
}


def get_bus_stop_name(bus_stop:str):
    output = requests.get(
        headers=HEADERS,
        url="http://api.wmata.com/Bus.svc/json/jStopSchedule?StopID=%s" % (bus_stop)
    )

    print(json.dumps(output.json(), indent=4))
    
    print(output.json()['Stop']['Name'])


def main():
    get_bus_stop_name("6000305")


if __name__ == '__main__':
    main()


