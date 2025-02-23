import logging

import dspy
import numpy as np

from config.utils import get_default_model
from data_map_backend.models import (
    COLUMN_META_SOURCE_FIELDS,
    CollectionColumn,
    CollectionItem,
    DataCollection,
    Dataset,
    SearchTask,
    User,
    WritingTask,
)
from legacy_backend.database_client.vector_search_engine_client import (
    VectorSearchEngineClient,
)
from legacy_backend.logic.model_client import get_local_embeddings
from legacy_backend.logic.search_common import get_document_details_by_id
from workflows.available_workflows.agents.agent_api import QuiddityAgentAPI
from workflows.available_workflows.agents.utils import override_dspy_model
from workflows.available_workflows.buiilding_blocks.exhaustive_search_bb import (
    ExhaustiveSearchBB,
)
from workflows.dspy_models import register_dspy_model
from workflows.logic import WorkflowBase, workflow
from workflows.schemas import (
    CreateCollectionSettings,
    WorkflowAvailability,
    WorkflowCategory,
    WorkflowMetadata,
    WorkflowOrder,
)
from write.logic.writing_task import execute_writing_task_safe

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


def get_detailed_instruct(task_description: str, query: str) -> str:
    return f"Instruct: {task_description}\nQuery: {query}"


@workflow
class ExhaustiveSearchWithAnswerWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="exhaustive_search_with_answer",
        order=WorkflowOrder.agent + 3,
        categories=[WorkflowCategory.search_and_curate],
        name1={"en": "🕵️ Let an agent", "de": "🕵️ Lass einen Agent"},
        name2={"en": "Answer based on all docs", "de": "anhand aller Dokumente antworten"},
        help_text={
            "en": "An agent that looks for documents relevant to your query ans generates an answer",
            "de": "Ein Agent, der nach für Ihre Anfrage relevanten Dokumenten sucht und eine Antwort generiert",
        },
        query_field_hint={
            "en": "What <entity_name_plural> you want to find",
            "de": "Welche <entity_name_plural> möchtest Du finden?",
        },
        supports_filters=False,
        needs_user_input=True,
        needs_result_language=True,
        availability=WorkflowAvailability.general_availability,
        needs_opt_in=False,
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
        assert settings.user_input is not None

        dataset = Dataset.objects.get(id=settings.dataset_id)
        total_items: int = dataset.item_count or 100  # type: ignore
        # set parameters for the exhaustive search based on the dataset size
        params_per_size = {  # TODO: for small dataset use true exhaustive search
            100: dict(max_depth=2, max_queries=3),
            250: dict(max_depth=3, max_queries=4),
            500: dict(max_depth=3, max_queries=5),
            1000: dict(max_depth=7, max_queries=7),
        }

        selected_params = None
        for size in sorted(params_per_size.keys()):
            if total_items <= size:
                selected_params = params_per_size[size]
                break

        if selected_params is None:
            selected_params = params_per_size[max(params_per_size.keys())]

        api = QuiddityAgentAPI(collection, settings, user)

        search_bb = ExhaustiveSearchBB(dspy_lm=dspy_lm, explore_around_rare=False, **selected_params, learn_query=True)
        collection, out_context = search_bb(api, collection, search_bb.InputContext(user_input=settings.user_input))

        api.exit_search_mode()

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
        all_found_items: list[CollectionItem] = collection.items.all()  # type: ignore
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
        api.set_agent_running(False)
