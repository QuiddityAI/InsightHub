from hashlib import md5
import os
import logging
from typing import Callable

import PIL
from PIL import Image
from PIL import ImageFile
import requests

from utils.helpers import do_in_parallel

ImageFile.LOAD_TRUNCATED_IMAGES = True

THUMBNAIL_CACHE_DIR = "/data/quiddity_data/thumbnails/"
THUMBNAIL_ATLAS_DIR = "/data/quiddity_data/thumbnail_atlas/"
THUMBNAIL_SIZE = 256


def generate_thumbnail_atlas(atlas_filename: str, thumbnail_uris: list[str | None],
                           sprite_size: int, on_success: Callable,
                           atlas_total_width: int = 4096,):
    if not os.path.exists(THUMBNAIL_CACHE_DIR):
        os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)
    if not os.path.exists(THUMBNAIL_ATLAS_DIR):
        os.makedirs(THUMBNAIL_ATLAS_DIR, exist_ok=True)
    max_images = pow(atlas_total_width // sprite_size, 2)
    imagesPerLine = (atlas_total_width / sprite_size)
    atlas = Image.new("RGBA", (atlas_total_width, atlas_total_width), color=(0, 0, 0, 0))

    def _load_image(thumbnail_uri):
        if not thumbnail_uri:
            return None
        elif thumbnail_uri.startswith("http"):
            url_hash = md5(thumbnail_uri.encode()).hexdigest()
            thumbnail_path = os.path.join(THUMBNAIL_CACHE_DIR, url_hash + ".jpg")
            if not os.path.exists(thumbnail_path):
                try:
                    image = Image.open(requests.get(thumbnail_uri, stream=True).raw)
                    image.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE))
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                except (PIL.UnidentifiedImageError, OSError) as e:
                    #logging.debug(f"Image can't be loaded (UnidentifiedImageError): {thumbnail_uri}, {e}")
                    return None
                try:
                    image.save(thumbnail_path, quality=80)
                except OSError as e:
                    logging.warning(f"Downloaded image can't be saved, error: {e}, URI: {thumbnail_uri}")
                    return None
            else:
                try:
                    image = Image.open(thumbnail_path)
                except (PIL.UnidentifiedImageError, OSError) as e:
                    #logging.debug(f"Image can't be loaded (UnidentifiedImageError): {thumbnail_uri}, {e}")
                    return None
        elif os.path.exists(thumbnail_uri):
            try:
                image = Image.open(thumbnail_uri)
            except (PIL.UnidentifiedImageError, OSError) as e:
                #logging.debug(f"Image can't be loaded (UnidentifiedImageError): {thumbnail_uri}, {e}")
                return None
        else:
            # image URI exists but can't be found
            logging.warning(f"Image can't be loaded: {thumbnail_uri}")
            return None
        image.thumbnail((sprite_size, sprite_size))
        return image

    images = do_in_parallel(_load_image, thumbnail_uris[:max_images])

    for i, image in enumerate(images):
        if not image:
            continue
        posRow: int = int(i / imagesPerLine)
        posCol: int = int(i % imagesPerLine)
        atlas.paste(image, (posCol * sprite_size + ((sprite_size - image.width) // 2),
                            posRow * sprite_size + ((sprite_size - image.height) // 2)))
        image.close()
    atlas.save(atlas_filename, quality=80)
    logging.warning(f"Thumbnail atlas sucessfully created: {atlas_filename}")
    on_success()