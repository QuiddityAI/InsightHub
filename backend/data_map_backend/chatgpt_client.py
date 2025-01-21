import os
import json
import logging

from openai import OpenAI, BadRequestError


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
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
temp = float(os.getenv("LLM_TEMPERATURE", 0.0))


class OPENAI_MODELS:
    GPT3_5 = "gpt-3.5-turbo"
    GPT4 = "gpt-4"
    GPT4_TURBO = "gpt-4-turbo"
    GPT4_O = "gpt-4o"


def get_chatgpt_response(question: str, language: str, model: str = OPENAI_MODELS.GPT4_O) -> str:
    logging.info(f"Sending question to ChatGPT: {question}")
    system_prompt = "You are a helpful assistant"
    system_prompt_de = "Du bist ein hilfreicher Assistent"
    response = client.chat.completions.create(
        model=model,
        temperature=temp,
        messages=[
            {"role": "system", "content": system_prompt_de if language == "de" else system_prompt},
            {"role": "user", "content": question},
        ],
    )

    response_text = response.choices[0].message.content
    assert response_text, "ChatGPT response is empty"
    return response_text


def get_chatgpt_response_using_history(history, model: str = OPENAI_MODELS.GPT4_O) -> str:
    logging.info(f"Sending prompt history to ChatGPT: {history[-1]}")
    response = client.chat.completions.create(model=model, temperature=temp, messages=history)

    response_text = response.choices[0].message.content
    assert response_text, "ChatGPT response is empty"
    return response_text


def multi_step_chatgpt(prompts, system_prompt, model: str = OPENAI_MODELS.GPT4_O):
    history = []
    result = {}
    history.append({"role": "system", "content": system_prompt})
    for result_name, prompt in prompts:
        history.append({"role": "user", "content": prompt})
        response = get_chatgpt_response_using_history(history, model)
        print(response)
        history.append({"role": "assistant", "content": response})
        result[result_name] = response
    return result
