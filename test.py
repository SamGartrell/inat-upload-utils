# %%
from inatutils import InatUtils

print("importing")
iu = InatUtils()


# iu.sort()

print("iu initialized and sorted")

# print("id ing")
# iu.identify()

# print("id done")
for p in iu.photos:
    if not p.identified:
        p.name = p.id
iu.output_dir = "C:/Users/SamGartrell/Desktop/inat"
print(iu.photos[235].__dict__)
print("saving")
iu.save()
# %%
