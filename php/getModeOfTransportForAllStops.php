<?php

/**
 * Trafiklab GTFS Examples
 * ================================================
 *
 * This set of scripts is meant to give you an example on how you can use GTFS, and what you can do with it.
 * This specific script will give a list of all modes of transport (bus, train, ...) per stop, and print them out
 * to the command line.
 *
 * Usage
 * -------------------
 * Run `composer install` first to install any dependencies. For more information, see https://getcomposer.org/ .
 *
 * Run this file directly from the command line by invoking `php getModeOfTransportForAllStops.php <your-gtfs-file>`
 * <your-gtfs-file> should be the path to the GTFS file on which you want to run the script.
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

// Used for logging later on.
const BACKSPACE = "\x08";

// If composer isn't installed, we show an error and quit
if (!file_exists(__DIR__ . "/vendor/autoload.php")) {
    die("You need to run `composer install` before running this script!");
}

require_once __DIR__ . "/vendor/autoload.php";


// Read the first argument, which should be the path to a GTFS file
// Argv is a special variable: https://www.php.net/manual/en/reserved.variables.argv.php
$gtfsFilePath = $argv[1];

// Use the GtfsArchive class from the Trafiklab GTFS SDK to read the GTFS file.
// See https://github.com/trafiklab/gtfs-php-sdk.
$archive = GtfsArchive::createFromPath($gtfsFilePath);

// Read the entire stops file
$allGtfsStops = $archive->getStopsFile()->getStops();

// We will store our results in a multi-dimensional array:
// For every stop-id we hold a nested array which contains all transport modes.
// Create an empty array to hold our results.
$transportModesPerStop = [];

echo "Looping over " . count($allGtfsStops) . " stops" . PHP_EOL;

foreach ($allGtfsStops as $gtfsStop) {
    // Get all StopTimes, defined in stop_times.txt, where the stop_id equals this stop.
    $stopId = $gtfsStop->getStopId();
    $stopTimesForStop = $archive->getStopTimesFile()->getStopTimesForStop($stopId);
    foreach ($stopTimesForStop as $stopTime) {
        // get the trip_id for this stop_time.
        $tripIdForStopTime = $stopTime->getTripId();
        // get the route_id for the trip
        $routeIdForStopTime = $archive->getTripsFile()->getTrip($tripIdForStopTime)->getRouteId();
        // get the route
        $routeForStopTime = $archive->getRoutesFile()->getRoute($routeIdForStopTime);
        // get the transport mode from the route
        $routeType = $routeForStopTime->getRouteType();

        if (!key_exists($stopId, $transportModesPerStop)) {
            // If this stop doesn't occur in our results array yet, initialize it.
            $transportModesPerStop[$stopId] = [];
        }
        // Ensure we store each type of traffic only once
        if (!in_array($routeType, $transportModesPerStop[$stopId])) {
            $transportModesPerStop[$stopId][] = $routeType;
        }
    }
    echo ".";
}
echo PHP_EOL;

// Cleanup
$archive->deleteUncompressedFiles();

foreach ($transportModesPerStop as $stopId => $transportModesArray) {
    echo "At stop " . $stopId . " the following types of transport are available: " .
        join(',', $transportModesArray) . PHP_EOL;
}