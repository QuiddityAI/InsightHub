import dspy
import logging

from workflows.available_workflows.agents.agent_api import QuiddityAgentAPI
from write.logic.writing_task import execute_writing_task_safe
from data_map_backend.models import (
    COLUMN_META_SOURCE_FIELDS,
    CollectionColumn,
    CollectionItem,
    DataCollection,
    User,
    SearchTask,
    WritingTask,
)
from workflows.logic import WorkflowBase, workflow
from workflows.schemas import (
    CreateCollectionSettings,
    WorkflowAvailability,
    WorkflowMetadata,
    WorkflowOrder,
)
from config.utils import get_default_model
from workflows.dspy_models import register_dspy_model
from workflows.available_workflows.agents.utils import override_dspy_model


dspy_lm = dspy.LM(**get_default_model("medium").to_litellm())


class ExtractorSignature(dspy.Signature):
    """You are given the page of text, and a list of extracted information.
    Find new information according to the task and generate new_information to extend
    list of information.
    """

    task: str = dspy.InputField(desc="Description of what information to extract")
    page: str = dspy.InputField()
    information: list[str] = dspy.InputField(desc="Already extracted information")
    new_information: list[str] = dspy.OutputField(desc="New information or empty list if not found")


@register_dspy_model
class LongTextExtractor(dspy.Module):
    def __init__(self):
        self.extractor = dspy.Predict(ExtractorSignature)

    def forward(self, column: CollectionColumn, input_data: dict) -> str:
        facts = []
        max_retries = 3
        for chunk in input_data["full_text_chunks"]:
            if not chunk["text"]:
                continue
            if len(chunk["text"]) > 5000:
                subchunks = self.split_text_into_chunks(chunk["text"], chunk_length=4000, overlap_length=500)
            else:
                subchunks = [chunk["text"]]
            for text in subchunks:
                try:
                    pred = self.extractor(task=column.expression, page=text, information=facts)
                    facts.extend(pred.new_information)
                except Exception as e:
                    # oops, something went wrong, try again but firstly disable cache
                    # dspy is implementing this support natively, but for now we'll do it manually
                    # https://github.com/stanfordnlp/dspy/pull/1959
                    logging.warning("Can't get predictions, retrying with cache disabled")
                    with dspy.context(lm=(lm := override_dspy_model(cache=False))):
                        for retry in range(max_retries):
                            try:
                                pred = self.extractor(task=column.expression, page=text, information=facts)
                                facts.extend(pred.new_information)
                                logging.warning(f"Success on retry {retry}")
                                break
                            except Exception as e:
                                if retry == max_retries - 1:
                                    logging.error(
                                        f"Can't get predictions, giving up. Last response: {lm.history[0]['response'].choices[0]}"
                                    )
                                    # we'll just skip this chunk then
        return "\n".join(f"- {fact}" for fact in facts)

    def split_text_into_chunks(self, text, chunk_length, overlap_length):
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + chunk_length, text_length)
            chunks.append(text[start:end])
            start += chunk_length - overlap_length

        return chunks


def group_objects_by_key(objects: list[CollectionItem], key: str, grouped_objects: dict = None) -> dict:
    if grouped_objects is None:
        grouped_objects = {}
    for obj in objects:
        value = getattr(obj, key)
        if value not in grouped_objects:
            grouped_objects[value] = []
        grouped_objects[value].append(obj)
    return grouped_objects


@workflow
class ExhaustiveSearchWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="exhaustive_search",
        order=WorkflowOrder.agent + 2,
        name1={"en": "Let an", "de": "Lass einen"},
        name2={"en": "Agent do exhaustive search", "de": "Agent Forschung betreiben"},
        help_text={
            "en": "An agent that looks for documents and executes summary",
            "de": "Ein Agent, der nach Dokumenten sucht und sie autonom zusammenfasst",
        },
        query_field_hint={"en": "Your question", "de": "Deine Frage"},
        supports_filters=False,
        needs_user_input=True,
        needs_result_language=True,
        availability=WorkflowAvailability.general_availability,
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
        assert settings.user_input is not None

        api = QuiddityAgentAPI(collection, settings, user)
        relevance_column = api.create_relevance_column(settings.user_input)
        items_per_page = 10

        # run a search:

        s = dspy.make_signature(
            "user_query: str, example_docs: list[str] -> search_queries: list[str]",
            """Generate detailed list of potential search queries to find documents relevant to user query. Include synonyms.
                                Use provided example documents to improve the query.""",
        )
        queries_gen = dspy.ChainOfThought(s)
        with dspy.context(lm=dspy_lm):
            # lets limit to just 5 queries for now
            candidate_queries = queries_gen(user_query=settings.user_input, example_docs=[]).search_queries[:5]

        # stage 1: search for the best queries
        api.update_message(f"Searching for the best queries...")
        queries: list[tuple[str, float, SearchTask]] = []
        items_counter = {}
        for q in candidate_queries:
            items, task = api.search(q, num_search_results=items_per_page, blocking=True)
            # count how many times given item was found, we'll need later for exploring the space
            items_counter = group_objects_by_key([i for i in items if i.relevance], "item_id", items_counter)
            mean_relevance = sum([c.relevance for c in items]) / len(items)
            print(f"Mean relevance for query '{q}': {mean_relevance}")
            queries.append((q, mean_relevance, task))

        queries = sorted(queries, key=lambda x: x[1], reverse=True)
        # stage 2: explore the best queries deeper
        api.update_message(f"Exploring the best queries in details...")
        for q, mean_relevance_first, task in queries[:3]:
            collection.log_explanation(f"Exploring query '{q}'...")
            for page in range(2, 3):
                new_items = api.continue_search(task, process_columns=True, blocking=True)
                items_counter = group_objects_by_key([i for i in new_items if i.relevance], "item_id", items_counter)
                if not new_items:
                    break
                mean_relevance = sum([c.relevance for c in new_items]) / len(new_items)
                collection.log_explanation(f"Mean relevance for query '{q}' on page {page}: {mean_relevance}")
                if mean_relevance < mean_relevance_first * 0.5:
                    collection.log_explanation(
                        "Mean relevance dropped below 50% of the first page, stopping exploration"
                    )
                    break

        # stage 3: explore the space around rare relevant documents
        api.update_message(f"Exploring the space around rare relevant documents...")
        rare_item_ids = sorted({k: len(v) for k, v in items_counter.items()}, key=lambda x: x[1])[-3:]
        for item_id in rare_item_ids:
            rare_item = items_counter[item_id][0]
            if abstract := rare_item.metadata.get("abstract"):
                items, task = api.search(abstract, num_search_results=items_per_page, blocking=True)
                mean_relevance = sum([c.relevance for c in items]) / len(items)
                if mean_relevance > 0.5:
                    for page in range(2, 5):
                        new_items = api.continue_search(task, process_columns=True, blocking=True)
                        if not new_items:
                            break
                        next_page_relevance = sum([c.relevance for c in new_items]) / len(new_items)
                        if mean_relevance < 0.5 * next_page_relevance:
                            collection.log_explanation("Mean relevance dropped below 50%, stopping exploration")
                            break

        api.exit_search_mode()
        api.update_message(f"Analyzing results...")

        # stage 4: extract the relevant information from the results
        all_found_items: list[CollectionItem] = collection.items.all()  # type: ignore
        s = dspy.make_signature(
            "task: str -> assistant_task: str, task_name: str",
            "Given the user task, tell assistant working with single document what to extract from the document. Also provide the short name of the task.",
        )
        column_task_gen = dspy.Predict(s)
        with dspy.context(lm=dspy_lm):
            cell_task_params = column_task_gen(task=settings.user_input)
        collection.log_explanation(f"Applied task {cell_task_params.assistant_task} to the results...")
        info_column = api.create_column(
            cell_task_params.assistant_task, cell_task_params.task_name, module="dspy", dspy_model=LongTextExtractor
        )
        api.execute_column(info_column, all_found_items)

        # stage 4: summarize the results
        api.update_message(f"Writing final answer...")
        api.show_writing_task_panel()
        # create the final result:
        writing_task = WritingTask(
            collection=collection,
            name="Final Answer",
            source_fields=[
                COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS,
                "_column__" + info_column.identifier,
            ],
            use_all_items=True,
            model=user.preferences.get("default_large_llm") or "Mistral_Mistral_Large",
            expression=f"Summarize the results of the search in regard to this question '{settings.user_input}'.",
            # its always using a default prompt plus this prompt, I just realized it doesn't have the option to override the default prompt yet
        )
        writing_task.save()
        execute_writing_task_safe(writing_task)
        collection.agent_is_running = False
        collection.save(update_fields=["agent_is_running"])
