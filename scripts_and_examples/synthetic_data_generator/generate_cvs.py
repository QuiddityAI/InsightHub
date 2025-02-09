import json
import os
import pprint
import subprocess

import dspy
import json_repair
from common import BASE_FOLDER, generate_company, model, set_stored_data, stored_data
from llmonkey.llms import Google_Gemini_Flash_1_5

CV_FOLDER = os.path.join(BASE_FOLDER, "cvs_de")
if not os.path.exists(CV_FOLDER):
    os.makedirs(CV_FOLDER)


class CvListSignature(dspy.Signature):
    """\
    Given the company context and the user input, generate a list of fictive CVs sent to the company.
    The list should be a JSON array of JSON objects. The number of CVs to generate is given as an input.
    Not all CVs must match the user input, some should not fit the job description at all.
    For each CV, generate the following information in this order as fields in the object:
    - name: the name of the applicant, be creative, use different ethnicities, don't use generic names like John Doe
    - filename: the name of the file (e.g. "Firstname_lastname_CV.pdf" or "my_final_cv_w3585.docx", either pdf or docx, be creative)
    - short_description: a short description of the applicant
    - positive_aspects: a list of positive aspects of the applicant (can either be 'none' or contain up to three aspects)
    - negative_aspects: a list of negative aspects of the applicant (can either be 'none' or contain up to three aspects)
    Answer only with the JSON array, no other characters.
    """

    company_context: str = dspy.InputField()
    user_input: str = dspy.InputField()
    number_of_cvs: int = dspy.InputField()
    target_language: str = dspy.InputField(desc="The desired language for the field content")
    cv_list: str = dspy.OutputField(desc="The generated CV list as JSON array")


cv_list_predictor = dspy.Predict(CvListSignature)


def generate_cv_list(id: str, company_context: str, user_input: str, number_of_cvs: int, target_language: str) -> list:
    if id in stored_data:
        return stored_data[id]

    with dspy.context(lm=dspy.LM(**model.to_litellm())):
        cv_list_raw = cv_list_predictor(
            company_context=company_context,
            user_input=user_input,
            number_of_cvs=number_of_cvs,
            target_language=target_language,
        ).cv_list

    cv_list = json_repair.loads(cv_list_raw)
    assert isinstance(cv_list, list)

    set_stored_data(id, cv_list)

    return cv_list


class CvGeneratorSignature(dspy.Signature):
    """\
    Given the description of a candidate, generate a fictive CV as Markdown text.
    It should contain all typical sections of a CV, such as personal information, education, work experience, skills, etc.
    Be creative and make up the information based on the description.
    Also include some spelling mistakes or other issues to make it look more realistic.
    Include some kirkish aspects in the CV. Don't use generic names like John Doe or Acmecorp, generic job titles, or personal information like phone number 555-1234.
    Answer only with the Markdown text, no other characters.
    """

    name: str = dspy.InputField()
    short_description: str = dspy.InputField()
    positive_aspects: list = dspy.InputField()
    negative_aspects: list = dspy.InputField()
    target_language: str = dspy.InputField(desc="The desired language for the generated text")
    cv_markdown: str = dspy.OutputField(desc="The generated CV as Markdown text")


cv_generator_predictor = dspy.Predict(CvGeneratorSignature)


def generate_cv(
    id: str, name: str, short_description: str, positive_aspects: list, negative_aspects: list, target_language: str
) -> str:
    if id in stored_data:
        return stored_data[id]

    with dspy.context(lm=dspy.LM(**model.to_litellm())):
        cv_markdown = cv_generator_predictor(
            name=name,
            short_description=short_description,
            positive_aspects=positive_aspects,
            negative_aspects=negative_aspects,
            target_language=target_language,
        ).cv_markdown

    set_stored_data(id, cv_markdown)

    return cv_markdown


def main():
    company_context = generate_company(
        "beer_brewing_company",
        "We are a company building beer brewing machine and are currently looking for software engineers with C++ skills to redo our user interface using Qt.",
        "en",
    )
    print(company_context)

    cv_list = generate_cv_list(
        "cpp_engineer_cv_list_de2",
        company_context,
        "CVs for a position of a junior C++ software developer with Qt skills. Be creative.",
        10,
        "de",
    )
    pprint.pprint(cv_list)

    for i, cv in enumerate(cv_list):
        cv_markdown = generate_cv(
            f'beer_cv_de_{cv.get("filename", "default_filename")}',
            cv.get("name", "Unknown Name"),
            cv.get("short_description", "No description available"),
            cv.get("positive_aspects", []),
            cv.get("negative_aspects", []),
            "de",
        )
        print(cv_markdown)
        suffix = cv["filename"].split(".")[-1]  # can be pdf or docx
        path = os.path.join(CV_FOLDER, cv["filename"])
        # convert markdown to pdf / docx:
        temp_md_path = os.path.join(CV_FOLDER, "temp_cv.md")
        with open(temp_md_path, "w") as temp_md_file:
            temp_md_file.write(cv_markdown)

        subprocess.run(["pandoc", temp_md_path, "-o", path])

        # remove tmp file:
        os.remove(temp_md_path)


if __name__ == "__main__":
    main()
