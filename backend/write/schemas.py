from ninja import Schema


class AddWritingTaskPayload(Schema):
    collection_id: int
    class_name: str
    name: str
    options: dict | None = None
    run_now: bool = False


class WritingTaskIdentifier(Schema):
    task_id: int


class UpdateWritingTaskPayload(Schema):
    task_id: int
    name: str
    source_fields: list = []
    use_all_items: bool = True
    selected_item_ids: list = []
    module: str | None = None
    parameters: dict = {}
    prompt: str | None = None
    text: str | None = None
