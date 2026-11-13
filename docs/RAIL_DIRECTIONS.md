# Rail travel directions

Arrival rows use travel directions rather than WMATA prediction Group numbers. The integration resolves the station and train terminus on the selected line, finds the next station, and labels travel along that part of the corridor. Short-turn termini work the same way. The normalized arrival exposes direction, next_station and next_station_code for templates and automations.

Directions use corridor conventions rather than the instantaneous compass bearing around each bend:

- Orange/Silver: east/west.
- Blue: north/south on the Virginia branch; east/west through downtown and the eastern branch. At Rosslyn, Blue trains toward Franconia-Springfield are southbound and trains toward downtown are eastbound.
- Yellow/Green: north/south.
- Red: north/south on the two outer legs, east/west through Metro Center, Gallery Place and Judiciary Square. Thus a Glenmont train is southbound at Dupont Circle, eastbound at Metro Center and northbound at Union Station.

Route order follows WMATA's [official system map](https://www.wmata.com/content/dam/wmata-com/maps/system-map-rail.pdf) and [Standard Routes API](https://api.wmata.com/TrainPositions/StandardRoutes?contentType=json). These compass labels are derived by this integration; WMATA's prediction API does not supply a compass direction. They describe route travel, not an official platform number or station-sign label.

Both platform codes at transfer stations are resolved against the train's line. The topology includes Potomac Yard, Yellow service toward Greenbelt, and either eastern branch for Orange/Blue/Silver service. It does not infer direction from the final destination's geographic bearing or from Group. Single tracking does not reverse the label merely because the train uses the other track.

If the station, line or destination cannot be resolved, or the train terminates at the current station, direction is null and the card shows “Direction unavailable”. A direction-filtered journey excludes these rows. Destination labels and arrival estimates remain visible.

The raw group attribute remains available to existing templates and old journey filters. New journey forms offer travel direction instead. Editing an old group-filtered journey replaces that track filter with the selected travel-direction filter.

## Station coverage

The reference below lists each published station/line pairing and its two adjacent-station directions. At a terminal there is one departure direction. Branches and curves can give different labels at the same physical station. Additional eastern-branch service follows the same east/west convention.

### Blue

| Station | Toward previous stop | Toward next stop |
| --- | --- | --- |
| Franconia-Springfield (J03) | — | Northbound → Van Dorn Street |
| Van Dorn Street (J02) | Southbound → Franconia-Springfield | Northbound → King St-Old Town |
| King St-Old Town (C13) | Southbound → Van Dorn Street | Northbound → Braddock Road |
| Braddock Road (C12) | Southbound → King St-Old Town | Northbound → Potomac Yard |
| Potomac Yard (C11) | Southbound → Braddock Road | Northbound → Ronald Reagan Washington National Airport |
| Ronald Reagan Washington National Airport (C10) | Southbound → Potomac Yard | Northbound → Crystal City |
| Crystal City (C09) | Southbound → Ronald Reagan Washington National Airport | Northbound → Pentagon City |
| Pentagon City (C08) | Southbound → Crystal City | Northbound → Pentagon |
| Pentagon (C07) | Southbound → Pentagon City | Northbound → Arlington Cemetery |
| Arlington Cemetery (C06) | Southbound → Pentagon | Northbound → Rosslyn |
| Rosslyn (C05) | Southbound → Arlington Cemetery | Eastbound → Foggy Bottom-GWU |
| Foggy Bottom-GWU (C04) | Westbound → Rosslyn | Eastbound → Farragut West |
| Farragut West (C03) | Westbound → Foggy Bottom-GWU | Eastbound → McPherson Square |
| McPherson Square (C02) | Westbound → Farragut West | Eastbound → Metro Center |
| Metro Center (C01) | Westbound → McPherson Square | Eastbound → Federal Triangle |
| Federal Triangle (D01) | Westbound → Metro Center | Eastbound → Smithsonian |
| Smithsonian (D02) | Westbound → Federal Triangle | Eastbound → L'Enfant Plaza |
| L'Enfant Plaza (D03) | Westbound → Smithsonian | Eastbound → Federal Center SW |
| Federal Center SW (D04) | Westbound → L'Enfant Plaza | Eastbound → Capitol South |
| Capitol South (D05) | Westbound → Federal Center SW | Eastbound → Eastern Market |
| Eastern Market (D06) | Westbound → Capitol South | Eastbound → Potomac Ave |
| Potomac Ave (D07) | Westbound → Eastern Market | Eastbound → Stadium-Armory |
| Stadium-Armory (D08) | Westbound → Potomac Ave | Eastbound → Benning Road |
| Benning Road (G01) | Westbound → Stadium-Armory | Eastbound → Capitol Heights |
| Capitol Heights (G02) | Westbound → Benning Road | Eastbound → Addison Road-Seat Pleasant |
| Addison Road-Seat Pleasant (G03) | Westbound → Capitol Heights | Eastbound → Morgan Boulevard |
| Morgan Boulevard (G04) | Westbound → Addison Road-Seat Pleasant | Eastbound → Downtown Largo |
| Downtown Largo (G05) | Westbound → Morgan Boulevard | — |

### Green

| Station | Toward previous stop | Toward next stop |
| --- | --- | --- |
| Branch Ave (F11) | — | Northbound → Suitland |
| Suitland (F10) | Southbound → Branch Ave | Northbound → Naylor Road |
| Naylor Road (F09) | Southbound → Suitland | Northbound → Southern Avenue |
| Southern Avenue (F08) | Southbound → Naylor Road | Northbound → Congress Heights |
| Congress Heights (F07) | Southbound → Southern Avenue | Northbound → Anacostia |
| Anacostia (F06) | Southbound → Congress Heights | Northbound → Navy Yard-Ballpark |
| Navy Yard-Ballpark (F05) | Southbound → Anacostia | Northbound → Waterfront |
| Waterfront (F04) | Southbound → Navy Yard-Ballpark | Northbound → L'Enfant Plaza |
| L'Enfant Plaza (F03) | Southbound → Waterfront | Northbound → Archives-Navy Memorial-Penn Quarter |
| Archives-Navy Memorial-Penn Quarter (F02) | Southbound → L'Enfant Plaza | Northbound → Gallery Pl-Chinatown |
| Gallery Pl-Chinatown (F01) | Southbound → Archives-Navy Memorial-Penn Quarter | Northbound → Mt Vernon Sq 7th St-Convention Center |
| Mt Vernon Sq 7th St-Convention Center (E01) | Southbound → Gallery Pl-Chinatown | Northbound → Shaw-Howard U |
| Shaw-Howard U (E02) | Southbound → Mt Vernon Sq 7th St-Convention Center | Northbound → U Street/African-Amer Civil War Memorial/Cardozo |
| U Street/African-Amer Civil War Memorial/Cardozo (E03) | Southbound → Shaw-Howard U | Northbound → Columbia Heights |
| Columbia Heights (E04) | Southbound → U Street/African-Amer Civil War Memorial/Cardozo | Northbound → Georgia Ave-Petworth |
| Georgia Ave-Petworth (E05) | Southbound → Columbia Heights | Northbound → Fort Totten |
| Fort Totten (E06) | Southbound → Georgia Ave-Petworth | Northbound → West Hyattsville |
| West Hyattsville (E07) | Southbound → Fort Totten | Northbound → Hyattsville Crossing |
| Hyattsville Crossing (E08) | Southbound → West Hyattsville | Northbound → College Park-U of Md |
| College Park-U of Md (E09) | Southbound → Hyattsville Crossing | Northbound → Greenbelt |
| Greenbelt (E10) | Southbound → College Park-U of Md | — |

### Orange

| Station | Toward previous stop | Toward next stop |
| --- | --- | --- |
| Vienna/Fairfax-GMU (K08) | — | Eastbound → Dunn Loring-Merrifield |
| Dunn Loring-Merrifield (K07) | Westbound → Vienna/Fairfax-GMU | Eastbound → West Falls Church |
| West Falls Church (K06) | Westbound → Dunn Loring-Merrifield | Eastbound → East Falls Church |
| East Falls Church (K05) | Westbound → West Falls Church | Eastbound → Ballston-MU |
| Ballston-MU (K04) | Westbound → East Falls Church | Eastbound → Virginia Square-GMU |
| Virginia Square-GMU (K03) | Westbound → Ballston-MU | Eastbound → Clarendon |
| Clarendon (K02) | Westbound → Virginia Square-GMU | Eastbound → Court House |
| Court House (K01) | Westbound → Clarendon | Eastbound → Rosslyn |
| Rosslyn (C05) | Westbound → Court House | Eastbound → Foggy Bottom-GWU |
| Foggy Bottom-GWU (C04) | Westbound → Rosslyn | Eastbound → Farragut West |
| Farragut West (C03) | Westbound → Foggy Bottom-GWU | Eastbound → McPherson Square |
| McPherson Square (C02) | Westbound → Farragut West | Eastbound → Metro Center |
| Metro Center (C01) | Westbound → McPherson Square | Eastbound → Federal Triangle |
| Federal Triangle (D01) | Westbound → Metro Center | Eastbound → Smithsonian |
| Smithsonian (D02) | Westbound → Federal Triangle | Eastbound → L'Enfant Plaza |
| L'Enfant Plaza (D03) | Westbound → Smithsonian | Eastbound → Federal Center SW |
| Federal Center SW (D04) | Westbound → L'Enfant Plaza | Eastbound → Capitol South |
| Capitol South (D05) | Westbound → Federal Center SW | Eastbound → Eastern Market |
| Eastern Market (D06) | Westbound → Capitol South | Eastbound → Potomac Ave |
| Potomac Ave (D07) | Westbound → Eastern Market | Eastbound → Stadium-Armory |
| Stadium-Armory (D08) | Westbound → Potomac Ave | Eastbound → Minnesota Ave |
| Minnesota Ave (D09) | Westbound → Stadium-Armory | Eastbound → Deanwood |
| Deanwood (D10) | Westbound → Minnesota Ave | Eastbound → Cheverly |
| Cheverly (D11) | Westbound → Deanwood | Eastbound → Landover |
| Landover (D12) | Westbound → Cheverly | Eastbound → New Carrollton |
| New Carrollton (D13) | Westbound → Landover | — |

### Red

| Station | Toward previous stop | Toward next stop |
| --- | --- | --- |
| Shady Grove (A15) | — | Southbound → Rockville |
| Rockville (A14) | Northbound → Shady Grove | Southbound → Twinbrook |
| Twinbrook (A13) | Northbound → Rockville | Southbound → North Bethesda |
| North Bethesda (A12) | Northbound → Twinbrook | Southbound → Grosvenor-Strathmore |
| Grosvenor-Strathmore (A11) | Northbound → North Bethesda | Southbound → Medical Center |
| Medical Center (A10) | Northbound → Grosvenor-Strathmore | Southbound → Bethesda |
| Bethesda (A09) | Northbound → Medical Center | Southbound → Friendship Heights |
| Friendship Heights (A08) | Northbound → Bethesda | Southbound → Tenleytown-AU |
| Tenleytown-AU (A07) | Northbound → Friendship Heights | Southbound → Van Ness-UDC |
| Van Ness-UDC (A06) | Northbound → Tenleytown-AU | Southbound → Cleveland Park |
| Cleveland Park (A05) | Northbound → Van Ness-UDC | Southbound → Woodley Park-Zoo/Adams Morgan |
| Woodley Park-Zoo/Adams Morgan (A04) | Northbound → Cleveland Park | Southbound → Dupont Circle |
| Dupont Circle (A03) | Northbound → Woodley Park-Zoo/Adams Morgan | Southbound → Farragut North |
| Farragut North (A02) | Northbound → Dupont Circle | Southbound → Metro Center |
| Metro Center (A01) | Westbound → Farragut North | Eastbound → Gallery Pl-Chinatown |
| Gallery Pl-Chinatown (B01) | Westbound → Metro Center | Eastbound → Judiciary Square |
| Judiciary Square (B02) | Westbound → Gallery Pl-Chinatown | Eastbound → Union Station |
| Union Station (B03) | Southbound → Judiciary Square | Northbound → NoMa-Gallaudet U |
| NoMa-Gallaudet U (B35) | Southbound → Union Station | Northbound → Rhode Island Ave-Brentwood |
| Rhode Island Ave-Brentwood (B04) | Southbound → NoMa-Gallaudet U | Northbound → Brookland-CUA |
| Brookland-CUA (B05) | Southbound → Rhode Island Ave-Brentwood | Northbound → Fort Totten |
| Fort Totten (B06) | Southbound → Brookland-CUA | Northbound → Takoma |
| Takoma (B07) | Southbound → Fort Totten | Northbound → Silver Spring |
| Silver Spring (B08) | Southbound → Takoma | Northbound → Forest Glen |
| Forest Glen (B09) | Southbound → Silver Spring | Northbound → Wheaton |
| Wheaton (B10) | Southbound → Forest Glen | Northbound → Glenmont |
| Glenmont (B11) | Southbound → Wheaton | — |

### Silver

| Station | Toward previous stop | Toward next stop |
| --- | --- | --- |
| Ashburn (N12) | — | Eastbound → Loudoun Gateway |
| Loudoun Gateway (N11) | Westbound → Ashburn | Eastbound → Washington Dulles International Airport |
| Washington Dulles International Airport (N10) | Westbound → Loudoun Gateway | Eastbound → Innovation Center |
| Innovation Center (N09) | Westbound → Washington Dulles International Airport | Eastbound → Herndon |
| Herndon (N08) | Westbound → Innovation Center | Eastbound → Reston Town Center |
| Reston Town Center (N07) | Westbound → Herndon | Eastbound → Wiehle-Reston East |
| Wiehle-Reston East (N06) | Westbound → Reston Town Center | Eastbound → Spring Hill |
| Spring Hill (N04) | Westbound → Wiehle-Reston East | Eastbound → Greensboro |
| Greensboro (N03) | Westbound → Spring Hill | Eastbound → Tysons |
| Tysons (N02) | Westbound → Greensboro | Eastbound → McLean |
| McLean (N01) | Westbound → Tysons | Eastbound → East Falls Church |
| East Falls Church (K05) | Westbound → McLean | Eastbound → Ballston-MU |
| Ballston-MU (K04) | Westbound → East Falls Church | Eastbound → Virginia Square-GMU |
| Virginia Square-GMU (K03) | Westbound → Ballston-MU | Eastbound → Clarendon |
| Clarendon (K02) | Westbound → Virginia Square-GMU | Eastbound → Court House |
| Court House (K01) | Westbound → Clarendon | Eastbound → Rosslyn |
| Rosslyn (C05) | Westbound → Court House | Eastbound → Foggy Bottom-GWU |
| Foggy Bottom-GWU (C04) | Westbound → Rosslyn | Eastbound → Farragut West |
| Farragut West (C03) | Westbound → Foggy Bottom-GWU | Eastbound → McPherson Square |
| McPherson Square (C02) | Westbound → Farragut West | Eastbound → Metro Center |
| Metro Center (C01) | Westbound → McPherson Square | Eastbound → Federal Triangle |
| Federal Triangle (D01) | Westbound → Metro Center | Eastbound → Smithsonian |
| Smithsonian (D02) | Westbound → Federal Triangle | Eastbound → L'Enfant Plaza |
| L'Enfant Plaza (D03) | Westbound → Smithsonian | Eastbound → Federal Center SW |
| Federal Center SW (D04) | Westbound → L'Enfant Plaza | Eastbound → Capitol South |
| Capitol South (D05) | Westbound → Federal Center SW | Eastbound → Eastern Market |
| Eastern Market (D06) | Westbound → Capitol South | Eastbound → Potomac Ave |
| Potomac Ave (D07) | Westbound → Eastern Market | Eastbound → Stadium-Armory |
| Stadium-Armory (D08) | Westbound → Potomac Ave | Eastbound → Benning Road |
| Benning Road (G01) | Westbound → Stadium-Armory | Eastbound → Capitol Heights |
| Capitol Heights (G02) | Westbound → Benning Road | Eastbound → Addison Road-Seat Pleasant |
| Addison Road-Seat Pleasant (G03) | Westbound → Capitol Heights | Eastbound → Morgan Boulevard |
| Morgan Boulevard (G04) | Westbound → Addison Road-Seat Pleasant | Eastbound → Downtown Largo |
| Downtown Largo (G05) | Westbound → Morgan Boulevard | — |

### Yellow

| Station | Toward previous stop | Toward next stop |
| --- | --- | --- |
| Huntington (C15) | — | Northbound → Eisenhower Avenue |
| Eisenhower Avenue (C14) | Southbound → Huntington | Northbound → King St-Old Town |
| King St-Old Town (C13) | Southbound → Eisenhower Avenue | Northbound → Braddock Road |
| Braddock Road (C12) | Southbound → King St-Old Town | Northbound → Potomac Yard |
| Potomac Yard (C11) | Southbound → Braddock Road | Northbound → Ronald Reagan Washington National Airport |
| Ronald Reagan Washington National Airport (C10) | Southbound → Potomac Yard | Northbound → Crystal City |
| Crystal City (C09) | Southbound → Ronald Reagan Washington National Airport | Northbound → Pentagon City |
| Pentagon City (C08) | Southbound → Crystal City | Northbound → Pentagon |
| Pentagon (C07) | Southbound → Pentagon City | Northbound → L'Enfant Plaza |
| L'Enfant Plaza (F03) | Southbound → Pentagon | Northbound → Archives-Navy Memorial-Penn Quarter |
| Archives-Navy Memorial-Penn Quarter (F02) | Southbound → L'Enfant Plaza | Northbound → Gallery Pl-Chinatown |
| Gallery Pl-Chinatown (F01) | Southbound → Archives-Navy Memorial-Penn Quarter | Northbound → Mt Vernon Sq 7th St-Convention Center |
| Mt Vernon Sq 7th St-Convention Center (E01) | Southbound → Gallery Pl-Chinatown | Northbound → Shaw-Howard U |
| Shaw-Howard U (E02) | Southbound → Mt Vernon Sq 7th St-Convention Center | Northbound → U Street/African-Amer Civil War Memorial/Cardozo |
| U Street/African-Amer Civil War Memorial/Cardozo (E03) | Southbound → Shaw-Howard U | Northbound → Columbia Heights |
| Columbia Heights (E04) | Southbound → U Street/African-Amer Civil War Memorial/Cardozo | Northbound → Georgia Ave-Petworth |
| Georgia Ave-Petworth (E05) | Southbound → Columbia Heights | Northbound → Fort Totten |
| Fort Totten (E06) | Southbound → Georgia Ave-Petworth | Northbound → West Hyattsville |
| West Hyattsville (E07) | Southbound → Fort Totten | Northbound → Hyattsville Crossing |
| Hyattsville Crossing (E08) | Southbound → West Hyattsville | Northbound → College Park-U of Md |
| College Park-U of Md (E09) | Southbound → Hyattsville Crossing | Northbound → Greenbelt |
| Greenbelt (E10) | Southbound → College Park-U of Md | — |
