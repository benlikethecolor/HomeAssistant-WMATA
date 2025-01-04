import csv
import os
import requests

api_key = os.environ['wmata_api']

HEADERS = {
    "api_key": api_key
}

def update_file(filename: str, data: dict):
    new_file = open("../data/%s" % filename, "w", newline="")
    writer = csv.DictWriter(new_file, data[0].keys())
    writer.writeheader()
    writer.writerows(data)


def update_train_stations():
    output = requests.get(
        headers=HEADERS, 
        url="https://api.wmata.com/Rail.svc/json/jStations"
    )
    
    # print(json.dumps(output.json(), indent=4))
    
    new_train_stations = output.json()["Stations"]
    
    update_file("station_codes.csv", new_train_stations)
    

def main():
    update_train_stations()


if __name__ == "__main__":
    main()
