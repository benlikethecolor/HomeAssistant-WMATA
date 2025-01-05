import requests
from .custom_components.const import DOMAIN, HEADERS, URL

from datetime import timedelta
import logging

import async_timeout


# TODO: https://developer.wmata.com/api-details#api=54763629281d83086473f231&operation=5476362a281d830c946a3d6c
# get bus schedule at stop


def get_next_buses_at_stop(stop_code: str):
    output = requests.get(
        headers=HEADERS, 
        url="%s/NextBusService.svc/json/jPredictions?StopID=%s" % (URL, stop_code)
    )
    
    bus_predictions = [bus for bus in output.json()["Predictions"]]
    
    print(bus_predictions)
    
    for bus in bus_predictions:
        print(bus["RouteID"])
        print(bus["DirectionText"])
        print(bus["Minutes"])
        print()
    
    return bus_predictions


def get_next_trains_at_station(station_code: str):
    output = requests.get(
        headers=HEADERS,
        url="%s/StationPrediction.svc/json/GetPrediction/%s" % (URL, station_code)
    )
    
    train_predictions = [train["Destination"] for train in output.json()["Trains"]]
    
    print(train_predictions)
    
    for train in train_predictions:
        print(train["Destination"])
        print(train["Line"])
        print(train["LocationName"])
        print(train["Min"])
        print()
        
    return train_predictions


def main():    
    train_predictions = get_next_trains_at_station("B03")
    
    bus_predictions = get_next_buses_at_stop("1001195")


if __name__ == "__main__":
    main()
