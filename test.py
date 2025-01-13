# %%
from inatutils import InatUtils

iu = InatUtils(log_level="DEBUG")
pic = iu.photos[0]
iu.georeference_image(pic)
# %%
