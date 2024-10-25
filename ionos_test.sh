
export IONOS_API_KEY=eyJ0eXAiOiJKV1QiLCJraWQiOiI3MDdiMWRjMy00YTRmLTQyNzUtYTA5NS01NDAyNjAyOTdjNjIiLCJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJpb25vc2Nsb3VkIiwiaWF0IjoxNzI5NTM5NzAwLCJjbGllbnQiOiJVU0VSIiwiaWRlbnRpdHkiOnsicHJpdmlsZWdlcyI6WyJEQVRBX0NFTlRFUl9DUkVBVEUiLCJTTkFQU0hPVF9DUkVBVEUiLCJJUF9CTE9DS19SRVNFUlZFIiwiTUFOQUdFX0RBVEFQTEFURk9STSIsIkFDQ0VTU19BQ1RJVklUWV9MT0ciLCJQQ0NfQ1JFQVRFIiwiQUNDRVNTX1MzX09CSkVDVF9TVE9SQUdFIiwiQkFDS1VQX1VOSVRfQ1JFQVRFIiwiQ1JFQVRFX0lOVEVSTkVUX0FDQ0VTUyIsIks4U19DTFVTVEVSX0NSRUFURSIsIkZMT1dfTE9HX0NSRUFURSIsIkFDQ0VTU19BTkRfTUFOQUdFX01PTklUT1JJTkciLCJBQ0NFU1NfQU5EX01BTkFHRV9DRVJUSUZJQ0FURVMiLCJBQ0NFU1NfQU5EX01BTkFHRV9MT0dHSU5HIiwiTUFOQUdFX0RCQUFTIiwiQUNDRVNTX0FORF9NQU5BR0VfRE5TIiwiTUFOQUdFX1JFR0lTVFJZIiwiQUNDRVNTX0FORF9NQU5BR0VfQ0ROIiwiQUNDRVNTX0FORF9NQU5BR0VfVlBOIiwiQUNDRVNTX0FORF9NQU5BR0VfQVBJX0dBVEVXQVkiLCJBQ0NFU1NfQU5EX01BTkFHRV9OR1MiLCJBQ0NFU1NfQU5EX01BTkFHRV9LQUFTIiwiQUNDRVNTX0FORF9NQU5BR0VfTkVUV09SS19GSUxFX1NUT1JBR0UiLCJBQ0NFU1NfQU5EX01BTkFHRV9BSV9NT0RFTF9IVUIiLCJBQ0NFU1NfQU5EX01BTkFHRV9JQU1fUkVTT1VSQ0VTIl0sInV1aWQiOiJjMWYzYmIzYS01NzZhLTQ0NDktYjk1OS01NWFhNTViYzQ0Y2YiLCJyZXNlbGxlcklkIjoxLCJyZWdEb21haW4iOiJpb25vcy5kZSIsInJvbGUiOiJvd25lciIsImNvbnRyYWN0TnVtYmVyIjozNDUzMDgxNiwiaXNQYXJlbnQiOmZhbHNlfSwiZXhwIjoxNzYxMDc1NzAwfQ.ewMCg33FWaHAvQCVmcNf0d_yiTh-k0VA91UGV5NQnt_xH9Gi67UA8pyABmMMJznA42FqjEahdjjNSHgqUP85rDjA3hkGzjTQby9fSgBvQjRoNwt0knHOHkuuSYcwvYxDHPMhLOrYHwvsNzYbsBe53UDtF7V0Ya-ET8uu9KPwszCm9rT8bZuES6Nu6iPIOhAqN0Fquir36LnQXkp23dQpPbTyyNbvdMrhrNFy8ZUbuOPudJdjCvj567bAtbbOswVDae5JqJ9tSKojo87bGcaHYek8w51SdgarWE7YxQWpqd5clb02oiH8sxgSa76PY9Yw3hsDeTTTDb06PBXRMs203A

# use curl to get the model list, use the API key as the bearer token
curl -X GET "https://openai.inference.de-txl.ionos.com/v1/models" \
  -H "Authorization: Bearer $IONOS_API_KEY" | python3 -m json.tool

  {
    "data": [
        {
            "id": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "meta-llama/CodeLlama-13b-Instruct-hf",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "stabilityai/stable-diffusion-xl-base-1.0",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "meta-llama/Meta-Llama-3.1-405B-Instruct-FP8",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "mistralai/Mistral-7B-Instruct-v0.3",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        }
    ],
    "object": "list"
}
