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
 * Run this file directly from the command line by invoking `php getModeOfTransportForAllStops.php <your-gtfs-file>
 * <whitelisted-operator>`
 * <your-gtfs-file> should be the path to the GTFS file on which you want to run the script.
 * <whitelisted-operator> is the GTFS agency id for the operator which you're interested in.
 *
 * Example: php getModeOfTransportForAllStopsByOperator.php "sweden-gtfs.zip" 276
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
use Trafiklab\Gtfs\Model\GtfsRouteType;

// If composer isn't installed, we show an error and quit
if (!file_exists(__DIR__ . "/vendor/autoload.php")) {
    die("You need to run `composer install` before running this script!");
}

require_once __DIR__ . "/vendor/autoload.php";


// Read the first argument, which should be the path to a GTFS file
// Argv is a special variable: https://www.php.net/manual/en/reserved.variables.argv.php
$gtfsFilePath = $argv[1];
// The operator to print out
$whitelistedOperator = $argv[2];

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
$stopsPerTransportMode = [];

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

        $simpleTransportMode = GtfsRouteType::mapExtendedRouteTypeToBasicRouteType($routeType);

        if (!key_exists($simpleTransportMode, $stopsPerTransportMode)) {
            // Initialize empty
            $stopsPerTransportMode[$simpleTransportMode] = [];
        }
        $stopsPerTransportMode[$simpleTransportMode][$stopId] = $gtfsStop;
    }
    echo ".";
    if ($i++ % ($stopCount / 20) == 0) {
        // Print out progress in %.
        echo round((100 * $i) / $stopCount, 0);
    }
}
// Cleanup
$archive->deleteUncompressedFiles();

echo PHP_EOL . PHP_EOL . PHP_EOL;
echo "Stops for operator " . $whitelistedOperator . " per transport mode:" . PHP_EOL . PHP_EOL;
foreach ($stopsPerTransportMode as $transportModeCode => $stops) {
    switch ($transportModeCode) {
        case 0:
            echo "TRAM";
            break;
        case 1:
            echo "METRO";
            break;
        case 2:
            echo "TRAIN";
            break;
        case 3:
            echo "BUS";
            break;
        case 4:
            echo "FERRY";
            break;
        default:
            // Skip this unknown entry in the for loop
            continue 2;
    }
    echo PHP_EOL . "===================" . PHP_EOL;

    foreach ($stops as $id => $stop) {
        echo $id . ", " . $stop->getStopName() . PHP_EOL;
    }

    echo PHP_EOL;
}