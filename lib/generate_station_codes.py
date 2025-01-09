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
        print(station)
        lines = [station['LineCode1']]
        
        if station['LineCode2']:
            lines.append(station['LineCode2'])
        if station['LineCode3']:
            lines.append(station['LineCode3'])
        if station['LineCode4']:
            lines.append(station['LineCode4'])
        
        for line in lines:
            if line == 'BL':
                lines[lines.index(line)] = 'Blue'
            elif line == 'GR':
                lines[lines.index(line)] = 'Green'
            elif line == 'OR':
                lines[lines.index(line)] = 'Orange'
            elif line == 'RD':
                lines[lines.index(line)] = 'Red'
            elif line == 'SV':
                lines[lines.index(line)] = 'Silver'
            elif line == 'YL':
                lines[lines.index(line)] = 'Yellow'
            
        lines.sort()
        lines = ', '.join(lines)
                
        readme_output += '| %s | %s | %s |\n' % (station['Name'], lines, station['Code'])
    
    print(readme_output)
    
    update_file("METRO_STATION_CODES.md", readme_output)
    

def main():
    get_train_stations()


if __name__ == "__main__":
    main()
