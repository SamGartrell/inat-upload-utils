import csv
import os

# Taxon name    | Date observed     | Description | Place name      | Latitude  | Longitude | Tags      | Geoprivacy
# text          | YYYY-MM-DD HH:MM  |        text |         text    | dd.dddd   | dd.dddd   | tag,tag   | obscured
# NO WAY TO BATCH UPLOAD PHOTOS :(


def format_timestamp_for_csv():
    pass


def gather_photos(photo_dir):
    photos = []
    for pic in os.listdir(photo_dir):
        photos.append(os.path.join(photo_dir, pic))
    return photos
