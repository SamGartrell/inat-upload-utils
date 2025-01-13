# %%
import json
import PIL.Image
import requests
import os
import sys
import uuid
from pprint import pprint
import logging
import PIL

# import oauthlib

# local
from utils import tools

class InatUtils:
    # region props
    def __init__(
        self,
        photo_dir: str = "in_photos",
        gpx_dir: str = "in_gpx",
        output_dir: str = "out_photos",
        gmt_offset: int = -8,
        token: str = None,
        trusted_genera: list = [],
        log_level="INFO",
        min_score: int | float = 75,
        common_ancestor_ok: bool = True,
        timestamp_fmt: str = "%Y-%m-%d %H:%M:%S",
        time_delta_threshold=None,
        camera_make: str = None,
        camera_model: str = None,
    ):
        """
        Initialize the InatUtils class.
        Args:
            photo_dir (str): Directory containing photos to be processed. Default is "in_photos".
            gpx_dir (str): Directory containing GPX files to georeference with. Default is "in_gpx".
            output_dir (str): Directory to save processed photos. Default is "out_photos".
            gmt_offset (int): GMT offset, representing the timezone in which the photos were taken, for timestamp conversion. Default is -8 (LA/Vancouver).
            token (str, optional): Authentication token for the iNaturalist computer vision service. Default is None.
            trusted_genera (list): List of trusted genera for identification. Default is an empty list.
            log_level (str): Logging level. Default is "INFO".
            min_score (int | float): Minimum score for organism identification. Default is 75.
            common_ancestor_ok (bool): Decides wether the common ancestor (typically Genus or Family rank) of all low-scoring IDs can be used as an identification, in the absence of a well-scored ID. Default is True.
            timestamp_fmt (str): Format for photo timestamps. Default is "%Y-%m-%d %H:%M:%S".
            time_delta_threshold (optional): Threshold for time delta. Default is None.
        """
        self.photos = []
        self.georeferenced_percent = 0.0
        self.identified_percent = 0.0
        self.waypoints = []  # TODO: refactor waypoints to be numpy array
        self.time_range = None
        self.bbox = None
        self.trusted_genera = trusted_genera
        self.time_delta_threshold = time_delta_threshold
        self.common_ancestor_ok = common_ancestor_ok
        self.min_score = min_score
        self.photo_dir = photo_dir
        self.gpx_dir = gpx_dir
        self.output_dir = output_dir
        self.token = token
        self.offset = gmt_offset
        self.camera_make = camera_make
        self.camera_model = camera_model
        self.timestamp_fmt = timestamp_fmt
        self.log_level = log_level
        logging.basicConfig(
            format="%(levelname)s:%(module)s:%(funcName)s:%(lineno)d:%(message)s"
        )
        logging.getLogger().setLevel(self.log_level)

        if photo_dir:
            self.photos = self.load_images(photo_dir=photo_dir)

        if gpx_dir:
            self.get_waypoints(gpx_dir=gpx_dir)
            self.match_waypoints()

        if token:
            self.token = token
        else:
            self.token = tools.refresh_token()

    # region images
    class Img:
        def __init__(self, path: str, offset: int):
            self.id = str(uuid.uuid4())
            self.name = os.path.split(path)[1]
            self.folder = os.path.split(path)[0]
            self.path = path
            self.format = os.path.splitext(self.path)[1]
            self.offset = offset
            self.datetime = tools.get_exif_timestamp(
                self.name, directory=self.folder, offset=self.offset
            )
            self.geo = dict()
            self.identity = dict()
            self.georeferenced = False  # meaning in Exif, not in geo property
            self.identified = False
            self.outputs = []
            self.src = None
            self.raster = PIL.Image.open(self.path)
            self.exif = self.raster.getexif()

    def load_images(self, photo_dir) -> list[Img]:
        out_images = []
        for pic in tools.list_photo_names(directory=photo_dir):
            if pic.startswith("."):
                continue
            path = os.path.join(os.getcwd(), photo_dir, pic)
            photo = InatUtils.Img(path=path, offset=self.offset)

            out_images.append(photo)
        return out_images

    # region spatial
    def get_waypoints(self, gpx_dir) -> None:
        if not gpx_dir and self.gpx_dir != None:
            gpx_dir = self.gpx_dir
        elif not gpx_dir and not self.gpx_dir:
            logging.error("cannot get waypoints; no GPX dir was provided")
        gpx_files = [
            os.path.join(gpx_dir, f)
            for f in tools.list_gpx_files(directory=gpx_dir)
            if not f.startswith(".")
        ]

        if not gpx_files:
            logging.warning(f"no gpx files found in {gpx_dir}")
            return None

        for gpx in gpx_files:
            self.waypoints.extend(tools.parse_gpx(gpx))

        logging.debug(
            f"{len(self.waypoints)} waypoints created from {len(gpx_files)} gpx files"
        )

    def match_waypoints(self):
        for p in self.photos:
            if not p.datetime:
                logging.debug(f"{p.name} has no timestamp and cannot be georeferenced")
                continue
            logging.debug(f"locating {p.name}...")
            georef = tools.find_closest_waypoint(self.waypoints, p.datetime)
            if not georef:
                logging.warning(f"waypoint matching failed for {p.name}")
                continue
            p.geo = georef

            logging.debug(
                f"waypoint matching succeeded with timedelta {p.geo['delta']}"
            )

            ref = tools.get_reference_direction(lat=p.geo["y"], lon=p.geo["x"])
            p.geo["ref"] = ref

    def georeference_image(self, photo: Img | str | int):
        p = None
        if isinstance(photo, int):
            try:
                p = self.photos[photo]
            except Exception as e:
                print(
                    f"no photo at index {photo}; check the length of self.photos and try again"
                )
        elif isinstance(photo, str):
            p = next((x for x in self.photos if x.name == photo), None)
        elif isinstance(photo, InatUtils.Img):
            p = photo

        if not p:
            logging.error(f"no photo found for input {p}")
            return
        exif = p.exif
        geo = p.geo
        ref = p.geo["ref"]

        gps_value = {
            0: b"\x02\x03\x00\x00",  # GPSVersionID
            1: ref["lat"],  # GPSLatitudeRef
            2: tools.get_dms_from_decimal(p.geo["y"]),  # GPSLatitude
            3: ref["lon"],  # GPSLongitudeRef
            4: tools.get_dms_from_decimal(p.geo["x"]),  # GPSLongitude
            5: b"\x00",  # GPSAltitudeRef
            6: p.geo.get("z", 0.0),  # GPSAltitude
            9: "A",  # GPSStatus
            18: "WGS-84\x00",  # GPSMapDatum
        }

        p.exif[34853] = gps_value

        if self.camera_make:
            p.exif[271] = self.camera_make

        if self.camera_model:
            p.exif[272] = self.camera_model

        p.georeferenced = True
        self.update_georeferenced_percent()

    def update_georeferenced_percent(self):
        self.georeferenced_percent = (
            100 * (sum(1 for p in self.photos if p.georeferenced) / len(self.photos))
            if self.photos
            else 0.0
        )

    def georeference(self):
        for p in self.photos:
            try:
                self.georeference_image(p)
            except Exception as e:
                logging.error(e)

        self.georeferenced_percent = (
            100 * (sum(1 for p in self.photos if p.georeferenced) / len(self.photos))
            if self.photos
            else 0.0
        )

    # region id
    def identify(
        self,
        min_score=None,
    ):
        if not min_score:
            min_score = self.min_score
        for p in self.photos:
            res = tools.get_cv_ids(p.path, token=self.token)
            identification = tools.interpret_results(
                res,
                confidence_threshold=min_score,
                common_ancestor_ok=self.common_ancestor_ok,
            )
            if identification:
                p.identity = identification
                p.identified = True
                if p.outputs:  # if has child images, they're also IDd now
                    for o in p.outputs:
                        o.identity = identification
                        o.identified = True

        self.update_identified_percent()

    def update_identified_percent(self):
        self.identified_percent = (
            100 * (sum(1 for p in self.photos if p.identified) / len(self.photos))
            if self.photos
            else 0.0
        )

    # region exports/uploads
    def dump_jpg(self):
        # TODO: implement filters here for time delta, trusted genera, and whatever else
        # Implementation for dumping photos as JPG
        pass

    def dump_csv(self):
        # TODO: implement filters here for time delta, trusted genera, and whatever else
        # Implementation for dumping data to CSV
        pass

    def _get_bbox(self):
        pass
        # min_lat = 999999999
        # min_lon = 999999999
        # max_lat = 0
        # max_lon = 0

        # return ((min_lon, min_lat), (max_lon, max_lat))

# For debugging
# iu = InatUtils(log_level="DEBUG")
# iu.identify()
# print()

# %%
