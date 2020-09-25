#!/usr/bin/python3
import csv
import gzip
import sys
import time
import urllib
import zipfile
from io import TextIOWrapper, StringIO


# This script downloads a GTFS archive and adds the average number of departures per day to each stop.
#
# Usage: python stops_calculate_average_departures.py
# Example: python stops_calculate_average_departures.py
#
# Note: Use python 3, NOT the outdated 2.7


def get_operating_days_count(gtfs_zip_file):
    """
    Get the number of unique days on which public transport is provided according to the GTFS file
    :param gtfs_zip_file:
    :return:
    """
    used_calendar_dates = set()
    with gtfs_zip_file.open("calendar_dates.txt") as file:
        calendar_dates = get_csv_dict_reader(file)
        for row in calendar_dates:
            used_calendar_dates.add(row["date"])
    return len(used_calendar_dates)


def create_service_frequency_table(gtfs_zip_file):
    """
    Get a dictionary describing the number of days every service is run.
    :param gtfs_zip_file:
    :return:
    """
    service_operating_dates = {}
    with gtfs_zip_file.open("calendar_dates.txt") as file:
        calendar_dates = get_csv_dict_reader(file)
        for row in calendar_dates:
            if row["exception_type"] == "2":
                # No service on this day
                continue

            # Store the operating dates for each service in a set to filter out possible duplicates
            if row["service_id"] not in service_operating_dates.keys():
                service_operating_dates[row["service_id"]] = {row["date"]}
            else:
                service_operating_dates[row["service_id"]].add(row["date"])

    # Map every set with dates to its size in order to obtain a frequency table
    service_frequency_table = \
        dict((service_id, len(dates_set)) for (service_id, dates_set) in service_operating_dates.items())
    return service_frequency_table


def create_trips_frequency_table(gtfs_zip_file, service_frequency_table):
    trips_frequency = {}
    with gtfs_zip_file.open("trips.txt") as file:
        trips = get_csv_dict_reader(file)
        for row in trips:
            trips_frequency[row["trip_id"]] = service_frequency_table[row["service_id"]]

    return trips_frequency


def create_stops_frequency_table(gtfs_zip_file, trips_frequency_table):
    stops_frequency = {}
    with gtfs_zip_file.open("stop_times.txt") as file:
        stop_times = get_csv_dict_reader(file)
        for row in stop_times:
            if row["stop_id"] not in stops_frequency:
                stops_frequency[row["stop_id"]] = trips_frequency_table[row["trip_id"]]
            else:
                stops_frequency[row["stop_id"]] += trips_frequency_table[row["trip_id"]]
    return stops_frequency


def create_stops_with_avg_departures(gtfs_stops_file_path):
    if gtfs_stops_file_path.startswith("http"):
        print(f"[{time.ctime()}] Downloading GTFS archive...")
        response = urllib.request.urlopen(gtfs_stops_file_path)
        gtfs_zip_file = zipfile.ZipFile(response, 'r')
    else:
        print(f"[{time.ctime()}] Opening GTFS archive...")
        gtfs_zip_file = zipfile.ZipFile(gtfs_stops_file_path, 'r')

    print(f"[{time.ctime()}] Starting calculations")

    operating_days = get_operating_days_count(gtfs_zip_file)
    print(f"[{time.ctime()}] {operating_days} operating days found")
    service_frequency_table = create_service_frequency_table(gtfs_zip_file)
    print(f"[{time.ctime()}] {len(service_frequency_table.keys())} services found")
    trips_frequency_table = create_trips_frequency_table(gtfs_zip_file, service_frequency_table)
    print(f"[{time.ctime()}] {len(trips_frequency_table)} trips with traffic found")
    stops_frequency_table = create_stops_frequency_table(gtfs_zip_file, trips_frequency_table)
    print(f"[{time.ctime()}] {len(stops_frequency_table)} stops with traffic found")
    average_departures_per_stop = \
        dict((stop_id, frequency / operating_days) for (stop_id, frequency) in stops_frequency_table.items())

    print(f"[{time.ctime()}] Writing results")

    output_path = "stops.txt"
    with gtfs_zip_file.open("stops.txt") as stops_file:
        stops = get_csv_dict_reader(stops_file)
        fieldnames = stops.fieldnames
        fieldnames.append("avg_stop_times")
        with open(output_path, "w", encoding="utf8", newline='\n') as new_stops_file:
            gtfs_writer = csv.DictWriter(new_stops_file, fieldnames=fieldnames,
                                         delimiter=',', quotechar='"')
            gtfs_writer.writeheader()
            for stop in stops:
                if stop["stop_id"] in average_departures_per_stop:
                    stop["avg_stop_times"] = round(average_departures_per_stop[stop["stop_id"]], 4)
                else:
                    stop["avg_stop_times"] = "0"
                gtfs_writer.writerow(stop)

    print(f"[{time.ctime()}] finished writing results")

    return output_path


def get_csv_dict_reader(zip_file_contents):
    return csv.DictReader(TextIOWrapper(zip_file_contents, 'utf-8'), delimiter=',', quotechar='"')


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <gtfs_url_or_path>")
        exit()
    gtfs_stops_file_path = sys.argv[1]
    output_file_path = create_stops_with_avg_departures(gtfs_stops_file_path)
    print(f"Done! Output can be found at {output_file_path}")
