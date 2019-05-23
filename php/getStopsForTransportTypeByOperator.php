<?php

/**
 * Trafiklab GTFS Examples
 * ================================================
 *
 * This set of scripts is meant to give you an example on how you can use GTFS, and what you can do with it.
 * This specific script will give a list of all stops for a given agency_id and route_type, and print them out
 * to the command line.
 *
 * Usage
 * -------------------
 * Run `composer install` first to install any dependencies. For more information, see https://getcomposer.org/ .
 *
 * Run this file directly from the command line by invoking `php getModeOfTransportPerStop.php <your-gtfs-file>
 * <whitelisted-operator> <whitelisted-transport-modes-csv>`
 * <your-gtfs-file> should be the path to the GTFS file on which you want to run the script.
 * <whitelisted-operator> is the GTFS agency id for the operator which you're interested in.
 * <whitelisted-transport-modes-csv> is one or more route-types which you are interested in, separated by ,
 *
 * Example: php getStopsForTransportTypeByOperator.php "sweden-gtfs.zip" 276 3,200,201,202,203,204,205,206,207,208,209,
 * 700,701,702,703,704,705,706,707,708,709,710,711,712,713,714,715,716,717
 *
 * License
 * -------------------
 * These examples are available under a CC-0 license, have fun with it!
 *
 * Github
 * -------------------
 * More examples can be found at https://github.com/trafiklab/gtfs-examples
 *
 */

use Trafiklab\Gtfs\Model\GtfsArchive;

// If composer isn't installed, we show an error and quit
if (!file_exists(__DIR__ . "/vendor/autoload.php")) {
    die("You need to run `composer install` before running this script!");
}

require_once __DIR__ . "/vendor/autoload.php";


// Read the first argument, which should be the path to a GTFS file
// Argv is a special variable: https://www.php.net/manual/en/reserved.variables.argv.php
$gtfsFilePath = $argv[1];
$whitelistedOperator = $argv[2];
// Read the whitelisted transport modes into a variable
$whitelistedTransportModes = $argv[3];
// Convert to an array if it is a list of values separated by a comma
if (strpos($whitelistedTransportModes, ',') !== false) {
    $whitelistedTransportModes = explode(',', $whitelistedTransportModes);
} else {
    // convert a single value to an array so this whitelist is always an array
    $whitelistedTransportModes = [$whitelistedTransportModes];
}

// Use the GtfsArchive class from the Trafiklab GTFS SDK to read the GTFS file.
// See https://github.com/trafiklab/gtfs-php-sdk.
$archive = GtfsArchive::createFromPath($gtfsFilePath);

echo "Reading stops.txt..." . PHP_EOL;
// Read the entire stops file
$allGtfsStops = $archive->getStopsFile()->getStops();

echo "Reading stop_times.txt..." . PHP_EOL;
// Load data into cache with a nice loading message.
$archive->getStopTimesFile();

// We will store our results in a multi-dimensional array:
// For every stop-id we hold a nested array which contains all transport modes.
// Create an empty array to hold our results.
$transportModesPerStop = [];

$stopCount = count($allGtfsStops);
echo "Looping over " . $stopCount . " stops" . PHP_EOL;

// Additional caching to ensure good performance when handling with millions of stop times
$routeForTripId = [];

$i = 0;
foreach ($allGtfsStops as $gtfsStop) {
    // Get all StopTimes, defined in stop_times.txt, where the stop_id equals this stop.
    $stopId = $gtfsStop->getStopId();
    $stopTimesForStop = $archive->getStopTimesFile()->getStopTimesForStop($stopId);
    foreach ($stopTimesForStop as $stopTime) {
        // get the trip_id for this stop_time.
        $tripIdForStopTime = $stopTime->getTripId();

        // If not cached, get the route in the cache
        if (!key_exists($tripIdForStopTime, $routeForTripId)) {
            // get the route_id for the trip
            $routeIdForStopTime = $archive->getTripsFile()->getTrip($tripIdForStopTime)->getRouteId();
            // get the route
            $routeForTripId[$tripIdForStopTime] = $archive->getRoutesFile()->getRoute($routeIdForStopTime);
        }
        // Get the route from cache
        $routeForStopTime = $routeForTripId[$tripIdForStopTime];

        // Filter on operator. If not whitelisted, ignore
        if ($routeForStopTime->getAgencyId() != $whitelistedOperator) {
            continue;
        }

        // get the transport mode from the route
        $routeType = $routeForStopTime->getRouteType();

        // Ensure we store each type of traffic only once
        if (!key_exists($stopId, $transportModesPerStop) || !in_array($routeType, $transportModesPerStop[$stopId])) {
            if (!key_exists($stopId, $transportModesPerStop)) {
                // If this stop doesn't occur in our results array yet, initialize it.
                $transportModesPerStop[$stopId] = [];
            }
            $transportModesPerStop[$stopId][] = $routeType;
        }
    }
    echo ".";
    if ($i++ % ($stopCount / 20) == 0) {
        echo round((100 * $i) / $stopCount, 0);
    }
}
echo PHP_EOL;

// Cleanup
$archive->deleteUncompressedFiles();

foreach ($transportModesPerStop as $stopId => $transportModesArray) {
    // Filter on whitelist. If there is at least one transport mode on the whitelist that's passing at this stop,
    // print the stop to the console
    if (count(array_intersect($whitelistedTransportModes, $transportModesArray)) > 0) {
        echo $stopId . PHP_EOL;
    }
}