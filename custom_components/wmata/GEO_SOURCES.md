# Geographic rail geometry

The geographic view uses a bundled snapshot of WMATA's public GIS data in EPSG:4326, with station coordinates from the Rail Station Information API.

Sources retrieved November 12, 2026:

- Rail Lines: https://services2.arcgis.com/2NBEaAVPObxRmRog/arcgis/rest/services/WMATA_Rail_Map_WFL1/FeatureServer/14
- Dulles Phase 2: https://services2.arcgis.com/2NBEaAVPObxRmRog/arcgis/rest/services/WMATA_Rail_Map_WFL1/FeatureServer/15
- Station catalog: https://api.wmata.com/Rail.svc/json/jStations
- Basemap attribution: © OpenStreetMap contributors, https://www.openstreetmap.org/copyright

geo_shapes.json contains station-to-station route shapes resampled by distance. www/geo_routes.json contains display paths and station labels. Station coordinates are projected onto rail polylines. The maximum station projection distance in this snapshot was 258 metres. Circuit positions use circuit order rather than measured circuit lengths, so train locations remain estimates.

Train markers use the same geometry drawn on the map. The official diagram uses separate schematic route_shapes.json.
