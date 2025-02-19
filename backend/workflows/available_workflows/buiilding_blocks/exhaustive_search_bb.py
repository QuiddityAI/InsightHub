import dspy

from data_map_backend.models import CollectionItem, DataCollection, SearchTask
from workflows.available_workflows.agents.agent_api import QuiddityAgentAPI
from workflows.available_workflows.buiilding_blocks.base_bb import (
    BaseBBContext,
    BaseBuidingBlock,
)


def group_objects_by_key(objects: list[CollectionItem], key: str, grouped_objects: dict | None = None) -> dict:
    if grouped_objects is None:
        grouped_objects = {}
    for obj in objects:
        value = getattr(obj, key)
        if value not in grouped_objects:
            grouped_objects[value] = []
        grouped_objects[value].append(obj)
    return grouped_objects


class ExhaustiveSearchInputContext(BaseBBContext):
    user_input: str


class ExhaustiveSearchOutputContext(BaseBBContext):
    rated_queries: list[dict]


class ExhaustiveSearchBB(BaseBuidingBlock[ExhaustiveSearchInputContext, ExhaustiveSearchOutputContext]):
    """Module to add metadata to items."""

    InputContext = ExhaustiveSearchInputContext
    OutputContext = ExhaustiveSearchOutputContext

    def __init__(
        self,
        dspy_lm: dspy.LM,
        max_queries: int = 5,
        top_best_queries: int = 3,
        items_per_page: int = 10,
        explore_around_rare: bool = True,
    ):
        self.max_queries = max_queries
        self.items_per_page = items_per_page
        self.dspy_lm = dspy_lm
        self.top_best_queries = top_best_queries
        self.explore_around_rare = explore_around_rare

    def __call__(
        self, api: QuiddityAgentAPI, collection: DataCollection, context: ExhaustiveSearchInputContext
    ) -> tuple[DataCollection, ExhaustiveSearchOutputContext]:

        s = dspy.make_signature(
            "user_query: str, example_docs: list[str] -> search_queries: list[str]",
            """Generate detailed list of potential search queries to find documents relevant to user query. Include synonyms.
                                Use provided example documents to improve the query.""",
        )
        queries_gen = dspy.ChainOfThought(s)
        with dspy.context(lm=self.dspy_lm):
            # take first N queries
            candidate_queries = queries_gen(user_query=context.user_input, example_docs=[]).search_queries[
                : self.max_queries
            ]

        # stage 1: search for the best queries
        api.update_message(f"Searching for the best queries...")
        queries: list[tuple[str, float, SearchTask]] = []
        items_counter = {}
        for q in candidate_queries:
            items, task = api.search(q, num_search_results=self.items_per_page, blocking=True)
            # count how many times given item was found, we'll need later for exploring the space
            items_counter = group_objects_by_key([i for i in items if i.relevance], "item_id", items_counter)
            mean_relevance = sum([c.relevance for c in items]) / len(items)
            print(f"Mean relevance for query '{q}': {mean_relevance}")
            queries.append((q, mean_relevance, task))

        queries = sorted(queries, key=lambda x: x[1], reverse=True)
        rated_queries = [{"query": q, "mean_relevance": mean_relevance} for q, mean_relevance, _ in queries]
        # stage 2: explore the best queries deeper
        api.update_message(f"Exploring the best queries in details...")
        for q, mean_relevance_first, task in queries[: self.top_best_queries]:
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

        if self.explore_around_rare:
            # stage 3: explore the space around rare relevant documents
            api.update_message(f"Exploring the space around rare relevant documents...")
            rare_item_ids = sorted({k: len(v) for k, v in items_counter.items()}, key=lambda x: x[1])[-3:]
            for item_id in rare_item_ids:
                rare_item = items_counter[item_id][0]
                if abstract := rare_item.metadata.get("abstract"):
                    items, task = api.search(abstract, num_search_results=self.items_per_page, blocking=True)
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

        return collection, ExhaustiveSearchOutputContext(rated_queries=rated_queries, **context.model_dump())
