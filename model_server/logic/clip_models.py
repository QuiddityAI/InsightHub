import logging
import os
import time

import torch
from PIL import Image, UnidentifiedImageError
from transformers import AutoProcessor, AutoTokenizer, CLIPModel

clip_models = [
    "openai/clip-vit-base-patch32",  # 768 dimensions
    "patrickjohncyh/fashion-clip",  # 768 dimensions
    "laion/CLIP-ViT-H-14-laion2B-s32B-b79K",  # 1024 dimensions
]

# see model comparison here: https://huggingface.co/laion/CLIP-convnext_xxlarge-laion2B-s34B-b82K-augreg

last_used_model: str | None = None
model = None
tokenizer = None
processor = None

compute_device = "cuda" if torch.cuda.is_available() else "cpu"


def get_clip_text_embeddings(texts, model_name):
    global last_used_model, model, tokenizer, processor
    if last_used_model != model_name:
        model = CLIPModel.from_pretrained(model_name)
        model.eval()
        model.to(compute_device)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        processor = AutoProcessor.from_pretrained(model_name)
        last_used_model = model_name
    assert model is not None and tokenizer is not None

    inputs = tokenizer(texts, padding=True, return_tensors="pt")
    inputs.to(compute_device)
    text_features = model.get_text_features(**inputs).to("cpu").detach()
    return text_features


def get_clip_image_embeddings(image_paths, model_name):
    global last_used_model, model, tokenizer, processor
    if last_used_model != model_name:
        model = CLIPModel.from_pretrained(model_name)
        model.eval()
        model.to(compute_device)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        processor = AutoProcessor.from_pretrained(model_name)
        last_used_model = model_name
    assert model is not None and processor is not None

    images = []
    missing_images = 0
    for image_path in image_paths:
        img = None
        if os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                img.draft("RGB", (224, 224))
            except (UnidentifiedImageError, OSError) as e:
                logging.warning(f"Error with image {image_path}: {e}")
        if not img:
            missing_images += 1
            logging.warning(
                f"Couldn't load image: {image_path} ({missing_images} missing of {len(image_paths)} in total)"
            )
            img = Image.new("RGB", (224, 224))
        images.append(img)

    inputs = processor(images=images, return_tensors="pt")
    inputs.to(compute_device)
    image_features = model.get_image_features(**inputs).to("cpu").detach()
    return image_features


def test_embedding():
    import numpy as np

    model_name = "laion/CLIP-ViT-H-14-laion2B-s32B-b79K"
    # model_name = "patrickjohncyh/fashion-clip"
    print(model_name)
    texts = ["a very intersting text", "just three words"]
    embeddings = get_clip_text_embeddings(texts, model_name)
    print(embeddings.shape)

    embeddings_single_item = get_clip_text_embeddings(texts[:1], model_name)
    embeddings_batch = get_clip_text_embeddings(texts, model_name)
    print(f"Single and batch are the same: {all(np.abs(embeddings_single_item[0] - embeddings_batch[0])) < 0.001}")

    image_paths = [
        "/home/tim/visual-data-map/frontend/favicon/android-chrome-512x512.png",
        "/home/tim/visual-data-map/frontend/favicon/android-chrome-192x192.png",
    ]
    embeddings = get_clip_image_embeddings(image_paths, model_name)
    print(embeddings.shape)

    embeddings_single_item = get_clip_image_embeddings(image_paths[:1], model_name)
    embeddings_batch = get_clip_image_embeddings(image_paths, model_name)
    print(f"Single and batch are the same: {all(np.abs(embeddings_single_item[0] - embeddings_batch[0])) < 0.001}")

    batch_size = 16  # max batch size for 12 GB GPU

    t1 = time.time()
    embeddings = get_clip_text_embeddings(texts[:1] * batch_size, model_name)
    print(f"Duration per text (batch of {batch_size}): {(time.time() - t1) / float(batch_size) * 1000:.2f} ms")

    batch_size = 8  # max batch size for 12 GB GPU

    t1 = time.time()
    embeddings = get_clip_image_embeddings(image_paths[:1] * batch_size, model_name)
    print(f"Duration per image (batch of {batch_size}): {(time.time() - t1) / float(batch_size) * 1000:.2f} ms")


if __name__ == "__main__":
    test_embedding()
