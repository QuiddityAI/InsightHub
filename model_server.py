import time

from flask import Flask, request, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

import torch
from transformers import AutoTokenizer, AutoModel


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
device = 'cuda'
model = model.to(device)


@app.route('/api/embedding/pubmedbert', methods=['POST'])
def query():
    data = request.json
    query = data.get("query")
    if not query:
        return jsonify([])

    _, embedding, _ = generate_embeddings(query, tokenizer, model, device)

    return jsonify({"embedding": embedding.tolist()})


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='55180', debug=True, use_reloader=False)
