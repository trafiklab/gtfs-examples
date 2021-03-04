#!/usr/bin/python3
import csv
import json
import sys

# This script adds the municipality to every stop in a GTFS stops.txt file.
# If the municipality cannot be found, nothing is added.
# This script makes use of the raycasting point in polygon algorithm: https://en.wikipedia.org/wiki/Point_in_polygon
#
# Usage: python stops_insert_municipality.py <stops_file> <geojson_borders_file>
# Example: python stops_insert_municipality.py stops.txt Sweden_AL7_OSM.geojson
# Obtain a file from https://osm-boundaries.com/ (replacement of https://wambachers-osm.website/boundaries/)
#
# Note: Use python 3, NOT the outdated 2.7

def add_municipality_to_gtfs_stops(gtfs_stops_file_path: str, geojson_file_path: str):
    output_path = gtfs_stops_file_path[0:-4] + "_with_municipalities.txt"

    with open(geojson_file_path, "r", encoding="utf8") as geojson_file:
        geojson = json.load(geojson_file)

    with open(gtfs_stops_file_path, "r", encoding="utf8") as stops_file:
        gtfs_reader = csv.DictReader(stops_file, delimiter=',', quotechar='"')
        with open(output_path, "w", encoding="utf8", newline='\n') as new_stops_file:
            gtfs_writer = csv.DictWriter(new_stops_file, fieldnames=gtfs_reader.fieldnames,
                                         delimiter=',', quotechar='"')
            for stop in gtfs_reader:
                write_stop_with_municipality(stop, gtfs_writer, geojson)
    return output_path


def write_stop_with_municipality(stop, new_stops_file, geojson):
    stop["stop_name"] = getNameWithMunicipalityForStop(stop, geojson)
    new_stops_file.writerow(stop)


def getNameWithMunicipalityForStop(stop, geojson):
    lon = float(stop["stop_lon"])
    lat = float(stop["stop_lat"])
    municipality = getMunicipalityForCoordinates(lon, lat, geojson)
    if municipality:
        return stop["stop_name"] + " (" + municipality["properties"]["official_name"] + ")"
    return stop["stop_name"]


def getMunicipalityForCoordinates(lat, lon, geojson):
    for feature in geojson["features"]:
        if "bbox" in feature:
            bbox = feature["bbox"]
            if not in_bbox(lat, lon, bbox):
                continue

        if "geometry" not in feature:
            continue

        geometry_type = feature["geometry"]["type"]
        # A triple-nested list: A list of rings, where each ring is a list of coordinates, where a coordinate is a
        # list of floats.
        coordinates = feature["geometry"]["coordinates"]
        if in_polygon(lon, lat, coordinates):
            return feature
    return False


def in_bbox(lat, lon, bbox):
    bbox_lon1 = bbox[1]
    bbox_lon2 = bbox[3]
    bbox_lat1 = bbox[0]
    bbox_lat2 = bbox[2]
    return min(bbox_lon1, bbox_lon2) < lon < max(bbox_lon1, bbox_lon2) \
           and min(bbox_lat1, bbox_lat2) < lat < max(bbox_lat1, bbox_lat2)


def in_polygon(lat, lon, coordinates):
    inside = False
    for ring in coordinates:
        for polygon in ring:
            polygon_size = len(polygon)
            for i in range(0, polygon_size):
                coordinate = polygon[i]
                next_coordinate = polygon[(i + 1) % polygon_size]
                if intersects_with_northbound_ray(lon, lat, coordinate, next_coordinate):
                    inside = not inside
    return inside


def intersects_with_northbound_ray(lat, lon, line_start, line_end):
    if line_start[1] > line_end[1]:
        return intersects_with_northbound_ray(lon, lat, line_end, line_start)

    # If the longitude lies exactly on the start or end latitude, move it a bit.
    if lon == line_start[1] or lon == line_end[1]:
        lon += 0.00001
        # YES, this adjust our point.
        # HOWEVER, this method is internal. There will be another line, also going from this point
        # THEREFORE, both lines will get the same offset, meaning both will be added or removed from the polygon.
        # Sketch it to visualise the situation.
        # 2x the same adjustment will correct itself in the odd/even algorithm

    # If the longitude of the point is higher than the longitude of the edges high end, they don't cross.
    # Remember, the edge end point has the largest longitude.
    # If the longitude of the point is higher than the longitude of the edges low end, they don't cross.
    # Remember, the edge start point has the lowest longitude.
    # If the point lies above the edge, towards the north, they don't cross.
    if lon > line_end[1] or lon < line_start[1] or lat > max(line_start[0], line_end[0]):
        return False

    # If the point lies to the south of the most south point of the line,
    # while its longitude lies between the edges of the line (see above), an northbound ray will cross this line.
    if lat < min(line_start[0], line_end[0]):
        return True

    # The last case is the case where the longitude of the point lies between the minimum and maximum longitude of the line, and the latitude lies
    # between the minimum and maximum latitude of the line. Determine if the point lies to the north (doesn't cross) or south side (crosses) of the line.

    # In order for this, determine the slope of
    # - The line, passed in the parameters, which is being test
    # - The line formed by the point and the start of the line which was passed in the parameters
    if line_start[0] == line_end[0] and line_start[0] == lat:
        # If the line is vertical and the point lies on the line
        # The complete "point on line" test is further down
        # This assertion is sensitive the the exact location in the code!
        # The if statement is based on the fact that the longitude of the point has already been
        # confirmed to lie within the bounding box of the line
        raise Exception("Point lies on vertical line, therefore it can't be above or below the line")
    start_of_line_to_point_slope = getSlopeBetweenTwoPoints(line_start, [lat, lon])
    defined_line_slope = getSlopeBetweenTwoPoints(line_start, line_end)
    return start_of_line_to_point_slope > defined_line_slope


def getSlopeBetweenTwoPoints(start_point, end_point):
    return (end_point[1] - start_point[1]) / (end_point[0] - start_point[0])


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <stops_file> <geojson_borders_file>")
        exit()
    gtfs_stops_file_path = sys.argv[1]
    geojson_file_path = sys.argv[2]
    output_file_path = add_municipality_to_gtfs_stops(gtfs_stops_file_path, geojson_file_path)
    print(f"Done! Output can be found at {output_file_path}")
