import time
import logging

import torch
import transformers
from transformers import AutoTokenizer, AutoModel
import numpy as np


bert_models = {
    "BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext": "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext",  # https://github.com/berenslab/pubmed-landscape/blob/main/scripts/02-ls-data-obtain-BERT-embeddings.ipynb
    "scibert_scivocab_uncased": "allenai/scibert_scivocab_uncased",  # https://github.com/allenai/scibert/
    "matscibert": "m3rg-iitd/matscibert",  # https://github.com/M3RG-IITD/MatSciBERT
}

# TODO: test S-PubMedBERT (PubMedBERT fine tuned on MSMARCO for sentence similarity)

bert_embedding_strategies = ["cls_token", "sep_token", "average_all_tokens"]


# cache of last used model:
current_checkpoint = ""
tokenizer = None
model = None


def get_bert_embeddings(texts, model_name, embedding_strategy):
    global tokenizer, model, current_checkpoint
    device = "cuda"
    checkpoint = bert_models[model_name]
    if current_checkpoint != checkpoint:
        tokenizer = AutoTokenizer.from_pretrained(checkpoint)
        model = AutoModel.from_pretrained(checkpoint)
        model.eval()
        try:
            model = model.to(device)
        except RuntimeError as e:
            logging.error(e)
            logging.warning("Using GPU didn't work, trying it now on the CPU...")
            device = "cpu"
            model = model.to(device)
        current_checkpoint = checkpoint
    assert tokenizer is not None
    assert model is not None

    embedding_cls, embedding_sep, embedding_av = generate_embeddings(texts, tokenizer, model, device)

    if embedding_strategy == "cls_token":
        embeddings = embedding_cls
    elif embedding_strategy == "sep_token":
        embeddings = embedding_sep
    elif embedding_strategy == "average_all_tokens":
        embeddings = embedding_av
    else:
        # default is average_all_tokens
        embeddings = embedding_av

    return embeddings.tolist()


# from https://github.com/berenslab/pubmed-landscape/blob/main/pubmed_landscape_src/data.py


@torch.no_grad()
def generate_embeddings(
    texts: str | list[str], tokenizer: transformers.PreTrainedTokenizerBase, model: transformers.BertModel, device: str
):
    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        return_tensors="pt",
        max_length=512,
    ).to(device)

    begin = time.time()
    outputs = model(**inputs)[0].cpu().detach()  # [0] means to get the last hidden layer
    end = time.time()
    print(f"Time per element: {(end - begin) / len(texts) * 1000:.0f} ms")

    # changed by Tim: get average per text, not over all texts:
    # more information on the meaning of the outputs here: https://stackoverflow.com/a/70812558
    embedding_av: np.ndarray = torch.mean(outputs, 1).numpy()
    embedding_sep: np.ndarray = outputs[:, -1, :].numpy()
    embedding_cls: np.ndarray = outputs[:, 0, :].numpy()

    return embedding_cls, embedding_sep, embedding_av


def test_embedding():
    global tokenizer, model, current_checkpoint
    # checkpoint = bert_models["BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"]
    checkpoint = bert_models["scibert_scivocab_uncased"]
    device = "cuda"
    tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    model = AutoModel.from_pretrained(checkpoint)
    model = model.to(device)

    text1 = "This is a sentence. This is another sentence."
    text2 = "This is a different sentence. This is another very different sentence."
    texts = [text1, text2]

    embedding_cls, embedding_sep, embedding_av = generate_embeddings(text1, tokenizer, model, device)
    print("Single text 1:")
    print("embedding_cls.shape, embedding_sep.shape, embedding_av.shape")
    print(embedding_cls.shape, embedding_sep.shape, embedding_av.shape)

    embedding_cls, embedding_sep, embedding_av = generate_embeddings(text2, tokenizer, model, device)
    print("Single text 2:")
    print("embedding_cls.shape, embedding_sep.shape, embedding_av.shape")
    print(embedding_cls.shape, embedding_sep.shape, embedding_av.shape)

    embedding_cls, embedding_sep, embedding_av = generate_embeddings(texts, tokenizer, model, device)
    print("Batch of texts:")
    print("embedding_cls.shape, embedding_sep.shape, embedding_av.shape")
    print(embedding_cls.shape, embedding_sep.shape, embedding_av.shape)

    embeddings_single_item = generate_embeddings(texts[:1], tokenizer, model, device)
    embeddings_batch = generate_embeddings(texts, tokenizer, model, device)
    print(
        f"Single and batch are the same: {all(np.abs(embeddings_single_item[0][0] - embeddings_batch[0][0])) < 0.001}"
    )
    print(
        f"Single and batch are the same: {all(np.abs(embeddings_single_item[1][0] - embeddings_batch[1][0])) < 0.001}"
    )
    print(
        f"Single and batch are the same: {all(np.abs(embeddings_single_item[2][0] - embeddings_batch[2][0])) < 0.001}"
    )

    batch_size = 64  # batch size could be even larger with 12 GB GPU, but this is already fast

    t1 = time.time()
    embeddings = generate_embeddings(texts[:1] * batch_size, tokenizer, model, device)
    print(f"Duration per image (batch of {batch_size}): {(time.time() - t1) / float(batch_size) * 1000:.2f} ms")


if __name__ == "__main__":
    test_embedding()
