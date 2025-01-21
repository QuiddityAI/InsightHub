import logging

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug import serving

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

from utils.dotdict import DotDict
from utils.batching import run_in_batches

from logic.bert_models import bert_models, bert_embedding_strategies, get_bert_embeddings
from logic.sentence_transformer_models import get_sentence_transformer_embeddings
from logic.clip_models import get_clip_text_embeddings, get_clip_image_embeddings

from PIL import ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True


# exclude polling endpoints from logs (see https://stackoverflow.com/a/57413338):
parent_log_request = serving.WSGIRequestHandler.log_request

paths_excluded_from_logging = ["/health"]


def log_request(self, *args, **kwargs):
    if self.path in paths_excluded_from_logging or self.path.startswith("/data_backend/local_image/"):
        return

    parent_log_request(self, *args, **kwargs)


serving.WSGIRequestHandler.log_request = log_request


@app.route("/health", methods=["GET"])
def health():
    return "", 200


@app.route("/api/embedding/bert/models", methods=["GET"])
def get_models():
    return jsonify(bert_models.keys())


@app.route("/api/embedding/bert/embedding_strategies", methods=["GET"])
def get_embedding_strategies():
    return jsonify(bert_embedding_strategies)


@app.route("/api/embedding/bert", methods=["POST"])
def get_embedding_bert():
    assert request.json is not None
    params = DotDict(request.json)
    # using a batch size of 1 for now because there is a bug with larger batches leading to different results
    # see https://github.com/huggingface/transformers/issues/2401
    embeddings = run_in_batches(
        params.texts, 1, lambda texts: get_bert_embeddings(texts, params.model_name, params.embedding_strategy)
    )
    return jsonify({"embeddings": embeddings})


@app.route("/api/embedding/sentence_transformer", methods=["POST"])
def get_embedding_sentence_transformer():
    assert request.json is not None
    params = DotDict(request.json)
    embeddings = run_in_batches(
        params.texts,
        8,
        lambda texts: get_sentence_transformer_embeddings(texts, params.model_name, params.prefix).tolist(),
    )
    return jsonify({"embeddings": embeddings})


@app.route("/api/embedding/clip/text", methods=["POST"])
def get_clip_text_embedding_endpoint():
    assert request.json is not None
    params = DotDict(request.json)
    embeddings = run_in_batches(
        params.texts, 8, lambda texts: get_clip_text_embeddings(texts, params.model_name).tolist()
    )
    return jsonify({"embeddings": embeddings})


@app.route("/api/embedding/clip/image", methods=["POST"])
def get_clip_image_embedding_endpoint():
    assert request.json is not None
    params = DotDict(request.json)
    embeddings = run_in_batches(
        params.image_paths, 8, lambda image_paths: get_clip_image_embeddings(image_paths, params.model_name).tolist()
    )
    return jsonify({"embeddings": embeddings})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=55180, debug=True, use_reloader=False)
