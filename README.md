# 🐛 iNaturalist Upload Utilities 🍄
Sam Gartrell || iNat profile: [mothpith](https://www.inaturalist.org/observations?place_id=any&user_id=mothpith&verifiable=any) || Email: [gartrell.sam.s@gmail.com](mailto:gartrell.sam.s@gmail.com)

This repository contains tools to assist iNaturalist users with georeferencing photos from digital cameras, and provides preliminary ID using the iNaturalist computer vision model. 

*NOTE: iNaturalist guidelines mandate that "content must be generated with real human involvement or oversight." Please use and modify this project responsibly!*

*Review the [iNaturalist Policy on Machine Generated Content](https://www.inaturalist.org/pages/machine_generated_content) for clarification.*

## Usage
For example use cases, check out the [`examples notebook`](https://github.com/SamGartrell/inat-upload-utils/blob/main/examples.ipynb), or the `demo.py` file for each of the modules in [`legacy/`](https://github.com/SamGartrell/inat-upload-utils/tree/main/legacy).

### Try it yourself!
For example use cases, check out the [`examples notebook`](https://github.com/SamGartrell/inat-upload-utils/blob/main/examples.ipynb), or the `demo.py` file for each of the modules in [`utils/`](https://github.com/SamGartrell/inat-upload-utils/tree/main/utils).

### Workflow
The general workflow for this tool is to record a GPX track with a mobile app like [Strava](https://www.strava.com) or [Avenza](https://store.avenza.com/pages/app-features) while you're out taking timestamped pictures on your digital camera. When ready to upload your photos, 
- put the GPX track in [`in_gpx/`]() 
- put the photos (JPG, CR2, and HEIC formats tested) in [`in_photos/`]()
- run `inatutils.py` to create an `InatUtils` instance, or run `legacy/geo/demo.py`
- find your georeferenced photos in [`out_photos/`]()
- optionally, you can identify these images calling `InatUtils.identify()` or running `legacy/suggest/demo.py`
- the export part is still under construction

*NOTE: if you can't get the tool to recognize metadata of images taken on iPhones (HEIC/JPG), try transfering them to your computer with google photos as per [this article](https://support.google.com/photos/thread/12597272/heic-being-downloaded-as-jpg-loses-all-meta-data?hl=en).* 

## Collaboration
To get started with this repository, clone it with
```bash
git clone https://github.com/SamGartrell/inat-upload-utils.git
cd inat-upload-utils
```

and build the conda environment with
```bash
conda env create -f environment.yml
conda activate inat-img-utils
```
Most of the logic for the `InatUtils` class methods originated from the standalone functions in the `legacy/` directory. I recommend using and developing against the class implementation for better organization and performance.

Please create issues and/or pull requests (I like feature branches referencing issues in comments/prs) as you see fit, and feel free to reach out with any questions or collaboration requests!

## External Resources
- [exiftool](https://exiftool.org/)
- [Strava](https://www.strava.com)
- [Avenza](https://store.avenza.com/pages/app-features)
- [iNaturalist Developers Page](https://www.inaturalist.org/pages/developers)
- [iNaturalist contribution guide](https://github.com/inaturalist/inaturalist/blob/main/CONTRIBUTING.md)
