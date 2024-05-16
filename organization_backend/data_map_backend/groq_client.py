import os
import logging

from ratelimit import limits, sleep_and_retry
from groq import Groq


def load_env_file():
    with open("../.env", "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.strip().split("=")
            os.environ[key] = value


load_env_file()
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

class GROQ_MODELS:
    LLAMA_3_8B = "llama3-8b-8192"
    LLAMA_3_70B = "llama3-70b-8192"
    MIXTRAL_8_7B = "mixtral-8x7b-32768"
    GEMMA_7B = "gemma-7b-it"


@sleep_and_retry
@limits(calls=29, period=60)
def get_groq_response_using_history(history, model: str = GROQ_MODELS.LLAMA_3_70B) -> str:
    #logging.info(f"Sending prompt history to Groq: {history[-1]}")
    response = client.chat.completions.create(
        model=model,
        messages=history
    )
    #logging.warning(f"Groq response: {response}")

    response_text = response.choices[0].message.content
    if response_text == "":
        logging.warning("Groq response is empty")
        logging.warning(f"Groq response: {response}")
    return response_text
