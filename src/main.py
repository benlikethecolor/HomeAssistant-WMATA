import os
import requests


api_key = os.environ['wmata_api']

HEADERS = {
    "api_key": api_key
}


def get_next_trains_at_station(station_code):
    url = "http://api.wmata.com/StationPrediction.svc/json/GetPrediction/%s" % station_code

    output = requests.get(url=url, headers=HEADERS)
    
    next_train_times = [train["Destination"] for train in output.json()["Trains"]]
    
    print(next_train_times)
    
    for train in next_train_times:
        print(train["Destination"])
        print(train["Line"])
        print(train["LocationName"])
        print(train["Min"])
        print()
    
    # for line in output.json()["Trains"]:
    #     print(line)
    
    # parse output


def main():
    station_code = "B03"
    
    get_next_trains_at_station(station_code)


if __name__ == "__main__":
    main()