import time

import dspy

from columns.logic.process_column import process_cells_blocking
from columns.schemas import CellData
from config.utils import get_default_model
from data_map_backend.models import (
    COLUMN_META_SOURCE_FIELDS,
    CollectionColumn,
    CollectionItem,
    DataCollection,
    FieldType,
    User,
    WritingTask,
)
from data_map_backend.schemas import CollectionUiSettings, ItemRelevance
from search.logic.execute_search import create_and_run_search_task
from search.schemas import SearchTaskSettings
from workflows.logic import WorkflowBase, workflow
from workflows.schemas import (
    CreateCollectionSettings,
    WorkflowAvailability,
    WorkflowCategory,
    WorkflowMetadata,
    WorkflowOrder,
)
from write.logic.writing_task import execute_writing_task_safe
from config.utils import get_default_model
from collections import Counter

dspy.configure(lm=dspy.LM(**get_default_model("medium").to_litellm()))


@workflow
class ResearchAgentWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="research_agent",
        categories=[WorkflowCategory.answer_and_report],
        order=WorkflowOrder.agent + 1,
        name1={"en": "🕵️ Let an", "de": "🕵️ Lass einen"},
        name2={"en": "Agent do Research", "de": "Agent Forschung betreiben"},
        help_text={
            "en": "An agent that looks for documents and summarizes them autonomously",
            "de": "Ein Agent, der nach Dokumenten sucht und sie autonom zusammenfasst",
        },
        query_field_hint={"en": "Your question", "de": "Deine Frage"},
        supports_filters=False,
        needs_user_input=True,
        needs_result_language=True,
        availability=WorkflowAvailability.in_development,
        needs_opt_in=True,
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
        assert settings.user_input is not None

        # run a search:
        collection.current_agent_step = "Searching..."
        collection.save(update_fields=["current_agent_step"])
        time.sleep(2)  # just for the demo to understand the process

        search_task = SearchTaskSettings(
            dataset_id=settings.dataset_id,
            user_input=settings.user_input
            or "",  # this is the full, natural language question (of course your agent could first generate a better one)
            result_language=settings.result_language,
            auto_set_filters=settings.auto_set_filters,
            filters=settings.filters,
            retrieval_mode=settings.retrieval_mode,
            ranking_settings=settings.ranking_settings,
            auto_approve=False,
            approve_using_comparison=False,
            exit_search_mode=False,
            candidates_per_step=10,  # this is the number of search results
        )
        new_items = create_and_run_search_task(collection, search_task, user, is_new_collection=True)  # type: ignore
        # now the results are already there (search is run synchronously, but if there would already be columns, they are run asynchronously)

        time.sleep(2)  # just for the demo to understand the process

        # create a column:
        column = CollectionColumn.objects.create(
            collection=collection,
            name="Relevance",
            identifier="relevance",  # any unique string
            field_type=FieldType.STRING,
            expression=f"Is the item relevant to the question '{settings.user_input}'?",
            prompt_template=None,  # set this if you want to use a custom prompt, otherwise a default is used
            source_fields=[
                COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS,
                COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS,
            ],
            module="llm",  # there is also a special 'relevance' module, but that's a different story
            parameters={"model": get_default_model("medium").__class__.__name__, "language": settings.result_language},
            auto_run_for_candidates=True,  # set this to run this column for all search results
        )
        time.sleep(2)  # just for the demo to understand the process
        # new_items = collection.items.all()  # alternative to get all items
        max_evaluated_candidates = 10
        collection.current_agent_step = "Evaluating results..."
        collection.log_explanation(f"Evaluting items individually", save=False)
        collection.save(update_fields=["current_agent_step", "explanation_log"])
        process_cells_blocking(new_items[:max_evaluated_candidates], column, collection, user.id)  # type: ignore

        time.sleep(2)  # just for the demo to understand the process

        # get the results of the column:
        for item in new_items[:max_evaluated_candidates]:
            data = CellData(**item.column_data[column.identifier])
            print(data.value)  # this is the text value of the cell
            assert isinstance(data.value, str)  # could by dict or list for other column types

            # set the relevance of an item:
            if "yes" in data.value.lower():
                item.relevance = ItemRelevance.APPROVED_BY_AI
                item.save(update_fields=["relevance"])

        # create the final result:
        writing_task = WritingTask(
            collection=collection,
            name="Final Answer",
            source_fields=[
                COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS,
                COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS,
            ],
            use_all_items=True,
            model=user.preferences.get("default_large_llm") or "Mistral_Mistral_Large",
            expression=f"Summarize the results of the search in regard to this question '{settings.user_input}'.",
            # its always using a default prompt plus this prompt, I just realized it doesn't have the option to override the default prompt yet
        )
        writing_task.save()
        collection.ui_settings = CollectionUiSettings(secondary_view="summary").model_dump()
        collection.current_agent_step = "Writing final answer..."
        collection.save(update_fields=["ui_settings", "current_agent_step"])
        execute_writing_task_safe(writing_task)
        collection.agent_is_running = False
        collection.save(update_fields=["agent_is_running"])


class QuiddityAPI:
    def __init__(self, collection: DataCollection, settings: CreateCollectionSettings, user: User):
        self.collection = collection
        self.settings = settings
        self.user = user

    def search(self, query: str, num_search_results: int = 10, is_new_collection=False) -> list[CollectionItem]:
        search_task = SearchTaskSettings(
            dataset_id=self.settings.dataset_id,
            user_input=query,
            result_language=self.settings.result_language,
            auto_set_filters=self.settings.auto_set_filters,
            filters=self.settings.filters,
            retrieval_mode=self.settings.retrieval_mode,
            ranking_settings=self.settings.ranking_settings,
            auto_approve=False,
            approve_using_comparison=False,
            exit_search_mode=False,
            candidates_per_step=num_search_results,  # this is the number of search results
        )
        new_items = create_and_run_search_task(self.collection, search_task, self.user.id, is_new_collection=is_new_collection)  # type: ignore
        return new_items

    def create_column(self, expression: str, name: str) -> CollectionColumn:
        column = CollectionColumn.objects.create(
            collection=self.collection,
            name="Relevance",
            identifier="relevance",  # any unique string
            field_type=FieldType.STRING,
            expression=f"Is the item relevant to the question '{self.settings.user_input}'?",
            prompt_template=None,  # set this if you want to use a custom prompt, otherwise a default is used
            source_fields=[
                COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS,
                COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS,
            ],
            module="llm",  # there is also a special 'relevance' module, but that's a different story
            parameters={
                "model": get_default_model("medium").__class__.__name__,
                "language": self.settings.result_language,
            },
            auto_run_for_candidates=True,  # set this to run this column for all search results
        )
        return column

    def update_message(self, message: str):
        self.collection.current_agent_step = message
        self.collection.save(update_fields=["current_agent_step"])


'''
class MultiEntrySearch(dspy.Module):

    def __init__(self):

        self.judge = DocJudge()

    def search_evaluate(self, task: str, query: str, page: int = 1) -> float:
        """Performs search with provided query and estimates relevancy of the documents
        found on the given page"""
        try:
            documents = search(query, page=page - 1)
            rel = self.judge(task=task, documents=documents)
        except Exception as e:
            print(e)
            return 0.0
        return rel

    def forward(self, task):
        example_docs = []
        for i in range(3):
            print(f"Iteration {i}")
            candidate_queries = self.queries_gen(user_query=task, example_docs=example_docs).search_queries
            observed = []
            # 1. test different queries by evaluating relevancy of found items
            for q in candidate_queries:
                relevance = self.search_evaluate(task=task, query=q, page=1)
                observed.append(dict(relevance=relevance, query=q))
                print(q, relevance)
            observed = sorted(observed, key=lambda x: x["relevance"])
            # 2. for the best queries go deeper
            for o in observed[-3:]:
                best_query, best_rel = o["query"], o["relevance"]
                for page in range(2, 10):
                    relevance = self.search_evaluate(task=task, query=best_query, page=page)
                    print(relevance)
                    if relevance < best_rel * 0.3 and page > 3:
                        print("Not relevant anymore")
                        break
            example_docs = [l[0] for l in Counter(self.judge.summaries).most_common()[-10:]]
        # 3. additionally use several best documents as queries to explore the space
        # around rare relevant docs found before
        #         candidate_docs = [l[0] for l in Counter(self.judge.relevant_docs).most_common()[:-10-1:-1]]
        #         for doc in candidate_docs:
        #             relevance = self.search_evaluate(task=task, query=get_text(doc), page=1)
        #             print(relevance)
        #             if relevance > 0.6:
        #                 for page in range(2, 10):
        #                     relevance = self.search_evaluate(task=task, query=get_text(doc), page=page)
        #                     if relevance < 0.4:
        #                         break
        return self.judge.relevant_docs
'''


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
        api = QuiddityAPI(collection, settings, user)

        # run a search:

        s = dspy.make_signature(
            "user_query: str, example_docs: list[str] -> search_queries: list[str]",
            """Generate detailed list of potential search queries to find documents relevant to user query. Include synonyms.
                                Use provided example documents to improve the query.""",
        )
        queries_gen = dspy.ChainOfThought(s)

        candidate_queries = queries_gen(user_query=settings.user_input, example_docs=[]).search_queries

        # now the results are already there (search is run synchronously, but if there would already be columns, they are run asynchronously)
        new_items = []
        for idx, q in enumerate(candidate_queries):
            api.update_message(f"Searching for '{q}'")
            new_items.extend(api.search(q, is_new_collection=(idx == 0)))

        # # create a column:
        column = api.create_column("List mentioned machines", "Machines")

        time.sleep(2)  # just for the demo to understand the process
        # # new_items = collection.items.all()  # alternative to get all items

        # get the results of the column:
        max_evaluated_candidates = 10
        for item in new_items[:max_evaluated_candidates]:
            data = CellData(**item.column_data[column.identifier])
            print(data.value)  # this is the text value of the cell
            assert isinstance(data.value, str)  # could by dict or list for other column types

        # create the final result:
        writing_task = WritingTask(
            collection=collection,
            name="Final Answer",
            source_fields=[
                COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS,
                COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS,
            ],
            use_all_items=True,
            model=user.preferences.get("default_large_llm") or "Mistral_Mistral_Large",
            expression=f"Summarize the results of the search in regard to this question '{settings.user_input}'.",
            # its always using a default prompt plus this prompt, I just realized it doesn't have the option to override the default prompt yet
        )
        writing_task.save()
        collection.ui_settings = CollectionUiSettings(secondary_view="summary").model_dump()
        collection.current_agent_step = "Writing final answer..."
        collection.save(update_fields=["ui_settings", "current_agent_step"])
        execute_writing_task_safe(writing_task)
        collection.agent_is_running = False
        collection.save(update_fields=["agent_is_running"])
