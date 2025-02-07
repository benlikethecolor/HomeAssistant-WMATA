import json
import os
import requests


api_key = os.environ['wmata_api']

HEADERS = {
    "api_key": api_key
}


def get_next_trains(train_station:str):
    output = requests.get(
        headers=HEADERS,
        url="http://api.wmata.com/StationPrediction.svc/json/GetPrediction/%s" % train_station
    )

    print(json.dumps(output.json(), indent=4))


def main():
    train_station = input('Enter your train station ID:\n')
    
    get_next_trains(train_station=train_station)


if __name__ == '__main__':
    main()
