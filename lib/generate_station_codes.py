import csv
import os
import requests

api_key = os.environ['wmata_api']

HEADERS = {
    "api_key": api_key
}

def update_file(filename: str, data: str):
    new_file = open(filename, "w")
    new_file.write(data)


def get_train_stations():
    output = requests.get(
        headers=HEADERS, 
        url="https://api.wmata.com/Rail.svc/json/jStations"
    )
        
    train_stations = output.json()["Stations"]
    train_stations.sort(key=lambda x: x['Name'])
    
    readme_output = '| Name | Line | Code\n|:-----|:----:|:-----|\n'
    
    for station in train_stations:
        readme_output += '| %s | %s | %s |\n' % (station['Name'], station['LineCode1'], station['Code'])
    
    print(readme_output)
    
    update_file("METRO_STATION_CODES.md", readme_output)
    

def main():
    get_train_stations()


if __name__ == "__main__":
    main()
