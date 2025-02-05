import threading
import logging

from django.utils import timezone
from llmonkey.llms import Mistral_Ministral3b

from data_map_backend.models import DataCollection, User
from workflows.schemas import CreateCollectionSettings, WorkflowMetadata
from workflows.prompts import query_language_prompt


class WorkflowBase:
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="not_implemented",
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
        raise NotImplementedError


workflows_by_id: dict[str, type[WorkflowBase]] = {}


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
                prompt = query_language_prompt.replace("{{ query }}", settings.user_input or "")
                settings.result_language = (
                    Mistral_Ministral3b().generate_short_text(prompt, exact_required_length=2, temperature=0.3) or "en"
                )

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
