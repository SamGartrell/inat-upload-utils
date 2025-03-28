# %%
from inatutils import InatUtils
# import pandas as pd
import datetime
import numpy as np
import time

print("importing")
while True:
    iu = InatUtils(log_level="INFO")

    iu.sort()

    print("iu initialized and sorted as")
    print(iu.__dict__)

    # print("id ing")
    # iu.identify()

    # print("id done")
    iu.output_dir = "C:/Users/SamGartrell/Desktop/inat"

    print(iu.photos[235].__dict__)
    img_offset = input("how many hours should be added to each photo's datetime? ")
    subtract = False
    if img_offset:
        if img_offset.startswith("-"):
            subtract = False
        if img_offset.strip("-").isdigit():
            img_offset = int(img_offset)
            for p in iu.photos:
                if subtract:
                    p.datetime = (
                        datetime.datetime.strptime(p.datetime, "%Y:%m:%d %H:%M:%S")
                        - datetime.timedelta(hours=img_offset)
                    ).strftime("%Y:%m:%d %H:%M:%S")
                else:
                    p.datetime = (
                        datetime.datetime.strptime(p.datetime, "%Y:%m:%d %H:%M:%S")
                        + datetime.timedelta(hours=img_offset)
                    ).strftime("%Y:%m:%d %H:%M:%S")
            print("updated photos. re-matching...")
            print("    getting waypoints...")
            iu.get_waypoints(gpx_dir=iu.gpx_dir)
            print("    matching waypoints...")
            iu.match_waypoints()
            print("    georeferencing images...")
            iu.georeference()
            iu.sort(by="timedelta", ascending=False)

    else:
        print("no offset applied")

    # time.sleep(6)
    print("saving")

    mean_timeDelta = np.mean([p.geo.get("delta", None) for p in iu.photos])
    cont = input(
        f"continue? (last time value was {img_offset}, which gave mean timedelta {mean_timeDelta}) "
    )
    if not cont:
        break
# %%
