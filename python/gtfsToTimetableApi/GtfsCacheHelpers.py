import csv
from collections import defaultdict
from datetime import datetime


class GtfsStopsCache:
    def __init__(self, gtfs_root):
        self._gtfs_root = gtfs_root
        self._stops_by_id = self._get_stops_by_id()
        self._stops_by_parent_id = self._map_stops_by_parent_id(self._stops_by_id)

    def get_stop(self, id):
        return self._stops_by_id[id]

    def get_all_stops(self):
        return self._stops_by_id.values()

    def get_all_quays_in_stop_place(self, parent_id):
        return self._stops_by_parent_id[parent_id]

    def _get_stops_by_id(self):
        stops = dict()
        with open(self._gtfs_root + "/stops.txt", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=',')
            for row in reader:
                stops[row['stop_id']] = row
        return stops

    def _map_stops_by_parent_id(self, stops_by_id):
        stops_by_parent_id = defaultdict(list)
        for stop in stops_by_id.values():
            if stop['parent_station']:
                stops_by_parent_id[stop['parent_station']].append(stop)
        return stops_by_parent_id


class GtfsRoutesCache:
    def __init__(self, gtfs_root):
        self._gtfs_root = gtfs_root
        self._routes_by_id = self._get_routes_by_id()

    def get_route(self, id):
        return self._routes_by_id[id]

    def _get_routes_by_id(self):
        routes = dict()
        with open(self._gtfs_root + "/routes.txt", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=',')
            for row in reader:
                routes[row['route_id']] = row
        return routes


class GtfsTripsCache:
    def __init__(self, gtfs_root):
        self._gtfs_root = gtfs_root
        self._trips_by_id = self._get_trips_by_id()

    def get_trip(self, id):
        return self._trips_by_id[id]

    def _get_trips_by_id(self):
        trips = dict()
        with open(self._gtfs_root + "/trips.txt", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=',')
            for row in reader:
                trips[row['trip_id']] = row
        return trips


class GtfsStopTimesCache:
    def __init__(self, gtfs_root, reduce_memory_usage=False):
        self._gtfs_root = gtfs_root
        self._reduce_memory_usage = reduce_memory_usage
        if not reduce_memory_usage:
            self._stop_times = self._get_stop_times()
            self._stops_by_stop_id = self._map_stop_times_by_stop_id(self._stop_times)
            self._stops_by_trip_id = self._map_stop_times_by_trip_id(self._stop_times)

    def get_stop_times(self):
        return self._stop_times

    def get_stop_times_for_trip(self, trip_id):
        if not self._reduce_memory_usage:
            return self._stops_by_trip_id[trip_id]
        else:
            stop_times = list()
            with open(self._gtfs_root + "/stop_times.txt", encoding="utf-8-sig") as csv_file:
                reader = csv.DictReader(csv_file, delimiter=',')
                for row in reader:
                    if row['trip_id'] != trip_id:
                        continue
                    # Perform this "heavy lifting" once, so we can reuse it quickly later on
                    row['departure_seconds'] = self.get_seconds_since_midnight(row['departure_time'])
                    stop_times.append(row)
            return stop_times

    def get_stop_times_for_stop(self, stop_id):
        if not self._reduce_memory_usage:
            return self._stops_by_stop_id[stop_id]
        else:
            stop_times = list()
            with open(self._gtfs_root + "/stop_times.txt", encoding="utf-8-sig") as csv_file:
                reader = csv.DictReader(csv_file, delimiter=',')
                for row in reader:
                    if row['stop_id'] != stop_id:
                        continue
                    # Perform this "heavy lifting" once, so we can reuse it quickly later on
                    row['departure_seconds'] = self.get_seconds_since_midnight(row['departure_time'])
                    stop_times.append(row)
            return stop_times

    def get_stop_times_for_stops(self, stop_ids):
        if not self._reduce_memory_usage:
            stop_time_lists = [self.get_stop_times_for_stop(stop_id) for stop_id in stop_ids]
            return [item for sublist in stop_time_lists for item in sublist]
        else:
            stop_times = list()
            with open(self._gtfs_root + "/stop_times.txt", encoding="utf-8-sig") as csv_file:
                reader = csv.DictReader(csv_file, delimiter=',')
                for row in reader:
                    if row['stop_id'] not in stop_ids:
                        continue
                    # Perform this "heavy lifting" once, so we can reuse it quickly later on
                    row['departure_seconds'] = self.get_seconds_since_midnight(row['departure_time'])
                    stop_times.append(row)
            return stop_times

    def _get_stop_times(self):
        stop_times = list()
        with open(self._gtfs_root + "/stop_times.txt", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=',')
            for row in reader:
                # Perform this "heavy lifting" once, so we can reuse it quickly later on
                row['departure_seconds'] = self.get_seconds_since_midnight(row['departure_time'])
                stop_times.append(row)
        return stop_times

    def _map_stop_times_by_stop_id(self, _stop_times):
        stop_times_by_stop = defaultdict(list)
        for stop in _stop_times:
            stop_times_by_stop[stop['stop_id']].append(stop)
        return stop_times_by_stop

    def _map_stop_times_by_trip_id(self, _stop_times):
        stop_times_by_trip = defaultdict(list)
        for stop in _stop_times:
            stop_times_by_trip[stop['trip_id']].append(stop)
        return stop_times_by_trip

    def get_seconds_since_midnight(self, time_str):
        """Get Seconds from time, for faster calculations later on."""
        h = time_str[0:2]
        m = time_str[3:5]
        s = time_str[6:8]
        return int(h) * 3600 + int(m) * 60 + int(s)


class GtfsCalendarDatesCache:
    def __init__(self, gtfs_root):
        self._gtfs_root = gtfs_root
        self._calendar_dates = self._get_calendar_dates()
        self._dates_by_service = self._map_operating_days_by_service(self._calendar_dates)
        self._services_by_date = self._map_services_by_date(self._calendar_dates)
        self._trip_serviced_on_date_cache = dict()  # Filled during use


    def _get_calendar_dates(self):
        dates = list()
        with open(self._gtfs_root + "/calendar_dates.txt", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=',')
            for row in reader:
                row['date'] = datetime.strptime(row['date'], '%Y%m%d').date()
                dates.append(row)
        return dates

    def _map_operating_days_by_service(self, dates):
        dates_by_id = defaultdict(list)
        for row in dates:
            if row['exception_type'] == '1':
                dates_by_id[row['service_id']].append(row['date'])
        return dates_by_id

    def _map_services_by_date(self, dates):
        dates_by_id = defaultdict(list)
        for row in dates:
            if row['exception_type'] == '1':
                dates_by_id[row['date']].append(row['service_id'])
        return dates_by_id

    def get_service_operating_days(self, service_id):
        return self._dates_by_service[service_id]

    def get_operating_services(self, date):
        return self._services_by_date[date]

    def is_serviced(self, service_id, date):
        key = (service_id, date)
        if key not in self._trip_serviced_on_date_cache:
            self._trip_serviced_on_date_cache[key] = service_id in self._services_by_date[date]
        return self._trip_serviced_on_date_cache[key]
