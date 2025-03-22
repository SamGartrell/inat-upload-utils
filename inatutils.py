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
import datetime
import pandas as pd
import numpy as np

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
        token: str = "eyJhbGciOiJIUzUxMiJ9.eyJ1c2VyX2lkIjo4ODA4MjMzLCJleHAiOjE3Mzg2MDY1MTF9.cb9_iyrGhuaUk89BwcB6xmf73qeqIRUMVBrEXrSxMx6vaF7gU7jYS2fmQXZwXrP5XUPJgpKYOXEhdwovnNyyvQ",
        trusted_genera: list = [],
        log_level="INFO",
        min_score: int | float = 70,
        common_ancestor_ok: bool = True,
        timestamp_fmt: str = "%Y:%m:%d %H:%M:%S",
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
        self.waypoints = pd.DataFrame(columns=["x", "y", "z", "t", "geo_src"])
        self.time_range = None
        self.bbox = None
        self.trusted_genera = trusted_genera
        self.time_delta_threshold = time_delta_threshold
        self.common_ancestor_ok = common_ancestor_ok
        self.min_score = min_score
        self.photo_dir = photo_dir
        self.photo_dir_valid = False
        self.gpx_dir = gpx_dir
        self.gpx_dir_valid = False
        self.output_dir = output_dir
        self.token = token
        self.offset = gmt_offset
        self.camera_make = camera_make
        self.camera_model = camera_model
        self.timestamp_fmt = timestamp_fmt
        self.photo_formats = ["jpg", "cr2", "jpeg", "heic"]
        self.log_level = log_level
        logging.basicConfig(
            format="%(levelname)s:%(module)s:%(funcName)s:%(lineno)d:%(message)s"
        )
        logging.getLogger().setLevel(self.log_level)

        if photo_dir:
            self.photo_dir_valid = self.validate_contents(photo_dir, self.photo_formats)
            self.photos = self.load_images(photo_dir=photo_dir)

        if gpx_dir:
            self.gpx_dir_valid = self.validate_contents(gpx_dir, ["gpx"])
            self.get_waypoints(gpx_dir=gpx_dir)
            self.match_waypoints()
            self.georeference()

        if self.photos:
            self.sort()

        if token:
            self.token = token
        else:
            self.token = tools.refresh_token()

    # region images
    def validate_contents(self, dir: str, expected_files: list[str]):
        expected_file_present = False
        expected_files.append(".gitignore")
        expected_files = [ef.lower().strip(".") for ef in expected_files]

        try:
            contents = os.listdir(dir)

            if contents:
                for file in contents:
                    file_ext = file.lower().split(".")[-1]
                    if not file_ext in expected_files:
                        logging.warning(f"unexpected file type in {dir}: {file}")
                    elif file_ext != "gitignore":
                        expected_file_present = True

        except Exception as e:
            logging.error(e)

        return expected_file_present

    class Img:
        def __init__(self, path: str, offset: int):
            self.id = str(uuid.uuid4())
            self.name = os.path.split(path)[1]
            self.folder = os.path.split(path)[0]
            self.path = path
            self.size = os.path.getsize(self.path)
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

            # if self.datetime and not isinstance(self.datetime, datetime.datetime):
            #     self.datetime = datetime.datetime(self.datetime)
            #     # TODO: enforce which format here?

        def show(self, size: tuple[int] = None):
            if size:
                self.raster.thumbnail(size)
            self.raster.show()

    def load_images(self, photo_dir, overwrite=False) -> list[Img]:
        if len(self.photos) > 0 and not overwrite:
            logging.warning(
                f"aborting load images; images have already been loaded. If you want to overwrite existing images, use this function with overwrite=True."
            )
            return
        if not os.path.exists(photo_dir):
            logging.error(f"specified photo dir doesn't exist: {photo_dir}")
            return
        if not self.validate_contents(photo_dir, self.photo_formats):
            logging.error(f"no photos found in specified photo dir {photo_dir}")
            return

        out_images = []

        for pic in tools.list_photo_names(directory=photo_dir):
            if pic.startswith("."):
                continue
            if not pic.lower().endswith(tuple(self.photo_formats)):
                logging.warning(f"skipping {pic} due to unexpected file type")
                continue
            path = os.path.join(os.getcwd(), photo_dir, pic)
            photo = self.Img(path=path, offset=self.offset)

            out_images.append(photo)
        return out_images

    def sort(
        self,
        by: str = "datetime_obj",
    ) -> None:
        photosdf = self.photos_df()
        sorted = photosdf.sort_values(by=by, ascending=True)
        self.photos = list(sorted["img_obj"])
        return self.photos

    # region spatial
    def get_waypoints(self, gpx_dir) -> None:
        """gets waypoints from GPX files in a directory and adds them to the waypoints dataframe.
        NOTE: timestamps are in utc
        """
        if not gpx_dir and self.gpx_dir != None:
            gpx_dir = self.gpx_dir
        elif not gpx_dir and not self.gpx_dir:
            logging.error("cannot georeference; no GPX dir was provided")
            return

        if not self.validate_contents(gpx_dir, ["gpx"]):
            logging.error(
                f"cannot georeference; no valid GPX files present in GPX dir {gpx_dir}"
            )
            return

        gpx_files = [
            os.path.join(gpx_dir, f)
            for f in tools.list_gpx_files(directory=gpx_dir)
            if f != ".gitignore"
        ]
        if not gpx_files:
            logging.warning(f"no gpx files found in {gpx_dir}")
            return

        for gpx in gpx_files:
            if ".gitignore" in gpx:
                continue
            waypoints = tools.parse_gpx(gpx)
            self.waypoints = pd.concat(
                [self.waypoints, pd.DataFrame(waypoints)], ignore_index=True
            )

        logging.debug(
            f"{len(self.waypoints)} waypoints created from {len(gpx_files)} gpx files"
        )

    def photos_df(self, get_ts_obj=True, keep_img_obj=True) -> pd.DataFrame:
        if len(self.photos) == 0:
            logging.error(f"no photos loaded")
            return pd.DataFrame()
        pdf = pd.DataFrame([p.__dict__ for p in self.photos])
        if get_ts_obj:
            pdf["datetime_obj"] = pd.to_datetime(
                pdf["datetime"], format=self.timestamp_fmt
            )
        if keep_img_obj:
            pdf["img_obj"] = pdf["id"].map({p.id: p for p in self.photos})
        return pdf

    def match_waypoints(self):
        photosdf = self.photos_df()
        if self.waypoints.empty:
            logging.warning(
                f"no photos will be georeferenced because there are no waypoints."
            )
            return
        elif photosdf.empty:
            logging.warning(
                f"there are no photos to georeference! Load some with InatUtils.load_images()."
            )
            return
        photosdf = self.photos_df()
        self.waypoints["t_obj"] = pd.to_datetime(
            self.waypoints["t"], format=self.timestamp_fmt
        )
        nearest_waypoints = pd.merge_asof(
            photosdf.sort_values("datetime_obj"),
            self.waypoints.sort_values("t_obj"),
            left_on="datetime_obj",
            right_on="t_obj",
            direction="nearest",
        )
        nearest_waypoints["delta"] = (
            nearest_waypoints["datetime_obj"] - nearest_waypoints["t_obj"]
        ).abs().dt.total_seconds() / 60

        for p in self.photos:
            if not p.datetime:
                logging.debug(f"{p.name} has no timestamp and cannot be georeferenced")
                continue
            logging.debug(f"locating {p.name}...")

            closest_waypoint = nearest_waypoints.loc[
                nearest_waypoints["id"] == p.id
            ].iloc[0]
            p.geo = closest_waypoint[["x", "y", "z", "t", "geo_src", "delta"]].to_dict()

            ref = tools.get_reference_direction(lat=p.geo["y"], lon=p.geo["x"])
            p.geo["ref"] = ref

            for k, v in p.geo.items():
                if isinstance(v, datetime.datetime):
                    p.geo[k] = v.strftime(self.timestamp_fmt)
                elif pd.isna(v):
                    p.geo[k] = 0

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
        elif isinstance(photo, self.Img):
            p = photo

        if not p:
            logging.error(f"no photo found for input {p}")
            return
        try:
            exif = p.exif
            geo = p.geo
            ref = p.geo.get("ref", None)
        except Exception as e:
            logging.error(e)

        if exif and geo and ref:
            gps_value = {
                0: b"\x02\x03\x00\x00",  # GPSVersionID
                1: ref["lat"],  # GPSLatitudeRef
                2: tools.get_dms_from_decimal(abs(p.geo["y"])),  # GPSLatitude
                3: ref["lon"],  # GPSLongitudeRef
                4: tools.get_dms_from_decimal(abs(p.geo["x"])),  # GPSLongitude
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

    def identify_image(self, photo: Img | str | int, min_score=None, overwrite=None):
        if not min_score:
            min_score = self.min_score
        if isinstance(photo, int):
            try:
                p = self.photos[photo]
            except Exception as e:
                logging.error(
                    f"no photo at index {photo}; check the length of self.photos and try again"
                )
        elif isinstance(photo, str):
            p = next((x for x in self.photos if x.name == photo), None)
            if not p:
                logging.error(f"no photo found for input {photo}")
                return
        elif isinstance(photo, self.Img):
            p = photo

        if isinstance(p, self.Img):
            try:
                if p.identified and not overwrite:
                    logging.warning(
                        f"image {p.name} is already identified; use this function with overwrite=True to overwrite existing ID"
                    )
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
            except Exception as e:
                logging.error(e)
        else:
            logging.error(f"photo yielded {p} which is type {type(p)}, not type Img")

    def update_identified_percent(self):
        self.identified_percent = (
            100 * (sum(1 for p in self.photos if p.identified) / len(self.photos))
            if self.photos
            else 0.0
        )

    def identify(self, min_score=None, overwrite=True):
        prior_identification = None
        if not min_score:
            min_score = self.min_score
        for p in self.photos:
            try:
                if p.identified and not overwrite:
                    logging.debug(f"skipping {p.name} because already identified")
                    continue
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
                elif identification == 0 and prior_identification == 0:
                    logging.warning("token appears to have expired--aborting.")
                    break
                prior_identification = identification
            except Exception as e:
                logging.error(e)
                self.update_identified_percent()
                break

            # todo: get and implement AppID here to automatically refresh token
            self.update_identified_percent()

    def update_identified_percent(self):
        self.identified_percent = (
            100 * (sum(1 for p in self.photos if p.identified) / len(self.photos))
            if self.photos
            else 0.0
        )

    # region exports/uploads
    def save(
        self,
        outdata: Img | int | list = None,
        # title: str = None,
        filter: str = None,
        output_dir: str = None,
        out_fmt: str = "JPEG",
        max_timedelta: int = 5,
        min_timedelta: int = 0,
        # overwrite: bool = True,
        # max_time: str|datetime.datetime = None,
        # min_time: str|datetime.datetime = None,
        # bounds: tuple = None,
    ):
        exports = []
        if not output_dir:
            output_dir = self.output_dir

        if isinstance(outdata, list):
            for i in outdata:
                if isinstance(i, int):
                    exports.append(self.photos[i])
                elif isinstance(i, self.Img):
                    exports.append(i)

        elif isinstance(outdata, self.Img):
            exports.append(outdata)
        elif isinstance(outdata, int):
            exports.append(self.photos[outdata])
        elif not outdata:
            exports = self.photos
        else:
            logging.error(
                f"expected outdata as Int, Img, or List, got {type(outdata)}; skipping"
            )
            return
        if filter:
            if filter == "georeferenced":
                exports = [p for p in self.photos if p.georeferenced]
            elif filter == "identified":
                exports = [p for p in self.photos if p.identified]
            elif filter == "unidentified":
                exports = [p for p in self.photos if not p.identified]
            elif filter == "ungeoreferenced":
                exports = [p for p in self.photos if not p.georeferenced]
            else:
                logging.error(f"filter {filter} not recognized")
        elif not filter and outdata == None and not exports:
            exports = self.photos

        if max_timedelta:
            exports = [
                p
                for p in exports
                if p.geo.get("delta", True) and p.geo.get("delta") < max_timedelta
            ]
        logging.info(f"exporting {len(exports)} photos to {output_dir}")

        for p in exports:
            try:
                # outname = p.name.strip(p.name[p.name.index(".") :])
                outname = ""
                if not out_fmt:
                    out_fmt = p.format

                if p.geo["t"]:
                    outname += f"{p.geo['t']}".replace(" ", "-").replace(":", "")

                if p.identified:
                    if p.identity["rank"] == "species":
                        outname += f"_{p.identity['name']}"
                    else:
                        outname += f"_{p.identity['rank']}_{p.identity['name']}"

                if p.georeferenced:
                    outname += "_geo"

                if p.format:
                    outname += f".{out_fmt}"

                p.raster.save(
                    os.path.join(output_dir, outname), format=out_fmt, exif=p.exif
                )
                res = self.Img(path=os.path.join(output_dir, outname), offset=p.offset)
                res.src = p.id
                p.outputs.append(res)
            except Exception as e:
                logging.error(e)

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
