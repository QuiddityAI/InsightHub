import threading
import logging

from django.utils import timezone
import dspy

from data_map_backend.models import DataCollection, User
from workflows.schemas import CreateCollectionSettings, WorkflowMetadata
from config.utils import get_default_dspy_llm


class WorkflowBase:
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="not_implemented",
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
        raise NotImplementedError


workflows_by_id: dict[str, type[WorkflowBase]] = {}


class QueryLanguageSignature(dspy.Signature):
    """Given the user question or task and the title, provide the language code of this question or task.
    Output language code should be a two-letter code.
    """

    user_question: str = dspy.InputField()
    language_code: str = dspy.OutputField()


query_language_predictor = dspy.Predict(QueryLanguageSignature)


def workflow(cls: type[WorkflowBase]):
    workflows_by_id[cls.metadata.workflow_id] = cls
    return cls


def create_collection_using_workflow(user: User, settings: CreateCollectionSettings) -> DataCollection:
    collection = DataCollection()
    collection.created_by = user
    collection.name = settings.user_input or f"Collection {timezone.now().isoformat()}"
    collection.related_organization_id = settings.related_organization_id  # type: ignore
    collection.agent_is_running = True
    collection.current_agent_step = "Preparing..."
    collection.cancel_agent_flag = False
    collection.save()
    # above takes about 17 ms

    def prepare_collection_in_thread():
        try:
            # creating thread takes about 0.6ms
            # preparing collection just for classic search takes up to 100ms
            workflow_cls: type[WorkflowBase] | None = workflows_by_id.get(settings.workflow_id)
            if not workflow_cls:
                logging.warning(f"Requested unsupported workflow: {settings.workflow_id}")
                workflow_cls = workflows_by_id["empty_collection"]
            assert workflow_cls

            if settings.auto_set_filters and workflow_cls.metadata.needs_result_language:
                if not settings.user_input:
                    settings.result_language = "en"
                else:
                    model = get_default_dspy_llm("query_language")
                    with dspy.context(lm=dspy.LM(**model.to_litellm())):
                        settings.result_language = query_language_predictor(
                            user_question=settings.user_input
                        ).language_code
            workflow_cls().run(collection, settings, user)
        except Exception as e:
            collection.agent_is_running = False
            collection.save()
            raise e

    thread = threading.Thread(target=prepare_collection_in_thread)
    thread.start()

    # wait a bit in case the task is quick, in that case we can reduce flickering in the UI
    try:
        thread.join(timeout=0.5)
    except TimeoutError:
        # if the task is still running, we return the collection without waiting
        pass
    # collecting the current / final results from the thread:
    collection.refresh_from_db()

    return collection
