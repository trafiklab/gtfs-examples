import time

import requests
from google.transit import gtfs_realtime_pb2


class RealtimeDataFetcher:
    def __init__(self, tripupdates_url, vehicle_positions_url):
        self._tripupdates_url = tripupdates_url
        self._positions_url = vehicle_positions_url
        self._delays = None
        self._delays_last_updated = None
        self._positions = None
        self._positions_last_updated = None

    def get_delays(self):
        '''
        Get the data. Cached data if it was fetched recently,
        or a fresh copy if the stored data is expired.
        :return:
        '''
        if self._are_delays_outdated():
            self._refresh_delays()
        return self._delays

    def get_positions(self):
        '''
        Get the data. Cached data if it was fetched recently,
        or a fresh copy if the stored data is expired.
        :return:
        '''
        if self._are_positions_outdated():
            self._refresh_positions()
        return self._positions

    def _are_delays_outdated(self):
        now = int(time.time())
        # Data never fetched or data older than x seconds
        return self._delays_last_updated is None or now - self._delays_last_updated > 60

    def _are_positions_outdated(self):
        now = int(time.time())
        # Data never fetched or data older than x seconds
        return self._positions_last_updated is None or now - self._positions_last_updated > 15

    def _refresh_delays(self):
        delays = dict()
        feed = gtfs_realtime_pb2.FeedMessage()
        response = requests.get(self._tripupdates_url).content
        feed.ParseFromString(response)
        for entity in feed.entity:
            if entity.HasField('trip_update'):
                # Handle
                trip_id = entity.trip_update.trip.trip_id
                for update in entity.trip_update.stop_time_update:
                    stop_sequence = update.stop_sequence  # ambiguous, need stop_sequence!
                    if not update.HasField('departure'):
                        continue
                    delay = update.departure.delay
                    delays[(trip_id, stop_sequence)] = delay
        self._delays = delays
        self._delays_last_updated = int(time.time())

    def _refresh_positions(self):
        positions = dict()
        feed = gtfs_realtime_pb2.FeedMessage()
        response = requests.get(self._positions_url).content
        feed.ParseFromString(response)
        for entity in feed.entity:
            if entity.HasField('vehicle'):
                # Handle
                position = entity.vehicle.position
                trip_id = entity.vehicle.trip.trip_id
                positions[trip_id] = {
                    "latitude": position.latitude,
                    "longitude": position.longitude,
                    "bearing": position.bearing,
                    "speed": position.speed * 3.6,  # m/s to kph
                }
        self._positions = positions
        self._positions_last_updated = int(time.time())

    def get_delay_for_trip_stop(self, trip_id, stop_sequence):
        data = self.get_delays()
        # Convert to int to match the data type from protobuf
        stop_sequence = int(stop_sequence)
        if (trip_id, stop_sequence) not in data:
            return 0
        return data[(trip_id, stop_sequence)]

    def get_position_for_trip(self, trip_id):
        data = self.get_positions()
        if trip_id not in data:
            return {}
        return data[trip_id]