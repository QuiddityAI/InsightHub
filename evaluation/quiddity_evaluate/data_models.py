from pydantic import BaseModel, ConfigDict


class ExampleDocument(BaseModel):
    model_config = ConfigDict(extra="allow")

    question: str
    fulltext: str
