from id import *
import time

token = refresh_token()
photo_dir = os.path.join(os.getcwd(), "in_photos")

logging.basicConfig(
    format="%(levelname)s:%(module)s:%(funcName)s:%(lineno)d:%(message)s"
)
logging.getLogger().setLevel(logging.INFO)

for photo in os.listdir(photo_dir):
    logging.info(f"identifying {photo}...")
    ph_path = os.path.join(photo_dir, photo)
    cv_results = get_cv_ids(ph_path, token=token)

    res = interpret_results(cv_results, confidence_threshold=70)
    time.sleep(1)  # to keep from throttling the API since dont have formal app ID yet
