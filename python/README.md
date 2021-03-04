# Trafiklab GTFS Examples in Python

Here you can find scripts written in Python, as an example on how you can use GTFS, and what's possible with it. Some
more complex scripts are located in their own subfolder with their own readme file. Scripts contain additional
information in the header and comments.

**Important:** All scripts are developed for Python 3.x. 

## Contents

- gtfsToTimetableApi: Get a list of departures from a stop, including realtime delays and vehicle positions. Can be used
  from the command line or as an JSON HTTP API. No pre-processing is needed, and you don't need a powerful computer
  either. You can have an API up and running on a raspberry pi in a matter of seconds.
- stopsMunicipalityCalculator: Determines the municipality of each stop in a GTFS stops.txt file based on the
  coordinates.
- `stops_calculate_average_departures.py`: This script calculates the average number of departures per day for each
  stop. Perfect if you want to implement an autocomplete where the most popular stations show up first.

## Contributing

We accept pull requests, but please create an issue first in order to discuss the addition or fix. If you would like to
see a new feature added, you can also create a feature request by creating an issue.

## Help

If you're stuck with a question, feel free to ask help through the Issue tracker.

- Need help with API keys? Please read [www.trafiklab.se/api-nycklar](https://www.trafiklab.se/api-nycklar) first.
- Do you want to check the current systems status? Service disruptions are published on
  the [Trafiklab homepage](https://www.trafiklab.se/)