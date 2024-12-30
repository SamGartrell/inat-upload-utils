# region modules
import os
import xml.etree.ElementTree as ET
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import requests
from datetime import datetime, timezone, timedelta
import math
from typing import Tuple


# endregion modules
# region temporal


def parse_tz(tz: str) -> int:
    """Parse the tz component of a timezone string and return the offset."""
    is_negative = False
    if tz.startswith("-"):
        is_negative = True
        tz = tz.strip("-")

    hours, minutes = tz.split(":")
    min_offset = (60 * int(hours)) + int(minutes)
    hour_offset = min_offset / 60
    offset = math.ceil(hour_offset * 2) / 2  # get to 1/2 hour precision

    if is_negative:
        return offset * -1
    return offset


def convert_to_utc(
    timestamp_str: str,
    fmt: str = "%Y:%m:%d %H:%M:%S%Z",
    outfmt: str = "%Y:%m:%d %H:%M:%S",
    local_offset: int = None,
):
    if fmt.endswith("%Z"):
        local_offset = parse_tz(
            timestamp_str[19:]  # e.g. -08:00 or 02:30 -> -8.0 or 2.5
        )
        fmt = fmt[:-2]
        timestamp_str = timestamp_str[:19]

    elif not local_offset:
        raise ValueError(
            "Local offset must be provided if timestamp does not include timezone info."
        )

    local_time = datetime.strptime(timestamp_str, fmt)

    gmt_offset = timezone(timedelta(hours=local_offset))

    local_time = local_time.replace(tzinfo=gmt_offset)

    utc_time = local_time.astimezone(timezone.utc)

    return utc_time.strftime(outfmt)


def validate_timediff_size(timediff: timedelta, threshold_hrs=2):
    """Check if the time difference is within an appropriate threshold."""
    threshold_seconds = threshold_hrs * 3600
    return abs(timediff.seconds()) <= threshold_seconds


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


# endregion temporal


# region spatial
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
            time, fmt="%Y-%m-%dT%H:%M:%S%Z"
        )  # gpx files are in UTC but we still gotta reformat the stamp
        lat = float(trkpt.attrib["lat"])
        lon = float(trkpt.attrib["lon"])
        waypoints.append({"t": timestamp, "x": lon, "y": lat})

    return waypoints


def truncate(f: float, n: int = 0) -> float:
    # ref: https://github.com/python-pillow/Pillow/issues/6657
    """
    Method for truncating a float value to n digits without rounding
    :param f: to be truncated
    :param n: number of digits
    :return: truncated float
    """
    return math.floor(f * 10**n) / 10**n


def get_dms_from_decimal(decimal: float) -> Tuple[float, float, float]:
    # ref: https://github.com/python-pillow/Pillow/issues/6657
    """
    Convert decimal value to DMS (degrees, minutes, seconds) tuple
    :param decimal: to be converted
    :return:
    """
    degrees = truncate(decimal, 0)
    minutes_whole = (decimal - degrees) * 60
    minutes = truncate(minutes_whole, 0)
    seconds = (minutes_whole - minutes) * 60
    return degrees, minutes, seconds


def get_decimal_from_dms(dms: Tuple[float, float, float], ref: str = "N") -> float:
    # ref: https://github.com/python-pillow/Pillow/issues/6657
    """
    Method for converting a DMS (degrees, minutes, seconds) tuple to a decimal value
    :param dms: to be converted
    :param ref: compass direction (N, E, S, W)
    :return: decimal representation
    """
    degrees = dms[0]
    minutes = dms[1] / 60.0
    seconds = dms[2] / 3600.0

    if ref in ["S", "W"]:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds

    return degrees + minutes + seconds


# endregion spatial
# region images
def get_XYZ(photo_name: str, directory: str = None) -> Tuple[float, float, float]:
    """
    Read gps EXIF information form image
    :param image_path: from which EXIF should be read
    :return: (lat, lng, alt) tuple
    """
    # ref: https://github.com/python-pillow/Pillow/issues/6657
    if not directory:
        directory = os.path.join(os.getcwd(), "in_photos")

    image_path = os.path.join(directory, photo_name)
    image = Image.open(image_path)

    exif = image.getexif()
    gps_info = exif.get_ifd(34853)
    gps_exif = {GPSTAGS.get(key, key): value for key, value in gps_info.items()}
    gps_latitude = gps_exif.get("GPSLatitude")
    gps_longitude = gps_exif.get("GPSLongitude")

    if gps_longitude is None or gps_latitude is None:
        raise Exception("No GPS information available in image")

    gps_latitude_ref = gps_exif.get("GPSLatitudeRef") or "N"
    gps_longitude_ref = gps_exif.get("GPSLongitudeRef") or "E"

    lat = get_decimal_from_dms(gps_latitude, gps_latitude_ref)
    lng = get_decimal_from_dms(gps_longitude, gps_longitude_ref)
    alt = gps_exif.get("GPSAltitude") or 0

    return lat, lng, alt


def write_XY(
    photo_name: str,
    lng: float,
    lat: float,
    alt: float = 0.0,
    camera_manufacturer: str = "Canon",
    camera: str = "T5EOS M100",
    in_directory: str = None,
    out_directory: str = None,
    out_fmt="JPEG",
) -> Tuple:
    """
    Method for writing GPS exif information to an image
    :param image_path: to which exif should be added
    :param lng: longitude
    :param lat: latitude
    :param alt: altitude
    :param camera_manufacturer: Manufacturer of the camera
    :param camera: Camera used
    :out_fmt: output format (see format parameter in PIL.Image.Save())
    :return: None
    """
    # ref: https://github.com/python-pillow/Pillow/issues/6657
    # ref: https://exiftool.org/TagNames/GPS.html
    if not in_directory:
        directory = os.path.join(os.getcwd(), "in_photos")
    if not out_directory:
        out_directory = os.path.join(os.getcwd(), "out_photos")

    image_path = os.path.join(in_directory, photo_name)
    image = Image.open(image_path)

    exif = image.getexif()
    # TODO: edit tag manipulations according to second ref
    # TODO: consider using exiftool to get a better idea of what tags to use
    # TODO: consider capturing snapshot of exif data before and after writing to compare, as per https://en.wikipedia.org/wiki/Exif#cite_note-14
    gps_value = {
        0: b"\x02\x03\x00\x00",
        1: "N",
        2: get_dms_from_decimal(lat),
        3: "E",
        4: get_dms_from_decimal(lng),
        5: b"\x00",
        6: alt,
        9: "A",
        18: "WGS-84\x00",
    }

    exif[34853] = gps_value
    exif[271] = camera_manufacturer
    exif[272] = camera

    photo_title = photo_name.split(".")[0]
    if not out_fmt:
        out_fmt = photo_name.split(".")[1]
    image_path = os.path.join(out_directory, f"{photo_title}_georeferenced.{out_fmt}")
    image.save(image_path, exif=exif, format=out_fmt)

    return (image, image_path)


def list_photo_names(directory: str = None):
    """Retrieve all photo names from a given directory."""
    if not directory:
        directory = os.path.join(os.getcwd(), "in_photos")

    return list(os.listdir(directory))


def get_exif_timestamp(
    photo_name: str,
    directory: str = None,
    as_utc: bool = True,
    offset: int = None,
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
                timestamp = convert_to_utc(
                    timestamp,
                    fmt="%Y:%m:%d %H:%M:%S",
                    outfmt="%Y:%m:%d %H:%M:%S",
                    local_offset=offset,
                )
                print(f"UTC timestamp: {timestamp}")
                return timestamp
            else:
                return datetime.strptime(timestamp, "%Y:%m:%d %H:%M:%S")

    except Exception as e:
        print(f"Error: {e}")
        return None


def modify_exif_position(
    photo_name: str,
    waypoint: dict,
    in_directory: str = None,
    out_directory: str = None,
    camera_manufacturer: str = "Canon",
    camera: str = "T5EOS M100",
) -> Tuple:
    """Relays the XY from a GPX waypoint to the EXIF data of an image."""
    if not in_directory:
        in_directory = os.path.join(os.getcwd(), "in_photos")
    if not out_directory:
        out_directory = os.path.join(os.getcwd(), "out_photos")

    lat = waypoint.get("y", 0)
    lon = waypoint.get("x", 0)
    alt = waypoint.get("z", 0)

    out_photo = write_XY(
        photo_name,
        lon,
        lat,
        alt,
        in_directory=in_directory,
        out_directory=out_directory,
    )
    return out_photo


# endregion images

# region web
###
# ref: https://github.com/python-pillow/Pillow/issues/6657
###


# endregion web
# Example usage

# region example
gpx_file = "gpx/hood_241225.gpx"
print(f"GPX file: {gpx_file}\ngetting waypoints...")
waypoints = parse_gpx(gpx_file)
# print(f"waypoints: {waypoints}")

print(f"photo funcs")
for photo in list_photo_names():
    ts = get_exif_timestamp(photo, offset=-8)  # -8 for PST
    georef = find_closest_waypoint(waypoints, ts)
    print(f"Photo: {photo},\nTimestamp: {ts}\nClosest Waypoint: {georef}")
    print()

    print("modifying exif data...")
    photo = modify_exif_position(photo, georef)
    print("modification complete")
    print(f"image written to {photo[1]}")
    photo[0].show()


# endregion example
