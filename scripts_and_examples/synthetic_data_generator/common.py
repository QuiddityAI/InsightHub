import json
import os

import dspy
from llmonkey.llms import Google_Gemini_Flash_1_5

Model = Google_Gemini_Flash_1_5
model = Model()


BASE_FOLDER = "scripts_and_examples/generated_data"
FILE_NAME = "stored_data.json"
STORED_DATA_PATH = os.path.join(BASE_FOLDER, FILE_NAME)
stored_data = {}


def save_stored_data():
    with open(STORED_DATA_PATH, "w") as f:
        json.dump(stored_data, f, indent=2)


def set_stored_data(key, value):
    stored_data[key] = value
    save_stored_data()


def load_stored_data():
    global stored_data
    if not os.path.exists(STORED_DATA_PATH):
        with open(STORED_DATA_PATH, "w") as f:
            json.dump({}, f)
    with open(STORED_DATA_PATH, "r") as f:
        stored_data = json.load(f)


load_stored_data()


class CompanyContextSignature(dspy.Signature):
    """\
    Given the user prompt, generate the following information about a fictive company in this order
    (make up the information based on the user prompt):
    - the companys industry
    - the companys offering on one sentence
    - what makes the company unique
    - the name of the company
    - the rough number of employees
    - the companys location
    - the companys main competitors (name three company names)
    - the name of the CEO
    - the name of the board members
    - the companys main products or services (three if not mentioned otherwise)
    - the companys main projects:
        - like building a new plant, planning a new product, restructuring
        - generate three projects, each with a short description, codename, and status
    """

    user_input: str = dspy.InputField()
    # target_language: str = dspy.InputField(desc="The desired output language for the output")
    company_context: str = dspy.OutputField(desc="The generated company context")


context_predictor = dspy.Predict(CompanyContextSignature)


def generate_company(id: str, user_input: str, target_language: str) -> str:
    if id in stored_data:
        return stored_data[id]

    with dspy.context(lm=dspy.LM(**model.to_litellm())):
        company_context = context_predictor(user_input=user_input, target_language=target_language).company_context

    set_stored_data(id, company_context)

    return company_context
