from abc import ABC, abstractmethod
from typing import Generic, Tuple, Type, TypeVar

from pydantic import BaseModel, ConfigDict

from data_map_backend.models import DataCollection
from workflows.available_workflows.agents.agent_api import QuiddityAgentAPI


class BaseBBContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")


TInputContext = TypeVar("TInputContext", bound=BaseBBContext)
TOutputContext = TypeVar("TOutputContext", bound=BaseBBContext)


class BaseBuidingBlock(ABC, Generic[TInputContext, TOutputContext]):
    """Base class for all modules, with explicit input and output context types."""

    InputContext: Type[TInputContext]
    OutputContext: Type[TOutputContext]

    @abstractmethod
    def __call__(
        self, api: QuiddityAgentAPI, collection: DataCollection, context: TInputContext
    ) -> Tuple[DataCollection, TOutputContext]:
        pass
