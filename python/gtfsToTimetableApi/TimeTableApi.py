"""
A JSON HTTP API for realtime timetables. Requires a static GTFS feed, VehiclePositions.pb and TripUpdates.pb.

"""
import argparse
import json
import logging
import sys

import flask

# Initialize the logger before importing our other module. This way we see the output for the other module as well.
root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

# Initialize the logger before importing our other module. This way we see the output for the other module as well.
from GtfsTimeTable import TimeTableQueryEngine, GtfsArchiveFetcher
from RealtimeDataFetcher import RealtimeDataFetcher

app = flask.Flask(__name__)


@app.route('/departures/<stop_id>', methods=['GET'])
def departures(stop_id):
    resp = flask.Response(json.dumps(query_engine.create_departures_timetable(stop_id)))
    resp.headers['Content-encoding'] = 'UTF-8'
    resp.headers['Content-type'] = 'Application/json'
    return resp


@app.route('/stops/', methods=['GET'])
def stops():
    resp = flask.Response(json.dumps(query_engine.list_queryable_stops()))
    resp.headers['Content-encoding'] = 'UTF-8'
    resp.headers['Content-type'] = 'Application/json'
    return resp


parser = argparse.ArgumentParser(
    description="Start a JSON HTTP API based on GTFS and GTFS-RT data"
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
optional.add_argument("--uncached", help="this option will reduce memory significantly, but queries will be slow",
                      action='store_true')
args = parser.parse_args()

realtime_data_fetcher = RealtimeDataFetcher(args.trip_updates, args.vehicle_positions)
# The Archive fetcher will only fetch a new file when needed
gtfs_path = GtfsArchiveFetcher.fetch_and_extract(args.gtfs_url, "gtfs/")
query_engine = TimeTableQueryEngine(gtfs_path, realtime_data_fetcher, reduce_memory_usage=args.uncached)

app.config["DEBUG"] = False
app.run()
