import logging

import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug import serving

try:
    from cuml.manifold.umap import UMAP

    logging.warning("Using GPU-based umap")
except ImportError:
    logging.warning("cuml library not found or issue with GPU, falling back to CPU-based umap")
    from umap import UMAP

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes


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


@app.route("/api/umap", methods=["POST"])
def umap_endpoint():
    data = request.get_json()
    vectors = np.array(data["vectors"])
    reduced_dimensions = data["reduced_dimensions"]
    projection_parameters = data["projection_parameters"]

    projections = do_umap(vectors, reduced_dimensions, projection_parameters)

    return jsonify({"projections": projections.tolist()})


def do_umap(
    vectors: np.ndarray,
    reduced_dimensions: int,
    projection_parameters: dict,
) -> np.ndarray:
    reducer = UMAP(
        n_components=reduced_dimensions,
        random_state=99,  # type: ignore
        min_dist=projection_parameters.get("min_dist", 0.17),
        n_epochs=projection_parameters.get("n_epochs", 500),
        n_neighbors=projection_parameters.get("n_neighbors", 15),
        metric=projection_parameters.get("metric", "euclidean"),
    )
    try:
        projections = reducer.fit_transform(vectors)
        assert isinstance(projections, np.ndarray)
    except (TypeError, ValueError) as e:
        # might happend when there are too few points
        logging.warning(f"UMAP failed: {e}")
        projections = np.zeros((len(vectors), reduced_dimensions))
    return projections


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=55180, debug=True, use_reloader=False)
