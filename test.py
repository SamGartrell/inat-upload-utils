# %%
from inatutils import InatUtils
import pandas as pd
import datetime
import os

# iu = InatUtils(log_level="DEBUG")
print("importing")
s = datetime.datetime.now()
iu = InatUtils()

iu.sort()

for p in iu.photos:
    # iu.identify_image(p)
    iu.save(indices=iu.photos.index(p))
print()
# %%
