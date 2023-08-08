import time
import logging

from flask import Flask, request, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

import torch
from transformers import AutoTokenizer, AutoModel

models = {
    "BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext": "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext",  # https://github.com/berenslab/pubmed-landscape/blob/main/scripts/02-ls-data-obtain-BERT-embeddings.ipynb
    "scibert_scivocab_uncased": "allenai/scibert_scivocab_uncased",  # https://github.com/allenai/scibert/
    "matscibert": "m3rg-iitd/matscibert",  # https://github.com/M3RG-IITD/MatSciBERT
}

embedding_strategies = ["cls_token", "sep_token", "average_all_tokens"]

current_checkpoint = ""
tokenizer = None
model = None
device = 'cuda'  # "cuda" if torch.cuda.is_available() else "cpu"


@app.route('/api/models', methods=['GET'])
def get_models():
    return jsonify(models.keys())


@app.route('/api/embedding_strategies', methods=['GET'])
def get_embedding_strategies():
    return jsonify(embedding_strategies)


@app.route('/api/embedding', methods=['POST'])
def get_embedding():
    global tokenizer, model, current_checkpoint
    data = request.json
    text = data.get("text")  # might also be a list of texts (a batch)
    model_name = data.get("model")
    embedding_strategy = data.get("embedding_strategy")
    if not text or model_name not in models or embedding_strategy not in embedding_strategies:
        logging.warning("Text, model or embedding_strategy are missing")
        print(model_name, embedding_strategy)
        return jsonify({})

    checkpoint = models[model_name]
    if current_checkpoint != checkpoint:
        tokenizer = AutoTokenizer.from_pretrained(checkpoint)
        model = AutoModel.from_pretrained(checkpoint)
        model = model.to(device)
        current_checkpoint = checkpoint

    embedding_cls, embedding_sep, embedding_av = generate_embeddings(text, tokenizer, model, device)

    if embedding_strategy == "cls_token":
        embedding = embedding_cls
    elif embedding_strategy == "sep_token":
        embedding = embedding_sep
    elif embedding_strategy == "average_all_tokens":
        embedding = embedding_av
    else:
        # default is average_all_tokens
        embedding = embedding_av

    return jsonify({"embedding": embedding.tolist()})


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
        Average of tokens of each abstract.
    """
    # preprocess the input
    inputs = tokenizer(
        abstracts,
        padding=True,
        truncation=True,
        return_tensors="pt",
        max_length=512,
    ).to(device)

    # inference
    begin = time.time()
    outputs = model(**inputs)[0].cpu().detach()
    end = time.time()
    print(f"Time: {(end - begin) * 1000:.0f} ms")

    # changed by Tim: get average per text, not over all texts:
    embedding_av = torch.mean(outputs, 1).numpy()
    embedding_sep = outputs[:, -1, :].numpy()
    embedding_cls = outputs[:, 0, :].numpy()

    # more information on the meaning of the outputs here: https://stackoverflow.com/a/70812558

    return embedding_cls, embedding_sep, embedding_av


def test_embedding():
    global tokenizer, model, current_checkpoint
    checkpoint = models["BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"]
    tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    model = AutoModel.from_pretrained(checkpoint)
    model = model.to(device)

    text1 = "This is a sentence. This is another sentence."
    text2 = "This is a different sentence. This is another very different sentence."
    texts = [text1, text2]

    embedding_cls, embedding_sep, embedding_av = generate_embeddings_pubmed(text1, tokenizer, model, device)
    print("Single text 1:")
    print("embedding_cls.shape, embedding_sep.shape, embedding_av.shape")
    print(embedding_cls.shape, embedding_sep.shape, embedding_av.shape)

    embedding_cls, embedding_sep, embedding_av = generate_embeddings_pubmed(text2, tokenizer, model, device)
    print("Single text 2:")
    print("embedding_cls.shape, embedding_sep.shape, embedding_av.shape")
    print(embedding_cls.shape, embedding_sep.shape, embedding_av.shape)

    embedding_cls, embedding_sep, embedding_av = generate_embeddings_pubmed(texts, tokenizer, model, device)
    print("Batch of texts:")
    print("embedding_cls.shape, embedding_sep.shape, embedding_av.shape")
    print(embedding_cls.shape, embedding_sep.shape, embedding_av.shape)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='55180', debug=True, use_reloader=False)
    #test_embedding()
