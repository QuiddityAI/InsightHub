import requests
import json

# r1 = requests.get('https://api.semanticscholar.org/datasets/v1/release').json()
# print(r1[-3:])
#['2023-08-29', '2023-09-05', '2023-09-12']

# r2 = requests.get('https://api.semanticscholar.org/datasets/v1/release/latest').json()
# print(json.dumps(r2, indent=2))
# #2023-03-28

# print(json.dumps(r2['datasets'][0], indent=2))
# # {
# #     "name": "abstracts",
# #     "description": "Paper abstract text, where available. 100M records in 30 1.8GB files.",
# #     "README": "Semantic Scholar Academic Graph Datasets The "abstracts" dataset provides..."
# # }

r3 = requests.get('https://api.semanticscholar.org/datasets/v1/release/latest/dataset/papers').json()
print(json.dumps(r3, indent=2))
# # {
# #   "name": "abstracts",
# #   "description": "Paper abstract text, where available. 100M records in 30 1.8GB files.",
# #   "README": "Semantic Scholar Academic Graph Datasets The "abstracts" dataset provides...",
# #   "files": [
# #     "https://ai2-s2ag.s3.amazonaws.com/dev/staging/2023-03-28/abstracts/20230331_0..."
# #   ]
# # }