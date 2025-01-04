import os
import requests


api_key = os.environ['wmata_api']

HEADERS = {
    "api_key": api_key
}


def get_next_buses_at_stop(stop_code):
    url = "http://api.wmata.com/NextBusService.svc/json/jPredictions?StopID=%s" % stop_code
    
    output = requests.get(url=url, headers=HEADERS)
    
    bus_predictions = [bus for bus in output.json()["Predictions"]]
    
    print(bus_predictions)
    
    for bus in bus_predictions:
        print(bus["RouteID"])
        print(bus["DirectionText"])
        print(bus["Minutes"])
        print()


def get_next_trains_at_station(station_code):
    url = "http://api.wmata.com/StationPrediction.svc/json/GetPrediction/%s" % station_code

    output = requests.get(url=url, headers=HEADERS)
    
    train_predictions = [train["Destination"] for train in output.json()["Trains"]]
    
    print(train_predictions)
    
    for train in train_predictions:
        print(train["Destination"])
        print(train["Line"])
        print(train["LocationName"])
        print(train["Min"])
        print()
    
    # for line in output.json()["Trains"]:
    #     print(line)
    
    # parse output


def main():    
    get_next_trains_at_station("B03")
    
    get_next_buses_at_stop("1001195")


if __name__ == "__main__":
    main()
