from geo import *
import logging

logging.basicConfig(
    format="%(levelname)s:%(module)s:%(funcName)s:%(lineno)d:%(message)s"
)
logging.getLogger().setLevel("INFO")

gpx_file = "in_gpx/hood_241225.gpx"
logging.debug(f"GPX file: {gpx_file}\ngetting waypoints...")
waypoints = parse_gpx(gpx_file)
logging.debug("waypoints retrieved")

for photo in list_photo_names():

    # get timestamp from exif data
    logging.debu("getting timestamp from exif data...")
    ts = get_exif_timestamp(photo, offset=-8)  # -8 for PST
    if ts:
        logging.debug("timestamp retrieved; georeferencing...")
        georef = find_closest_waypoint(waypoints, ts)
        logging.info(f"Photo: {photo},\nTimestamp: {ts}\nClosest Waypoint: {georef}")

        # cardinal reference for use in creating DMS coordinates
        ref = get_reference_direction(lat=georef["y"], lon=georef["x"])

        logging.debug("modifying exif data...")
        photo = modify_exif_position(photo, georef, ref)

        logging.debug("modification complete")
        logging.info(f"image w/ updated metadata written to {photo[1]}")

        # photo[0].show()
