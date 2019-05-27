# Trafiklab GTFS Examples in PHP

Here you can find scripts written in PHP, as an example on how you can use GTFS, and what's possible with it. 
All scripts are invoked from the commandline and take the path to a zipped PHP file as first parameter. Further 
parameters are explained in the file header.

These examples make use of the Trafiklab GTFS SDK, which can be found at https://github.com/trafiklab/gtfs-php-sdk.

## Contents
- getAllStopsForoperatorOrderedBySize: list the stops for a certain operator, ordered by the average number of vehicles 
halting there per day
- getModeOfTransportForAllStops: give the modes of transport for every stop in a GTFS stops file.
- getModeOfTransportForAllStopsByOperator: give all stops for a certain operator per transport mode.
 This results in a list of all train stations for that operator, all bus stops, ...
## Contributing

We accept pull requests, but please create an issue first in order to discuss the addition or fix.
If you would like to see a new feature added, you can also create a feature request by creating an issue.

## Help

If you're stuck with a question, feel free to ask help through the Issue tracker.
- Need help with API keys? Please read [www.trafiklab.se/api-nycklar](https://www.trafiklab.se/api-nycklar) first.
- Do you want to check the current systems status? Service disruptions
 are published on the [Trafiklab homepage](https://www.trafiklab.se/)