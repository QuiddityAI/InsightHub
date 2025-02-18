import time

import torch
from transformers import AutoModel, AutoTokenizer

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


def run(text):
    # specifying model
    checkpoint = "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"

    print("tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    print("model...")
    model = AutoModel.from_pretrained(checkpoint)
    print("device...")
    device = "cpu"
    model = model.to(device)
    print("generate_embeddings...")
    _, embedding, _ = generate_embeddings(text, tokenizer, model, device)
    print("done")
    return embedding


if __name__ == "__main__":
    embedding = run("paper about skin cancer")
    print(embedding)
