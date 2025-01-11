#######################################
# Sam Gartrell
# 20250109
# automated image ID
# NOTE: inaturalist App guidelines mandate that "content must be generated with real human involvement or oversight"
# This app therefore only creates a CSV of image IDs designed for manual review before uploading to iNaturalist
#######################################
import sys
import os
import json
import requests
import PIL
import datetime
import logging


def refresh_token(
    manual_token="eyJhbGciOiJIUzUxMiJ9.eyJ1c2VyX2lkIjo4ODA4MjMzLCJleHAiOjE3MzY2NjE5NDF9.X2_XcDe5fyzPbfF6e93jsT_jZzERZJqV1ppldR8Nga8pL1TwCIZYiaXQJeVLFGXEdSvhntfgCVqZ9xtSoR_7Ig",
):
    logging.info(f"getting token...")
    # TODO: need an oauth app setup, request one here: https://www.inaturalist.org/oauth/app_owner_application
    # in interim, tokens can be generated by manually visting the endpoint in browser after authenticating; tokens last 2 months or something crazy
    try:
        res = requests.get(
            "https://www.inaturalist.org/users/api_token?f=json",
            timeout=1,
        )
        if res and res.ok:
            token = res.json().get("api_token", ValueError("Failed to get token"))
            return token
    except Exception as e:
        logging.error(e)
        logging.warning("returning manual_token")
        return manual_token


def get_cv_ids(image_path, token=None):
    """sends an image to the computer vision model, returns the response json

    Args:
        image_path (str): the location of the image.
        token (str, optional): a token for the API. Defaults to None.

    Returns:
        _type_: _description_
    """
    if not token:
        token = refresh_token()
    with open(image_path, "rb") as image_file:
        files = {"image": image_file}
        headers = {"Authorization": token}
        res = requests.post(
            "https://api.inaturalist.org/v1/computervision/score_image",
            files=files,
            headers=headers,
            timeout=9999,
        )
    return json.loads(res.text)


def interpret_results(
    res: object, confidence_threshold: int = 75, common_ancestor_ok: bool = True
):
    if (
        res.get("results")
        and isinstance(res.get("results"), list)
        and len(res.get("results")) > 0
    ):
        # if there's a sufficient score, return that suggestion; IDs sorted by best-worst score
        results = res.get("results")
        if results[0].get("combined_score") >= confidence_threshold:
            score = results[0].get("combined_score")
            if results[0].get("taxon").get("name"):
                result = results[0].get("taxon")
                logging.info(
                    f"acceptable ID found within confidence threshold {confidence_threshold}:\n\tscore: {score}\n\trank: {result.get('rank')}\n\tname: {result.get('name')}"
                )
                return {
                    "name": results[0].get("taxon", {}).get("name", None),
                    "rank": results[0].get("taxon", {}).get("rank", None),
                    "score": results[0].get("combined_score"),
                }
        elif results[0].get("combined_score") < confidence_threshold:
            score = results[0].get("combined_score")
            if results[0].get("taxon").get("name"):
                result = results[0].get("taxon")
                logging.info(
                    f"no acceptable ID found within confidence threshold {confidence_threshold}:\n\tbest score: {score}\n\trank: {result.get('rank')}\n\tname: {result.get('name')}"
                )
            if not common_ancestor_ok:
                logging.warning(f"use of common ancestor not permitted; ID failed")
                return None
            if res.get("common_ancestor", False) and common_ancestor_ok:
                logging.info(
                    f"resorting to common ancestor of all {len(res['results'])} results:\n\trank: {res.get('common_ancestor').get('taxon').get('rank')}\n\tname: {res.get('common_ancestor').get('taxon').get('name')}"
                )
                return {
                    "name": res.get("common_ancestor", {}).get("name"),
                    "rank": res.get("common_ancestor", {}).get("rank"),
                    "score": None,
                }
            else:
                logging.warning(f"no common ancestor available; ID failed")
                return None
    # else,
    logging.error(f"ID request failed\n\nres:\n\n{res}")
    return None
