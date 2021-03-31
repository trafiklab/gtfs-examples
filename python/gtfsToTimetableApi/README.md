# GTFS Timetable API demo
**This example shows how to use GTFS, GTFS-RT TripUpdates (delays), GTFS-RT VehiclePositions (GPS positions), GTFS-RT VehiclePositions (Occupancy data).**


This project is a little tech demo, showing how GTFS and GTFS-RT data can be used to create a timetable API. The
timetable API shows a list of realtime departures from a given stop, along with the current position and occupancy grade
of the vehicle if it's available. No pre-processing or data conversion is needed.

The demo consists of a module that builds timetables from scheduled GTFS data (`GtfsTimeTable.py`) and a module that
fetches and parses realtime data (`RealtimeDataFetcher.py`). A helper class

The purpose of this demo is to show how GTFS and GTFS-RT are related, and how compact GTFS files can be "inflated" to
timetable data. This project is not meant to be used in a production environment, but it can either inspire and help
while building a production-ready solution. It can be tweaked to be production-ready.

## Installation

- Make sure you have python 3 and pip on your device. Make sure you are actually working in python 3 if you have
  multiple versions installed.
- **Optional:** If you want to, and know how to, you can run this project in a virtual environment.
- Clone or download the python files, the install the requirements using `pip install -r requirements.txt`

## Running

- Run the `TimeTableApi` flask app to start a
  webserver: `python3 TimeTableApi.py --gtfs="<URL to GTFS.zip>" --vehicle-positions="<URL to vehiclepositions.pb>" --trip-updates="<URL to tripupdates.pb>"`
- Or use the GtfsTimeTable module direct from the command
  line: `python3 GtfsTimeTable.py --gtfs="<URL to GTFS.zip>" --vehicle-positions="<URL to vehiclepositions.pb>" --trip-updates="<URL to tripupdates.pb>" --stop-id="<id of stop to get departures for>"`

Note: All GTFS data is cached:

- A new GTFS file is only fetched once per day
- New tripupdates data is only fetched on demand, no more than once per minute
- New vehiclepositions data is only fetched on demand, no more than once per 15s

## Webserver endpoints

The Flask webapp contains two endpoints:

- The `/stops` endpoint lists all stops which you can search for
- The `/departures/<stop-id>` endpoint shows the departures from the past 10 minutes to the next 2 hours for the given
  stop.

**Important! ** If you want to reach the development server from another machine in your network, you need to edit the
last line in `TimeTableApi.py` from `app.run()` to `app.run(host="0.0.0.0")`

A response from the `/departures/<stop-id>` endpoint contains all the platforms that were searched, and all the
departures from those platforms. It looks like this:

```json
{
  "stops": [
    {
      "id": "9021012081007000",
      "name": "Lund Katedralskolan",
      "platform": "",
      "latitude": "55.700294",
      "longitude": "13.191750"
    },
    {
      "id": "9022012081007002",
      "name": "Lund Katedralskolan",
      "platform": "B",
      "latitude": "55.700322",
      "longitude": "13.191780"
    },
    {
      "id": "9022012081007003",
      "name": "Lund Katedralskolan",
      "platform": "C",
      "latitude": "55.700210",
      "longitude": "13.191613"
    },
    {
      "id": "9022012081007001",
      "name": "Lund Katedralskolan",
      "platform": "A",
      "latitude": "55.700924",
      "longitude": "13.192186"
    }
  ],
  "departures": [
    {
      "direction": "Klostergården",
      "scheduled_departure_time": "14:19:38",
      "realtime_departure_time": "14:19:25",
      "stop": {
        "id": "9022012081007003",
        "name": "Lund Katedralskolan",
        "platform": "C",
        "latitude": "55.700210",
        "longitude": "13.191613"
      },
      "type": "BUS",
      "route_long": "Klostergården - Botulfsplatsen - Östra Torn",
      "route_short": "7",
      "delay": -13,
      "position": {
        "latitude": 55.694007873535156,
        "longitude": 13.174702644348145,
        "bearing": 46,
        "speed": 37.08000068664551
      },
      "occupancy": "MANY_SEATS_AVAILABLE"
    }
  ]
```

## Performance

Time to generate a response:

- Cached on a modern laptop: 5ms - 2s, 740MB memory usage
- Cached on a Raspberry pi 4: 20ms - 3.5s, 670MB memory usage
- Uncached on a modern laptop: 4s, 80MB memory usage
- Uncached on a Raspberry pi 4: 10-12s, 80MB memory usage

Some notes:

- Realtime data is fetched on-demand. This causes the high spikes seen in the metrics above. Periodically updating
  realtime data on a separate thread will remove this spikes, and result in a consistent response time under 25ms

- The API can be run with an `--uncached` parameter. This will reduce memory usage, but increases computing time. It is
  only recommended when you will make no more than 1 request, or on devices that have insufficient memory for caching.
  
