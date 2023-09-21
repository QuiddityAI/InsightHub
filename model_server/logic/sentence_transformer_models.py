import time
from sentence_transformers import SentenceTransformer


last_used_model: str | None = None
model = None

sentence_transformer_models = [
    'intfloat/e5-base-v2',  # 768 dimensions
    'intfloat/e5-large-v2',  # 1024 dimensions
    'intfloat/multilingual-e5-base',  # 768 dimensions
    'allenai/specter2',  # ? dimensions, needs different code!  # TODO
]


def get_sentence_transformer_embeddings(texts, model_name, prefix: str = ""):
    global last_used_model, model
    if model_name != last_used_model:
        model = SentenceTransformer(model_name)
        model.eval()
        model.to('cuda')
        last_used_model = model_name
    assert model is not None

    if model_name in ['intfloat/e5-base-v2', 'intfloat/e5-large-v2', 'intfloat/multilingual-e5-base']:
        prefix = prefix or "query:"
        # alternative: "passage: " for documents meant for retrieval
        texts = [prefix + " " + t for t in texts]

    embeddings = model.encode(texts)
    return embeddings


def test_embedding():
    import numpy as np

    texts = ["a very intersting text", "just three words"]
    embeddings = get_sentence_transformer_embeddings(texts, 'intfloat/e5-base-v2')
    print(embeddings.shape)

    embeddings_single_item = get_sentence_transformer_embeddings(texts[:1], 'intfloat/e5-base-v2')
    embeddings_batch = get_sentence_transformer_embeddings(texts, 'intfloat/e5-base-v2')
    print(f"Single and batch are the same: {all(np.abs(embeddings_single_item[0] - embeddings_batch[0])) < 0.001}")

    batch_size = 32  # batch size could be even larger with 12 GB GPU, but this is already fast

    t1 = time.time()
    embeddings = get_sentence_transformer_embeddings(texts[:1] * batch_size, 'intfloat/e5-base-v2')
    print(f"Duration per image (batch of {batch_size}): {(time.time() - t1) / float(batch_size) * 1000:.2f} ms")


if __name__ == "__main__":
    test_embedding()
