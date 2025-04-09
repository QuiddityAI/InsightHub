import time
from typing import Callable

import dspy

from columns.logic.process_column import process_cells_blocking
from config.utils import get_default_model
from data_map_backend.models import (
    COLUMN_META_SOURCE_FIELDS,
    CollectionColumn,
    CollectionItem,
    DataCollection,
    FieldType,
    SearchTask,
    User,
)
from data_map_backend.schemas import CollectionUiSettings
from search.logic.approve_items_and_exit_search import (
    approve_using_comparison,
    auto_approve_items,
    exit_search_mode,
)
from search.logic.execute_search import (
    add_items_from_task,
    add_items_from_task_and_run_columns,
    create_and_run_search_task,
)
from search.schemas import SearchTaskSettings
from workflows.create_columns import create_relevance_column
from workflows.schemas import CreateCollectionSettings


class QuiddityAgentAPI:
    def __init__(self, collection: DataCollection, settings: CreateCollectionSettings, user: User):
        self.collection = collection
        self.settings = settings
        self.user = user
        self._is_running = False
        self.after_columns_were_processed = lambda: None

    def make_finish_running_handler(self, callbacks: list[Callable] = []):
        def _handler(items: list[CollectionItem]):
            for callback in callbacks:
                callback(items)
            self._is_running = False

        return _handler

    def _after_columns_were_processed_internal(self, search_task, new_items):
        # needed to duplicate logic of run_search_task for continue_search
        # otherwise the cells are not appro
        from_ui = True
        task_settings = SearchTaskSettings(**search_task.settings)
        if task_settings.auto_approve:
            auto_approve_items(
                self.collection, new_items, task_settings.max_selections, task_settings.forced_selections, from_ui
            )
        elif task_settings.approve_using_comparison:
            self.collection.log_explanation(
                "Use AI model to **compare search results** and **approve best items**", save=False
            )
            approve_using_comparison(
                self.collection,
                new_items,
                task_settings,
                task_settings.max_selections,
                task_settings.forced_selections,
            )

    def search(
        self,
        query: str = "",
        vector: list[float] | None = None,
        num_search_results: int = 10,
        exit_search_mode=False,
        blocking=True,
    ) -> tuple[list[CollectionItem], SearchTask]:
        if not (query or vector):
            raise ValueError("Either query or vector must be provided")
        search_task = SearchTaskSettings(
            dataset_id=self.settings.dataset_id,
            user_input=query,
            result_language=self.settings.result_language,
            vector=vector,
            auto_set_filters=False,
            filters=None,
            retrieval_mode="vector",
            ranking_settings=self.settings.ranking_settings,
            auto_approve=True,
            approve_using_comparison=False,
            exit_search_mode=exit_search_mode,
            candidates_per_step=num_search_results,  # this is the number of search results
            use_reranking=False,
        )
        if blocking:
            self._is_running = True
            new_items, task = create_and_run_search_task(
                self.collection,
                search_task,
                self.user.id,  # type: ignore
                return_task_object=True,
                set_agent_step=False,
                after_columns_were_processed=self.make_finish_running_handler(),
            )  # type: ignore
            while self._is_running:
                time.sleep(0.1)
        else:
            new_items, task = create_and_run_search_task(
                self.collection,
                search_task,
                self.user.id,  # type: ignore
                set_agent_step=False,
                return_task_object=True,
            )
        return new_items, task  # type: ignore

    def continue_search(self, task: SearchTask, process_columns=True, blocking=True) -> list[CollectionItem]:
        def _run():
            if process_columns:
                items = add_items_from_task_and_run_columns(
                    task,
                    self.user.id,
                    ignore_last_retrieval=False,
                    # this is needed to duplicate logic of run_search_task to auto approve items
                    after_columns_were_processed=self.make_finish_running_handler(
                        callbacks=[lambda items: self._after_columns_were_processed_internal(task, items)]
                    ),
                )
            else:
                items = add_items_from_task(
                    self.collection,
                    task,
                    ignore_last_retrieval=False,
                )
            return items

        if process_columns and blocking:
            self._is_running = True
            items = _run()
            while self._is_running:
                time.sleep(0.1)
        else:
            items = _run()
        return items

    def create_relevance_column(self, query: str) -> CollectionColumn:
        column = create_relevance_column(self.collection, query, self.settings.result_language, self.user)
        return column

    def create_column(
        self, expression: str, name: str, module="llm", dspy_model: type[dspy.Module] | None = None,
    dspy_model_parameters={}) -> CollectionColumn:
        column = CollectionColumn.objects.create(
            collection=self.collection,
            name=name,
            identifier=name.lower().replace(" ", "_"),  # any unique string
            field_type=FieldType.STRING,
            expression=expression,
            prompt_template=None,  # set this if you want to use a custom prompt, otherwise a default is used
            source_fields=[
                COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS,
                COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS,
            ],
            module=module,  # there is also a special 'relevance' module, but that's a different story
            parameters={
                "model": get_default_model("medium").__class__.__name__,
                "language": self.settings.result_language,
                "dspy_model": dspy_model.__name__ if dspy_model else None,
                "dspy_model_parameters": dspy_model_parameters,
            },
            auto_run_for_candidates=True,  # set this to run this column for all search results
        )
        column.save()
        return column

    def update_message(self, message: str):
        self.collection.current_agent_step = message
        self.collection.save(update_fields=["current_agent_step"])

    def execute_column(self, column: CollectionColumn, items: list[CollectionItem]):
        process_cells_blocking(items, column, self.collection, self.user.id)  # type: ignore

    def show_writing_task_panel(self):
        self.collection.ui_settings = CollectionUiSettings(secondary_view="summary").model_dump()
        self.collection.save(update_fields=["ui_settings"])

    def exit_search_mode(self):
        exit_search_mode(self.collection, "_default", from_ui=True)

    def set_agent_running(self, is_running: bool):
        self.collection.agent_is_running = is_running
        self.collection.save(update_fields=["agent_is_running"])
