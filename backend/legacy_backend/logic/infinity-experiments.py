import base64

import litellm
from numpy import dot
from numpy.linalg import norm


def file_to_base64(file, modality="image"):
    with open(file, "rb") as f:
        content = f.read()
    base64_encoded = base64.b64encode(content).decode("utf-8")
    mimetype = f"{modality}/{file.split('.')[-1]}"
    return f"data:{mimetype};base64,{base64_encoded}"


resp = litellm.embedding(
    "openai/intfloat/multilingual-e5-large-instruct",
    input=["Who is Albert Einstein"],
    api_base="http://localhost:7997",
    api_key="12",
)

print(resp)


resp = litellm.rerank(
    "infinity/mixedbread-ai/mxbai-rerank-xsmall-v1",
    query="How much is the fish",
    documents=[
        "fish costs 3.22$",
        "London is the capital of great britain where you can have Fish and chips",
        "water is important for life because fishes live in there",
    ],
    api_base="http://localhost:7997",
    api_key="12",
)

print(resp)


resp = litellm.embedding(
    "openai/jinaai/jina-clip-v1",
    input=["http://images.cocodataset.org/val2017/000000039769.jpg"],
    extra_body={"modality": "image"},
    api_base="http://localhost:7997",
    api_key="12",
)

# OR
# resp = litellm.embedding("openai/jinaai/jina-clip-v1",
#                   input=[file_to_base64("~/1736114585430.jpg")],
#                   extra_body={ "modality": "image" },
#                   api_base="http://localhost:7997", api_key="12")


img_emb = resp.data[0]["embedding"]


resp = litellm.embedding(
    "openai/jinaai/jina-clip-v1",
    input=["Two cats"],
    extra_body={"modality": "text"},
    api_base="http://localhost:7997",
    api_key="12",
)

text_emb = resp.data[0]["embedding"]


def cos_sim(a, b):
    return dot(a, b) / (norm(a) * norm(b))


print(cos_sim(img_emb, text_emb))  # 0.213454231162523
