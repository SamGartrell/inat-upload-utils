import os
import xml.etree.ElementTree as ET
from PIL import Image
from PIL.ExifTags import TAGS
import requests
from datetime import datetime, timezone, timedelta


# region time
def convert_to_utc(
    timestamp_str: str,
    fmt: str = "%Y:%m:%d %H:%M:%S",
    outfmt: str = "%Y:%m:%d %H:%M:%S",
    local_offset: int = -8,  # PST
):
    # Parse the timestamp string to a datetime object
    local_time = datetime.strptime(timestamp_str, fmt)

    # Define the PST timezone (UTC-8)
    gmt_offset = timezone(timedelta(hours=local_offset))

    # Localize the datetime object to PST
    local_time = local_time.replace(tzinfo=gmt_offset)

    # Convert the localized time to UTC
    utc_time = local_time.astimezone(timezone.utc)

    # Return the UTC time as a string in the same format
    return utc_time.strftime(outfmt)


# endregion time


# region gpx
def parse_gpx(gpx_file):
    """Parse GPX file and return a list of waypoints with their timestamps."""
    tree = ET.parse(gpx_file)
    root = tree.getroot()
    # Namespace for GPX file
    ns = {"default": "http://www.topografix.com/GPX/1/1"}

    waypoints = []

    for trkpt in root.findall(".//default:trkpt", ns):
        time = trkpt.find("default:time", ns).text
        timestamp = convert_to_utc(
            time,
            fmt="%Y-%m-%dT%H:%M:%SZ",
            local_offset=0,
        )  # gpx files are in UTC but we still gotta reformat the stamp
        lat = float(trkpt.attrib["lat"])
        lon = float(trkpt.attrib["lon"])
        waypoints.append({"t": timestamp, "x": lon, "y": lat})

    return waypoints


def find_closest_waypoint(
    waypoints,
    target_timestamp: str,
    waypoint_fmt="%Y:%m:%d %H:%M:%S",
    target_fmt="%Y:%m:%d %H:%M:%S",
):
    """Find the waypoint with the timestamp closest to the target timestamp."""
    time_difs = {}

    wp_copy = waypoints.copy()

    for wp in wp_copy:
        wp_time = datetime.strptime(wp["t"], waypoint_fmt)
        target_time = datetime.strptime(target_timestamp, target_fmt)
        time_dif = abs(wp_time - target_time)
        wp["delta"] = time_dif

    wp_copy.sort(key=lambda x: x["delta"])
    return wp_copy[0]


def get_track_timespan(waypoints):
    """Return the start and end waypoints."""
    start, end = waypoints[0], waypoints[-1]

    start_time = start["t"]
    end_time = end["t"]

    return (start_time, end_time)


# endregion gpx
# region images
def list_photo_names(directory: str = None):
    """Retrieve all photo names from a given directory."""
    if not directory:
        directory = os.path.join(os.getcwd(), "in_photos")

    return list(os.listdir(directory))


def get_exif_timestamp(
    photo_name: str,
    directory: str = None,
    as_utc: bool = True,
    tz: timedelta = timedelta(hours=-8),  # PST
):
    """Gets the timestamp from the EXIF data of an image."""
    if not directory:
        directory = os.path.join(os.getcwd(), "in_photos")
    try:
        with Image.open(os.path.join(directory, photo_name)) as img:
            exif_data = img.getexif()

            if exif_data:
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    # if tag_name != "XMLPacket":
                    #     print(TAGS.get(tag_id, tag_id), "\t\t\t", value)
                    if tag_name == "DateTime":
                        print(f"image {photo_name} was taken at {value}")
                        timestamp = value
                        break
        if timestamp:
            if as_utc:
                print("converting timestamp to UTC")
                timestamp = convert_to_utc(timestamp)
                print(f"UTC timestamp: {timestamp}")
                return timestamp
            else:
                return datetime.strptime(timestamp, "%Y:%m:%d %H:%M:%S")

    except Exception as e:
        print(f"Error: {e}")
        return None


# endregion images
# Example usage
gpx_file = "gpx/sample.gpx"
print(f"GPX file: {gpx_file}\ngetting waypoints...")
waypoints = parse_gpx(gpx_file)
print(f"waypoints: {waypoints}")

print(f"photo funcs")
for photo in list_photo_names():
    ts = get_exif_timestamp(photo)
    print(
        f"Photo: {photo},\nTimestamp: {ts}\nClosest Waypoint: {find_closest_waypoint(waypoints, ts)}"
    )
    print()
