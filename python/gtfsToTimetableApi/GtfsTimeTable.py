import argparse
import datetime
import logging
import os
import sys
import zipfile
from datetime import datetime, timedelta
from io import BytesIO

import requests
import urllib3

from GtfsCacheHelpers import GtfsStopsCache, GtfsRoutesCache, GtfsTripsCache, GtfsStopTimesCache, GtfsCalendarDatesCache
from RealtimeDataFetcher import RealtimeDataFetcher

ROUTE_TYPE_NAMES = {
    100: "TRAIN",
    401: "METRO",
    700: "BUS",
    717: "FÖRBESTÄLLNINGSTRAFIK",
    900: "TRAM",
    1000: "FERRY",
}


class GtfsArchiveFetcher:
    """
    This is a helper class to download and extract GTFS archives.
    """

    @staticmethod
    def fetch_and_extract(url: str, directory: str) -> str:
        """
        Fetch a GTFS file if it hasn't been fetched recently, and extract it.
        :param url: The url to download the archive from in case this is needed.
        :param directory: Where to extract the archive to
        :return: The directory containing the extracted archive
        """
        filename = os.path.basename(urllib3.util.parse_url(url).path)[0:-4]  # Get the filename from the URL
        directory_path = os.path.join(os.getcwd(), directory, filename)

        if not os.path.exists(directory_path):
            os.makedirs(directory_path)

        # Check if a download is needed
        if not GtfsArchiveFetcher.archive_exists(directory_path) or GtfsArchiveFetcher.is_archive_outdated(
                directory_path):
            logging.info("Updating GTFS archive")
            r = requests.get(url, allow_redirects=True)
            zipdata = BytesIO()
            zipdata.write(r.content)
            with zipfile.ZipFile(zipdata) as zip_ref:
                zip_ref.extractall(directory_path)
        return directory_path

    @staticmethod
    def archive_exists(directory):
        return os.path.exists(directory) \
               and os.path.isdir(directory) \
               and os.path.exists(os.path.join(directory, "feed_info.txt"))

    @staticmethod
    def is_archive_outdated(directory):
        """
        Determine if the GTFS feed in a directory is outdated based on the creation time of the feed_info.txt file.
        :param directory: The directory containing the extracted GTFS feed.
        :return: True if outdated, False otherwise.
        """
        creation_time_epoch = os.path.getctime(os.path.join(directory, "feed_info.txt"))
        creation_time = datetime.fromtimestamp(creation_time_epoch)
        is_outdated = datetime.now() - creation_time > timedelta(days=1)
        if is_outdated:
            logging.info("GTFS archive is older than 1 day")
        else:
            logging.info("GTFS archive is less than 1 day old")
        return is_outdated


class TimeTableQueryEngine:

    def __init__(self, gtfs_root, realtime_fetcher, reduce_memory_usage=False):
        logging.info("Initializing TimeTableQueryEngine")
        if reduce_memory_usage:
            logging.warning("Reduced memory usage is enabled."
                            " This will reduce memory usage by up to 90%, at the cost of slower queries.")
        # Initialize all caches here
        self._realtime_fetcher = realtime_fetcher
        self._gtfs_root = gtfs_root
        self._calendar_dates_cache = GtfsCalendarDatesCache(self._gtfs_root)
        self._stops_cache = GtfsStopsCache(self._gtfs_root)
        logging.debug("Initializing stop times cache, this can take a while...")
        self._stop_times_cache = GtfsStopTimesCache(self._gtfs_root, reduce_memory_usage=reduce_memory_usage)
        logging.debug("Initialized stop times cache")
        self._routes_cache = GtfsRoutesCache(self._gtfs_root)
        self._trips_cache = GtfsTripsCache(self._gtfs_root)
        logging.info("Initialized TimeTableQueryEngine")

    def list_queryable_stops(self):
        """
        Get a list of all stops a user would want to search for (stations only, no quays or entrances)
        :return: A list of all stops a user would want to search for.
        """
        return [self._gtfs_stop_to_api_stop(stop) for stop in self._stops_cache.get_all_stops() if
                stop['location_type'] == '1']

    def create_departures_timetable(self,
                                    query_stop_id: str,
                                    window_start: datetime = datetime.now() - timedelta(minutes=10),
                                    window_end: datetime = datetime.now() + timedelta(hours=2)) -> object:
        """
        Create a TimeTable with departure information for a given stop.
        :param query_stop_id:  The id of the stop to search for. All quays in this stop will be automatically included.
        :param window_start: The start date/time of the time window in which to search.
        :param window_end: The end date/time of the time window in which to search.
                           Must be within 24h after after window_start.
        :return: An object containing information about the stops for which the timetable was constructed,
                 and the departures in the requested time frame.
        """
        assert window_start < window_end
        assert (window_end - window_start) < timedelta(days=1)  # The max interval is one day
        # Get the queried stop ids (stopplace + platforms)
        query_stop_ids = self._get_queried_stop_ids(query_stop_id)
        # Get the stop times at these stops
        stop_times = self._get_stop_times_for_stops(query_stop_ids)
        # Only retain stop times in the time window
        stop_times_in_window = self._filter_stop_times_window(stop_times, window_start, window_end)
        # Sort the stop times
        # Only sort when we have filtered out the interesting ones, to prevent wasting time on unnecessary sorting
        stop_times_in_window.sort(key=lambda item: item['departure_seconds'])
        # Compile a response based on the stop times and query ids.
        return self._compile_results(stop_times_in_window, query_stop_ids)

    def _get_queried_stop_ids(self, query_id: str) -> list:
        """
        Get the ids of the parent location and all quays, for the parent or quay provided.
        :param query_id:  Parent location or quay id
        :return:  The ids of the parent location and all quays
        """
        logging.debug("Getting related stops")
        stop = self._stops_cache.get_stop(query_id)
        if stop['parent_station']:
            # Ensure we always search from the top-level stop
            stop = self._stops_cache.get_stop(stop['parent_station'])
        return [stop['stop_id']] + \
               [stop['stop_id'] for stop in self._stops_cache.get_all_quays_in_stop_place(stop['stop_id'])]

    def _get_stop_times_for_stops(self, stop_ids):
        logging.debug("Getting stop times for stops")
        # Get a list of all the stop times at the given stop_ids
        return self._stop_times_cache.get_stop_times_for_stops(stop_ids)

    def _filter_stop_times_window(self, stop_times: list, window_start: datetime, window_end: datetime) -> list:
        """
        This method will only retain the stop times in the given time window
        :param stop_times: The list of stop times to filter.
        :param window_start: The start of the time window.
        :param window_end: End of the time window
        :return: The filtered list
        """
        logging.debug("Filtering stop times")

        # Check if the time window spans across midnight
        window_crosses_midnight = window_end.date() > window_start.date()
        # Calculate the seconds from midnight. This way we can do all later comparisons using integers
        window_start_secs_since_midnight = window_start.time().hour * 3600 \
                                           + window_start.time().minute * 60 \
                                           + window_start.time().second

        window_end_secs_since_midnight = window_end.time().hour * 3600 \
                                         + window_end.time().minute * 60 \
                                         + window_end.time().second

        # Get the day before the start date, needed to check if a trip that spans multiple days was active on this day.
        day_before_start = window_start.date() - timedelta(days=1)

        filtered_stop_times = list()
        for stop_time in stop_times:
            # We already calculated the seconds from midnight in the StopTimesCache.
            secs_since_midnight = stop_time['departure_seconds']
            # The first, easy, check is to see if the time lies between the start and end time.
            # If this fails, we can skip all other checks
            if not self._is_time_in_window(secs_since_midnight,
                                           window_start_secs_since_midnight,
                                           window_end_secs_since_midnight):
                continue

            # Alright, so the time is valid. Is the trip actually ran on that day? Get the service id so we can check
            trip = self._trips_cache.get_trip(stop_time['trip_id'])
            service_id = trip['service_id']

            # Get the hour part from the time. If it is more than 23, it is a trip that started the day before.
            hour_int = secs_since_midnight // 3600

            # This is a trip that started the same day
            if hour_int < 24:
                # If the window doesn't cross midnight, the departure date is the same as the date of the window start.
                # Check if the service_id is active that day
                if not window_crosses_midnight \
                        and self._calendar_dates_cache.is_serviced(service_id, window_start.date()):
                    filtered_stop_times.append(stop_time)
                # If it crosses midnight, we need to determine the departure date first
                elif window_crosses_midnight:
                    # We have constrained the time window to no more than 24h. This means that, if the time window
                    # crosses midnight, the end time will lie before the start time. This simplifies the following tests
                    if secs_since_midnight >= window_start_secs_since_midnight:
                        if self._calendar_dates_cache.is_serviced(service_id, window_start.date()):
                            filtered_stop_times.append(stop_time)
                    else:
                        if self._calendar_dates_cache.is_serviced(service_id, window_start.date()):
                            filtered_stop_times.append(stop_time)
            # This is a trip that started the day before (it's past midnight),
            # check if it was active on the day it started
            elif hour_int >= 24:
                if not window_crosses_midnight and self._calendar_dates_cache.is_serviced(service_id,
                                                                                          day_before_start):
                    filtered_stop_times.append(stop_time)
                # Alright, so the window crosses midnight and this trip started the day before.
                # Since this trip planner is restricted to 1-day intervals, we know the day before is start date
                elif window_crosses_midnight:
                    # We have constrained the time window to no more than 24h. This means that, if the time window
                    # crosses midnight, the end time will lie before the start time. This simplifies the following tests
                    # First day. Comparison corrects for the 24h offset since the hour part is larger than 24h
                    if secs_since_midnight - 86400 >= window_start_secs_since_midnight:
                        if self._calendar_dates_cache.is_serviced(service_id, day_before_start):
                            filtered_stop_times.append(stop_time)
                    # Second day
                    else:
                        if self._calendar_dates_cache.is_serviced(service_id, window_start.date()):
                            filtered_stop_times.append(stop_time)
        return filtered_stop_times

    def _is_time_in_window(self,
                           seconds_since_midnight: int,
                           window_start_since_midnight: int,
                           window_end_since_midnight: int
                           ) -> bool:
        """
        Check if a time (in seconds from midnight) lies in a window. window_end can lie before window_start if
        window_end is on the next day. This only works with the 24h constraint on the time window.
        :param seconds_since_midnight: Time to check in seconds from midnight
        :param window_start_since_midnight: Start of the window
        :param window_end_since_midnight:  End of the window, less than 24h after the start. Can be smaller than
                                           window_start_since_midnight if it is a time during the next day.
        :return: True if the timestamp lies in the window.
        """
        return window_start_since_midnight <= seconds_since_midnight < window_end_since_midnight \
               or (window_start_since_midnight > window_end_since_midnight > seconds_since_midnight >= 0) \
               or (window_end_since_midnight < window_start_since_midnight <= seconds_since_midnight < 24 * 3600)

    def _compile_results(self, stop_times: list, searched_stop_ids: list) -> object:
        """
        Inflate a list of stop times (which are already filtered on location and time) to an API response.
        :param stop_times:  The stop times to include in the API response.
        :param searched_stop_ids:  The stop ids for which departures were calculated.
        :return: The API response
        """
        logging.debug("Compiling results")
        entries = list()
        for stop_time in stop_times:
            # Get additional information for each stop
            trip = self._trips_cache.get_trip(stop_time['trip_id'])
            route = self._routes_cache.get_route(trip['route_id'])
            stop = self._gtfs_stop_id_to_api_stop(stop_time['stop_id'])
            # Get realtime information
            delay = self._realtime_fetcher.get_delay_for_trip_stop(trip['trip_id'], stop_time['stop_sequence'])
            position = self._realtime_fetcher.get_position_for_trip(trip['trip_id'])
            entries.append({
                "direction": stop_time['stop_headsign'],
                "scheduled_departure_time": stop_time['departure_time'],
                "realtime_departure_time": self._add_seconds(stop_time['departure_time'], delay),
                "stop": stop,
                "type": ROUTE_TYPE_NAMES[int(route['route_type'])],
                "route_long": route['route_long_name'],
                "route_short": route['route_short_name'],
                "delay": delay,
                "position": position
            })

        # Wrap departures and stops in one object
        return {"stops": [self._gtfs_stop_id_to_api_stop(stop_id) for stop_id in searched_stop_ids],
                "departures": entries}

    def _gtfs_stop_id_to_api_stop(self, stop_id):
        # This is just a helper metod to wrap the get_stop method call
        return self._gtfs_stop_to_api_stop(self._stops_cache.get_stop(stop_id))

    def _gtfs_stop_to_api_stop(self, stop):
        """
        Create an API stop object based on a GTFS stop. Some attributes are renamed, irrelevant data is left out.
        :param stop:  The GTFS stop.
        :return: The API stop.
        """
        return {
            "id": stop["stop_id"],
            "name": stop["stop_name"],
            "platform": stop["platform_code"],
            "latitude": stop["stop_lat"],
            "longitude": stop["stop_lon"],
        }

    def _add_seconds(self, time: str, seconds: int) -> str:
        """
        Add seconds to a time string
        :param time: A time in hh:mm:ss
        :param seconds: Seconds to add (or subtract) to the given time
        :return: The time with seconds added in hh:mm:ss format
        """
        if seconds == 0:
            return time
        time_seconds = self.get_seconds_since_midnight(time)
        if time_seconds < 0:
            time_seconds += 24 * 3600  # + 1 day in case the delay was negative and we got below zero
        time_seconds += seconds
        # Seconds to hh:mm:ss
        m, s = divmod(time_seconds, 60)  # Get quotient and modulo in one operation
        h, m = divmod(m, 60)
        return f'{h:02d}:{m:02d}:{s:02d}'

    def get_seconds_since_midnight(self, time_str: str) -> int:
        """Get Seconds from time, for faster calculations later on."""
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + int(s)


if __name__ == '__main__':
    root = logging.getLogger()
    root.setLevel(logging.WARN)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.WARN)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    parser = argparse.ArgumentParser(
        description="CLI script to get a realtime timetable for a stop based on GTFS and GTFS-RT data"
    )
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')
    required.add_argument("--gtfs", dest="gtfs_url",
                          help="the url to the gtfs zip file. Include an API key if the gtfs feed requires this.",
                          required=True)
    required.add_argument("--trip-updates",
                          help="the url to the tripupdates.pb file. Include an API key if the realtime feed requires this.",
                          dest="trip_updates", required=True)
    required.add_argument("--vehicle-positions",
                          help="the url to the vehiclepositions.pb file. Include an API key if the realtime feed requires this.",
                          dest="vehicle_positions", required=True)
    required.add_argument("--stop-id", help="the id of the stop to create a timetable for", dest="stop-id",
                          required=True)
    args = parser.parse_args()

    realtime_data_fetcher = RealtimeDataFetcher(args.trip_updates, args.vehicle_positions)
    # The Archive fetcher will only fetch a new file when needed
    gtfs_path = GtfsArchiveFetcher.fetch_and_extract(args.gtfs_url, "gtfs/")
    # The query engine will calculate most of the data on-the-fly.
    # Only one query will be made, so favor lower memory usage since the longer query time
    # will be offset by the reduced startup time.
    query_engine = TimeTableQueryEngine(gtfs_path, realtime_data_fetcher, reduce_memory_usage=True)
    # Run a sample query and print the result
    result = query_engine.create_departures_timetable('9021012080000000')
    print(result)
