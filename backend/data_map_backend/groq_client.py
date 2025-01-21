from collections import defaultdict
import os
import logging
import time

from ratelimit import RateLimitException, limits, sleep_and_retry
from groq import Groq, RateLimitError


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

temp = float(os.getenv("LLM_TEMPERATURE", 0.0))


class GROQ_MODELS:
    LLAMA_3_8B = "llama3-8b-8192"
    LLAMA_3_70B = "llama3-70b-8192"
    MIXTRAL_8_7B = "mixtral-8x7b-32768"
    GEMMA_7B = "gemma-7b-it"


timestamps_and_num_tokens_per_model = defaultdict(dict)
max_tokens_per_minute_per_model = {
    GROQ_MODELS.LLAMA_3_8B: 30000,
    GROQ_MODELS.LLAMA_3_70B: 6000,
    GROQ_MODELS.MIXTRAL_8_7B: 5000,
    GROQ_MODELS.GEMMA_7B: 15000,
}


@sleep_and_retry
@limits(calls=28, period=60)
def get_groq_response_using_history(history, model: str = GROQ_MODELS.LLAMA_3_70B) -> str:
    for timestamp in timestamps_and_num_tokens_per_model[model].copy():
        if timestamp < time.time() - 60:
            del timestamps_and_num_tokens_per_model[model][timestamp]
    num_tokens = sum(timestamps_and_num_tokens_per_model[model].values())
    if num_tokens > max_tokens_per_minute_per_model[model]:
        remaining_time = max(timestamps_and_num_tokens_per_model[model].keys()) + 60 - time.time()
        logging.warning(f"Token rate limit reached for Groq model {model}. Remaining time: {remaining_time}")
        raise RateLimitException("too many calls", remaining_time)

    try:
        response = client.chat.completions.create(model=model, temperature=temp, messages=history)
    except RateLimitError as e:
        logging.warning(f"Token rate limit reached for Groq model {model}.")
        raise RateLimitException("too many calls", 30)

    # logging.warning(f"Groq response: {response}")
    # -> ChatCompletion(id='chatcmpl-f9b2d897-d792-4b8b-aa2f-518df47d4e5e',
    # choices=[
    # Choice(finish_reason='stop', index=0, logprobs=None,
    # message=ChatCompletionMessage(content='...', role='assistant',
    # function_call=None, tool_calls=None))],
    # created=1719654414, model='llama3-70b-8192', object='chat.completion',
    # system_fingerprint='fp_2f30b0b571',
    # usage=CompletionUsage(completion_tokens=23, prompt_tokens=208, total_tokens=231,
    # completion_time=0.065714286, prompt_time=0.132865694, queue_time=None, total_time=0.19857998),
    # x_groq={'id': 'req_01j1hp7wm6f6t82pbnqkmsyqtc'})

    if response.usage:
        timestamps_and_num_tokens_per_model[model][time.time()] = response.usage.total_tokens

    response_text = response.choices[0].message.content
    if not response_text or not response_text.strip():
        logging.warning("Groq response is empty")
        logging.warning(f"Groq response: {response}")
        return ""
    return response_text
