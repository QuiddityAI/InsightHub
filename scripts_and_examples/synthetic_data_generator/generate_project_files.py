import json
import os
import pprint
import subprocess

import dspy
import json_repair
from common import BASE_FOLDER, generate_company, model, set_stored_data, stored_data
from llmonkey.llms import Google_Gemini_Flash_1_5

DATA_FOLDER = os.path.join(BASE_FOLDER, "beer_files_german")
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)


class FileTreeGeneratorSignature(dspy.Signature):
    """\
    Given the company context and the user input, generate a file tree.
    The number of files to mention is given as an input.
    The file tree should look similar to this:
    - folder
        - subfolder
            - file 1
            - file 2
        - file 3
    - file 4
    - file 5
    Be creative, don't use generic file titles like "meeting minutes.docx", rather use realistic file names with different formats.
    Use realistic or creative names for the folders.
    Answer with just the file tree structure, no other characters.
    """

    company_context: str = dspy.InputField()
    user_input: str = dspy.InputField()
    number_of_files: int = dspy.InputField()
    target_language: str = dspy.InputField(desc="The desired language for the output")
    file_tree: str = dspy.OutputField(desc="The generated file tree")


predictor = dspy.Predict(FileTreeGeneratorSignature)


def generate_tree(id: str, company_context: str, user_input: str, number_of_files: int, target_language: str) -> str:
    if id in stored_data:
        return stored_data[id]
    with dspy.context(lm=dspy.LM(**model.to_litellm())):
        file_tree = predictor(
            company_context=company_context,
            user_input=user_input,
            number_of_files=number_of_files,
            target_language=target_language,
        ).file_tree
    set_stored_data(id, file_tree)
    return file_tree


class FileListGeneratorSignature(dspy.Signature):
    """\
    Given the company context and a file tree, generate a JSON array with one JSON object for each file in the tree.
    Each object should contain the following fields:
    - full_path: the full path of the file, starting with the root folder, including the file name and extension
    - short_description: a short description of the file, include made up issues with the file, e.g. outdated, wrong format, conflicting with a different file, etc.
    Answer with just the JSON array, no other characters.
    """

    company_context: str = dspy.InputField()
    file_tree: str = dspy.InputField()
    target_language: str = dspy.InputField(desc="The desired language for the field content")
    file_list: str = dspy.OutputField(desc="The generated file list as JSON array")


file_list_predictor = dspy.Predict(FileListGeneratorSignature)


def generate_file_list(id: str, company_context: str, file_tree: str, target_language: str) -> list:
    if id in stored_data:
        return stored_data[id]
    with dspy.context(lm=dspy.LM(**model.to_litellm())):
        file_list_raw = file_list_predictor(
            company_context=company_context, file_tree=file_tree, target_language=target_language
        ).file_list
    file_list = json_repair.loads(file_list_raw)
    assert isinstance(file_list, list)
    set_stored_data(id, file_list)
    return file_list


class FileGeneratorSignature(dspy.Signature):
    """\
    Given the company context, a list of file descriptions, and one specific file description, generate a fictive file as markdown text.
    The file should be realistic and match its description.
    Include some spelling mistakes or other issues to make it look more realistic.
    Write about two pages. Include some kirkish aspects in the file.
    You can mention other files of the company. Make up people names and use them in the file.
    Answer with just the Markdown text, no other characters.
    """

    company_context: str = dspy.InputField()
    file_list: list = dspy.InputField()
    file_description: dict = dspy.InputField()
    target_language: str = dspy.InputField(desc="The desired language for the generated text")
    file_markdown: str = dspy.OutputField(desc="The generated file as Markdown text")


file_predictor = dspy.Predict(FileGeneratorSignature)


def generate_file(id: str, company_context: str, file_list: list, file_description: dict, target_language: str) -> str:
    if id in stored_data:
        return stored_data[id]
    with dspy.context(lm=dspy.LM(**model.to_litellm())):
        file_markdown = file_predictor(
            company_context=company_context,
            file_list=file_list,
            file_description=file_description,
            target_language=target_language,
        ).file_markdown
    set_stored_data(id, file_markdown)
    return file_markdown


def main():
    company_context = generate_company(
        "beer_brewing_company",
        "We are a company building beer brewing machine and are currently looking for software engineers with C++ skills to redo our user interface using Qt.",
        "en",
    )
    print(company_context)

    user_input = """\
    Generate a file tree for the main projects of the beer brewing company.
    Include meeting protocols, project plans, technical specifications, vendor contracts, and other relevant documents.
    Each project should have a different structure and different files.
    Also add a folder for generic company documents like the company profile, the employee handbook, and the code of conduct.
    Use only PDF, docx and pptx files for the documents.
    """

    tree = generate_tree("beer_brewing_company_files2_de", company_context, user_input, 25, "de")
    print(tree)

    file_list = generate_file_list("beer_brewing_company_files2x_de", company_context, tree, "de")
    pprint.pprint(file_list)

    for file in file_list:
        markdown = generate_file(file["full_path"], company_context, file_list, file, "de")
        path = os.path.join(DATA_FOLDER, file["full_path"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # convert markdown to pdf / docx / pptx:
        temp_md_path = os.path.join(DATA_FOLDER, "temp.md")
        with open(temp_md_path, "w") as temp_md_file:
            temp_md_file.write(markdown)

        subprocess.run(["pandoc", temp_md_path, "-o", path])

        # remove tmp file:
        os.remove(temp_md_path)


if __name__ == "__main__":
    main()
