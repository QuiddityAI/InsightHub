from flask import Flask, request, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

# ------
import time

import torch
from transformers import AutoTokenizer, AutoModel

import csv
from pathlib import Path
import time
import uuid
import json

import weaviate
import numpy as np


weaviate_server_url = "http://localhost:8080"
item_class_name = "Paper"

weaviate_client = weaviate.Client(
    url = weaviate_server_url,
    # using anonymous connection, no auth needed
    # auth_client_secret=weaviate.AuthApiKey(api_key="YOUR-WEAVIATE-API-KEY"),
)


# from https://github.com/berenslab/pubmed-landscape/blob/main/pubmed_landscape_src/data.py

@torch.no_grad()
def generate_embeddings(abstracts, tokenizer, model, device):
    """Generate embeddings using BERT-based model.
    Code from Luca Schmidt.

    Parameters
    ----------
    abstracts : list
        Abstract texts.
    tokenizer : transformers.models.bert.tokenization_bert_fast.BertTokenizerFast
        Tokenizer.
    model : transformers.models.bert.modeling_bert.BertModel
        BERT-based model.
    device : str, {"cuda", "cpu"}
        "cuda" if torch.cuda.is_available() else "cpu".

    Returns
    -------
    embedding_cls : ndarray
        [CLS] tokens of the abstracts.
    embedding_sep : ndarray
        [SEP] tokens of the abstracts.
    embedding_av : ndarray
        Average of tokens of the abstracts.
    """
    # preprocess the input
    print("create tokenizer...")
    inputs = tokenizer(
        abstracts,
        padding=True,
        truncation=True,
        return_tensors="pt",
        max_length=512,
    ).to(device)

    # inference
    print("run model...")
    begin = time.time()
    outputs = model(**inputs)[0].cpu().detach()
    end = time.time()
    print(f"Time: {end - begin:.2f} sec")

    embedding_av = torch.mean(outputs, [0, 1]).numpy()
    embedding_sep = outputs[:, -1, :].numpy()
    embedding_cls = outputs[:, 0, :].numpy()


    return embedding_cls, embedding_sep, embedding_av


# from https://github.com/berenslab/pubmed-landscape/blob/main/scripts/02-ls-data-obtain-BERT-embeddings.ipynb

# specifying model
checkpoint = "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"

tokenizer = AutoTokenizer.from_pretrained(checkpoint)
model = AutoModel.from_pretrained(checkpoint)
device = 'cpu'
model = model.to(device)

# ------



@app.route('/')
def index():
    return '<h1>Hello!</h1>'


@app.route('/api/query', methods=['POST'])
def query():
    data = request.json
    query = data.get("query")
    if not query:
        return jsonify([])

    _, embedding, _ = generate_embeddings(query, tokenizer, model, device)

    response = (
        weaviate_client.query
        .get("Paper", ["title", "journal"])
        # .with_near_vector({
        #     "vector": embedding
        # })
        .with_hybrid(
            query = query,
            vector = embedding[0]
        )
        .with_limit(10)
        .with_additional(["distance", "score", "explainScore"]).do()
    )

    result = response["data"]["Get"]["Paper"]
    return jsonify(result)


@app.route('/api/map', methods=['POST'])
def map_html():
    data = request.json
    query = data.get("query")
    if not query:
        return jsonify([])

    _, embedding, _ = generate_embeddings(query, tokenizer, model, device)

    response = (
        weaviate_client.query
        .get("Paper", ["title"])
        .with_near_vector({
            "vector": embedding
        })
        .with_limit(600)
        .with_additional(["id", "distance"]).do()
    )
    elements = response["data"]["Get"]["Paper"]

    vectors = []
    titles = []
    distances = []

    for e in elements:
        d = weaviate_client.data_object.get_by_id(
            uuid=e["_additional"]["id"],
            class_name='Paper',
            with_vector=True
        )
        vectors.append(d["vector"])
        distances.append(e["_additional"]["distance"])
        titles.append(e["title"])

    from sklearn.manifold import TSNE
    import plotly.express as px

    features = np.asarray(vectors)
    print(features.shape)

    tsne = TSNE(n_components=2, random_state=0)
    projections = tsne.fit_transform(features)
    x = [(projections[i][0], projections[i][1], titles[i]) for i in range(len(projections))]

    fig = px.scatter(
        x, x=0, y=1,
        text=titles,
        color=distances
    )
    fig.for_each_trace(lambda t: t.update(texttemplate="-", textposition='top center'))
    html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    js = html.split('<script type="text/javascript">')[2]
    js = js.replace("</script>", "").replace("</div>", "")
    return jsonify({"html": html, "js": js})


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='55123', debug=True)
