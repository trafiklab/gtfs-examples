<?php

/**
 * Trafiklab GTFS Examples
 * ================================================
 *
 * This set of scripts is meant to give you an example on how you can use GTFS, and what you can do with it.
 * This specific script will autocomplete a station name, using 6 variants of simple autocomplete algorithms. The goal
 * of this example is to show how to create autocomplete based on a GTFS stops.txt file, and how different parameters
 * and sorting can affect the results.
 *
 * Usage
 * -------------------
 * Run `composer install` first to install any dependencies. For more information, see https://getcomposer.org/ .
 *
 * Run this file directly from the command line by invoking
 * `php autocompleteStopNames.php <your-gtfs-file> <query>`
 *
 * <your-gtfs-file> should be the path to the GTFS file on which you want to run the script.
 * <query> is the (part of a) stop name to search for.
 *
 * Example: php autocompleteStopNames.php "sweden-gtfs.zip" stoc
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

use Trafiklab\Gtfs\Model\Entities\Stop;
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
$query = $argv[2];

// coordinates for 2 cities
$cities = [
    'Stockholm' => [59.3293, 18.0686],
    'Göteborg' => [57.7089, 11.9746]
];

// Use the GtfsArchive class from the Trafiklab GTFS SDK to read the GTFS file.
// See https://github.com/trafiklab/gtfs-php-sdk.
$archive = GtfsArchive::createFromPath($gtfsFilePath);

// Read the entire stops file
$allGtfsStops = $archive->getStopsFile();

$startOfNameSearch = [];
$nameContainsSearch = [];
$startOfNameSearchOrderByDistance = [];
$nameContainsSearchOrderByDistance = [];
$startOfNameSearchInArea = [];
$nameContainsSearchInArea = [];

foreach ($cities as $city => $coordinates) {
    $startOfNameSearch[$city] = [];
    $nameContainsSearch[$city] = [];
    $startOfNameSearchOrderByDistance[$city] = [];
    $nameContainsSearchOrderByDistance[$city] = [];
    $startOfNameSearchInArea[$city] = [];
    $nameContainsSearchInArea[$city] = [];

    foreach ($allGtfsStops->getStops() as $gtfsStop) {
        startOfNameSearch($startOfNameSearch[$city], $query, $gtfsStop, $coordinates);
        nameContainsSearch($nameContainsSearch[$city], $query, $gtfsStop, $coordinates);
        startOfNameSearchOrderByDistance($startOfNameSearchOrderByDistance[$city], $query, $gtfsStop, $coordinates);
        nameContainsSearchOrderByDistance($nameContainsSearchOrderByDistance[$city], $query, $gtfsStop, $coordinates);
        startOfNameSearchInArea($startOfNameSearchInArea[$city], $query, $gtfsStop, $coordinates);
        nameContainsSearchInArea($nameContainsSearchInArea[$city], $query, $gtfsStop, $coordinates);
    }
}

foreach ($cities as $city => $coordinates) {
    postProcessAlphabetical($startOfNameSearch[$city]);
    postProcessAlphabetical($nameContainsSearch[$city]);
    postProcessWeighted($startOfNameSearchOrderByDistance[$city]);
    postProcessWeighted($nameContainsSearchOrderByDistance[$city]);
    postProcessAlphabetical($startOfNameSearchInArea[$city]);
    postProcessAlphabetical($nameContainsSearchInArea[$city]);

    echo "Search results for $query for a user in $city:" . PHP_EOL . "================================" . PHP_EOL;
    echo "Search in start of name, alphabetical:" . PHP_EOL;
    printResult($startOfNameSearch[$city]);
    echo "Search in start of name, in 30km radius:" . PHP_EOL;
    printResult($startOfNameSearchInArea[$city]);
    echo "Search in start of name, ordered by distance:" . PHP_EOL;
    printResult($startOfNameSearchOrderByDistance[$city]);
    echo "Search anywhere in name, alphabetical:" . PHP_EOL;
    printResult($nameContainsSearch[$city]);
    echo "Search anywhere in name, in 30km radius:" . PHP_EOL;
    printResult($nameContainsSearchInArea[$city]);
    echo "Search anywhere in name, ordered by distance:" . PHP_EOL;
    printResult($nameContainsSearchOrderByDistance[$city]);
}


echo PHP_EOL . PHP_EOL;
// Cleanup GTFS data which is no longer needed
$archive->deleteUncompressedFiles();

function startOfNameSearch(array &$results, string $query, Stop $gtfsStop, array $location): void
{
    if (startsWith($gtfsStop->getStopName(), $query)) {
        $results[] = $gtfsStop->getStopName();
    }
}

function nameContainsSearch(array &$results, string $query, Stop $gtfsStop, array $location): void
{
    if (contains($gtfsStop->getStopName(), $query)) {
        $results[] = $gtfsStop->getStopName();
    }
}

function startOfNameSearchOrderByDistance(array &$results, string $query, Stop $gtfsStop, array $location): void
{
    if (startsWith($gtfsStop->getStopName(), $query)) {
        $distance = dist($location[0], $location[1], $gtfsStop->getStopLat(), $gtfsStop->getStopLon());
        $results[$gtfsStop->getStopName()] = $distance;
    }
}

function nameContainsSearchOrderByDistance(array &$results, string $query, Stop $gtfsStop, array $location): void
{
    if (contains($gtfsStop->getStopName(), $query)) {
        $distance = dist($location[0], $location[1], $gtfsStop->getStopLat(), $gtfsStop->getStopLon());
        $results[$gtfsStop->getStopName()] = $distance;
    }
}

function startOfNameSearchInArea(array &$results, string $query, Stop $gtfsStop, array $location): void
{
    $distance = dist($location[0], $location[1], $gtfsStop->getStopLat(), $gtfsStop->getStopLon());
    if (startsWith($gtfsStop->getStopName(), $query) && $distance < 30000) {
        $results[] = $gtfsStop->getStopName();
    }
}

function nameContainsSearchInArea(array &$results, string $query, Stop $gtfsStop, array $location): void
{
    $distance = dist($location[0], $location[1], $gtfsStop->getStopLat(), $gtfsStop->getStopLon());
    if (contains($gtfsStop->getStopName(), $query) && $distance < 30000) {
        $results[] = $gtfsStop->getStopName();
    }
}

/**
 * Get the distance between 2 coordinates in meters.
 * @param float $lat1
 * @param float $lon1
 * @param float $lat2
 * @param float $lon2
 * @return float
 */
function dist(float $lat1, float $lon1, float $lat2, float $lon2): float
{
    $R = 6371e3; // earth radius, metres

    // convert degrees to radians
    $lat1 = ($lat1 / 180) * M_PI;
    $lat2 = ($lat2 / 180) * M_PI;
    $lon1 = ($lon1 / 180) * M_PI;
    $lon2 = ($lon2 / 180) * M_PI;
    // caclulate differences between latitude and longitude
    $dlat = $lat2 - $lat1;
    $dlon = $lon2 - $lon1;

    // Haversine distance formula
    $a = sin($dlat / 2) * sin($dlat / 2)
        + cos($lat1) * cos($lat2)
        * sin($dlon / 2) * sin($dlon / 2);

    $c = 2 * atan2(sqrt($a), sqrt(1 - $a));
    return $R * $c;
}

function postProcessAlphabetical(array &$array, int $limit = 5): void
{
    // alphabetical first highest up, then use the first 5 keys as return value
    sort($array);
    $array = array_slice($array, 0, 5);
}

function postProcessWeighted(array &$array, int $limit = 5): void
{
    // largest values highest up, then use the first 5 keys as return value
    asort($array);
    $array = array_keys($array);
    $array = array_slice($array, 0, 5);
}

function printResult(array $array)
{
    echo join(PHP_EOL, $array) . PHP_EOL . PHP_EOL;
}

/**
 * @param string $haystack
 * @param string $needle
 * @return bool
 */
function startsWith(string $haystack, string $needle): bool
{
    return strpos(strtolower($haystack), strtolower($needle)) === 0;
}

/**
 * @param string $haystack
 * @param string $needle
 * @return bool
 */
function contains(string $haystack, string $needle): bool
{
    return strpos(strtolower($haystack), strtolower($needle)) !== false;
}