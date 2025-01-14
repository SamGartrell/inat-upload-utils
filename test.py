# %%
from inatutils import InatUtils
import pandas as pd
import datetime
import os

# iu = InatUtils(log_level="DEBUG")
print("importing")
s = datetime.datetime.now()
iu = InatUtils()
pic = iu.photos[0]
iu.georeference()

print(f"everything loaded, georeferenced in {datetime.datetime.now() - s}")
print(
    f"{len(iu.photos)} photos ({sum([os.path.getsize(p.path) for p in iu.photos]) / 1024 / 1024:.2f} MB total)"
)
print(f"{len(iu.waypoints)} waypoints")
os.path.getsize(iu.photos[0].path)

print()
# %%
