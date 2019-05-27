<?php

/**
 * Trafiklab GTFS Examples
 * ================================================
 *
 * This set of scripts is meant to give you an example on how you can use GTFS, and what you can do with it.
 * This specific script will give a list of all stops for a given agency_id, and sort them by the average number of
 * stops per day. The average number of stops per day is a good indicator for the size of the stop.
 *
 * Usage
 * -------------------
 * Run `composer install` first to install any dependencies. For more information, see https://getcomposer.org/ .
 *
 * Run this file directly from the command line by invoking
 * `php getAllstopsForOperatorOrderedBySize.php <your-gtfs-file> <whitelisted-operator>`
 *
 * <your-gtfs-file> should be the path to the GTFS file on which you want to run the script.
 * <whitelisted-operator> is the GTFS agency id for the operator which you're interested in.
 *
 * Example: php getAllstopsForOperatorOrderedBySize.php "sweden-gtfs.zip" 276
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

$stopCount = count($allGtfsStops);
echo $stopCount . " stops will be processed." . PHP_EOL;

// This array will hold our results
$averageStopsPerDayPerStop = [];

// This array will keep track of all the days on which at least one trip is serviced
$handledDays = [];

// This array will keep track of all the days on which a certain trip is served
$serviceIdForTrip = [];

// This array will keep track of which trips are serving which stops
$tripsPerStop = [];
echo "Processing trips and calendar dates...";
$allTrips = $archive->getTripsFile()->getTrips();

$serviceDates = [];
foreach ($archive->getCalendarDatesFile()->getCalendarDates() as $calendarDate) {
    $dateStr = $calendarDate->getDate()->format("Ymd");
    if (!key_exists($calendarDate->getServiceId(), $serviceDates)) {
        $serviceDates[$calendarDate->getServiceId()] = [];
    }
    $serviceDates[$calendarDate->getServiceId()][] = $dateStr;
    // register this day as in service
    $handledDays[$dateStr] = 1;
}

foreach ($allTrips as $trip) {
    $serviceIdForTrip[$trip->getTripId()] = $trip->getServiceId();
}

echo PHP_EOL;
$routeForTripId = [];
echo "Processed trips, now starting with stops...";
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

        if (!key_exists($stopId, $tripsPerStop)) {
            $tripsPerStop[$stopId] = [];
        }

        if (!key_exists($tripIdForStopTime, $tripsPerStop[$stopId])) {
            $tripsPerStop[$stopId][$tripIdForStopTime] = 0;
        }

        // Count the number of times a trip stops at a certain stop
        $tripsPerStop[$stopId][$tripIdForStopTime]++;
    }

}
echo PHP_EOL . PHP_EOL;
// Cleanup GTFS data which is no longer needed
$archive->deleteUncompressedFiles();

$totalDaysSeen = count($handledDays);
foreach ($tripsPerStop as $stopId => $trips) {
    $servingsForThisStop = 0;
    foreach ($trips as $tripId => $timesServiced) {
        $servingsForThisStop += $timesServiced * count($serviceDates[$serviceIdForTrip[$tripId]]);
    }
    $averageStopsPerDayPerStop[$stopId] = $servingsForThisStop / $totalDaysSeen;
}

asort($averageStopsPerDayPerStop);

foreach ($averageStopsPerDayPerStop as $stopId => $averageStops) {
    echo $stopId . ": " . round($averageStops, 2) . PHP_EOL;
}

