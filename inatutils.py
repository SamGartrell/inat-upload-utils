# %%
import json
import requests
import os
import sys
import uuid
from pprint import pprint
import logging

# import oauthlib

# local
from upload import batch
from suggest import id
from georeference import geo

class InatUtils:
    # region props
    def __init__(
        self,
        photo_dir=None,
        gpx_dir=None,
        output_dir=None,
        gmt_offset: int = -8,
        token=None,
        trusted_genera=None,
        log_level=logging.INFO,
    ):
        self.photos = []
        self.trusted_genera = []
        self.georeferenced_percent = 0.0
        self.identified_percent = 0.0
        self.time_range = None
        self.waypoints = []  # TODO: refactor waypoints to be numpy array
        self.bbox = None
        self.photo_dir = photo_dir
        self.gpx_dir = gpx_dir
        self.output_dir = output_dir
        self.token = token
        self.offset = gmt_offset
        self.log_level = log_level
        logging.basicConfig(
            format="%(levelname)s:%(module)s:%(funcName)s:%(lineno)d:%(message)s"
        )
        logging.getLogger().setLevel(self.log_level)

        if photo_dir:
            self.photos = self.load_images(photo_dir=photo_dir)

        if gpx_dir:
            self.georeference(gpx_dir=gpx_dir)

            if self.georeferenced_percent:
                self.bbox = self._get_bbox()

        if token:
            self._token = token
        else:
            self._token = id.refresh_token()

    # region image class
    class Image:
        def __init__(self, path: str, offset: int):
            self.id = str(uuid.uuid4())
            self.name = os.path.split(path)[1]
            self.folder = os.path.split(path)[0]
            self.path = path
            self.format = os.path.splitext(self.path)[1]
            self.offset = offset
            self.datetime = geo.get_exif_timestamp(
                self.name, directory=self.folder, offset=self.offset
            )
            self.geo = dict()
            self.georeferenced = False
            self.identified = False
            self.outputs = []

    # region methods
    def load_images(self, photo_dir) -> list[Image]:
        out_images = []
        for pic in geo.list_photo_names(directory=photo_dir):
            path = os.path.join(os.getcwd(), photo_dir, pic)
            photo = InatUtils.Image(path=path, offset=self.offset)

            out_images.append(photo)
        return out_images

    def georeference(self, gpx_dir=None, photo_dir=None, delta_threshold=None):

        if not gpx_dir and self.gpx_dir != None:
            gpx_dir = self.gpx_dir
        elif not gpx_dir and not self.gpx_dir:
            logging.error("cannot georeference; no GPX dir was provided")
        gpx_files = [
            os.path.join(gpx_dir, f) for f in geo.list_gpx_files(directory=gpx_dir)
        ]

        if not gpx_files:
            logging.warning(f"no gpx files found in {gpx_dir}")
            return None

        for gpx in gpx_files:
            self.waypoints.extend(geo.parse_gpx(gpx))

        logging.debug(
            f"{len(self.waypoints)} waypoints created from {len(gpx_files)} gpx files"
        )

        for p in self.photos:
            if not p.datetime:
                logging.debug(f"{p.name} has no timestamp and cannot be georeferenced")
                continue
            logging.debug(f"georeferencing {p.name}...")
            georef = geo.find_closest_waypoint(self.waypoints, p.datetime)
            if not georef:
                logging.warning(f"waypoint matching failed for {p.name}")
                continue
            p.geo = georef
            p.georeferenced = True

            logging.debug(
                f"waypoint matching succeeded with timedelta {p.geo['delta']}"
            )

            if delta_threshold and p.geo["delta"] > delta_threshold:
                logging.warning(
                    f"waypoint matching was not within {delta_threshold}-minute time accuracy threshold for {p.name}; skipping EXIF georeferencing"
                )
                continue

            ref = geo.get_reference_direction(lat=p.geo["y"], lon=p.geo["x"])

            # TODO: split waypoint matching and exif georeferencing into separate functions
            logging.debug("modifying exif data...")
            try:
                geo_img = geo.modify_exif_position(p.name, georef, ref)
                print("modification complete")
                print(f"image written to {geo_img[1]}")

                p.outputs.append(InatUtils.Image(geo_img[1], self.offset))
            except Exception as e:
                logging.error(e)

        # TODO: modify exif metadata with p.geo

        self.georeferenced_percent = (
            sum(1 for p in self.photos if p.georeferenced) / len(self.photos)
            if self.photos
            else 0.0
        )

    def identify(self, confidence_threshold=75):
        # Implementation for identifying species in photos
        pass

    def dump_jpg(self):
        # Implementation for dumping photos as JPG
        pass

    def dump_csv(self):
        # Implementation for dumping data to CSV
        pass

    def _get_token(self, appId):
        # todo: employ oauthlib after attaining inat app registration
        pass

    def _get_bbox(self):
        pass
        # min_lat = 999999999
        # min_lon = 999999999
        # max_lat = 0
        # max_lon = 0

        # return ((min_lon, min_lat), (max_lon, max_lat))


iu = InatUtils(photo_dir="in_photos", gpx_dir="in_gpx")

print()
