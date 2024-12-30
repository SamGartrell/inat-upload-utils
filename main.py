from utils import *

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

    # cardinal reference for use in creating DMS coordinates
    ref = get_reference_direction(lat=georef["y"], lon=georef["x"])

    print("modifying exif data...")
    photo = modify_exif_position(photo, georef, ref)

    print("modification complete")
    print(f"image written to {photo[1]}")

    photo[0].show()
