import logging
import os
import json
import base64
import datetime
from typing import Callable

import cv2
import numpy as np

from ingest.schemas import AiFileProcessingInput, AiFileProcessingOutput
from ingest.logic.common import UPLOADED_FILES_FOLDER, store_thumbnail
from legacy_backend.logic.model_client import get_clip_image_embeddings



def process_video(result: AiFileProcessingOutput, input_item: AiFileProcessingInput):
    logging.warning(f"Processing video: {input_item.file_name}")
    video_path = f'{UPLOADED_FILES_FOLDER}/{input_item.uploaded_file_path}'

    def generate_thumbnail(video_path: str) -> str:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        middle_frame = total_frames // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
        success, frame = cap.read()
        if not success:
            raise ValueError("Could not read video file")

        cap.release()

        _, buffer = cv2.imencode('.png', frame)
        thumbnail_base64 = base64.b64encode(buffer).decode('utf-8')
        return thumbnail_base64

    thumbnail_base64 = generate_thumbnail(video_path)
    thumbnail_path = store_thumbnail(base64.b64decode(thumbnail_base64), input_item.uploaded_file_path)
    result.thumbnail_path = thumbnail_path

    temp_frame_dir = f'{UPLOADED_FILES_FOLDER}/{input_item.uploaded_file_path}.frames'
    os.makedirs(temp_frame_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_paths = []
    frame_every_n_seconds = 2
    frame_interval = cap.get(cv2.CAP_PROP_FPS) * frame_every_n_seconds

    for frame_num in range(0, total_frames, int(frame_interval)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        success, frame = cap.read()
        if not success:
            logging.error(f"Could not read frame {frame_num} from video {input_item.file_name}")
            continue

        frame_path = f'{temp_frame_dir}/{frame_num}.png'
        cv2.imwrite(frame_path, frame)
        frame_paths.append(frame_path)

    cap.release()

    embedding_parts = []
    batch_size = 2
    for i in range(0, len(frame_paths), batch_size):
        embeddings_part = get_clip_image_embeddings(frame_paths[i:i + batch_size], "laion/CLIP-ViT-H-14-laion2B-s32B-b79K")
        embedding_parts.append(embeddings_part)
    embeddings = np.concatenate(embedding_parts, axis=0)
    result.video_frame_embeddings = embeddings.tolist()

    chunks = []
    for i, frame_path in enumerate(frame_paths):
        pos_seconds = i * frame_every_n_seconds
        time_h_m_s = str(datetime.timedelta(seconds=pos_seconds))
        chunks.append({
            "text": f"Frame {i} at {time_h_m_s}",
        })
        os.remove(frame_path)
    result.video_frame_chunks = chunks

    os.rmdir(temp_frame_dir)
    return result
