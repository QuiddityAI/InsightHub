import logging

import dspy
import numpy as np
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV

from data_map_backend.models import (
    CollectionItem,
    DataCollection,
    Dataset,
    Generator,
    SearchTask,
)
from legacy_backend.database_client.vector_search_engine_client import (
    VectorSearchEngineClient,
)
from legacy_backend.logic.model_client import get_local_embeddings
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


def get_detailed_instruct(task_description: str, query: str) -> str:
    return f"Instruct: {task_description}\nQuery: {query}"


class ExhaustiveSearchBB(BaseBuidingBlock[ExhaustiveSearchInputContext, ExhaustiveSearchOutputContext]):
    """Module to add metadata to items."""

    InputContext = ExhaustiveSearchInputContext
    OutputContext = ExhaustiveSearchOutputContext

    def __init__(
        self,
        dspy_lm: dspy.LM,
        max_queries: int = 5,
        top_best_queries: int = 3,
        max_depth: int = 5,
        items_per_page: int = 10,
        top_rarest_items: int = 3,
        explore_around_rare: bool = True,
        learn_query: bool = False,
    ):
        """
        Initializes the ExhaustiveSearchBB class.

        Args:
            dspy_lm (dspy.LM): The LM instance from the dspy library.
            max_queries (int, optional): The maximum number of search queries to explore
            top_best_queries (int, optional): The number of top best queries to consider. Defaults to 3.
            max_depth (int, optional): The maximum depth (in pages) for exploring the best queries. Defaults to 5.
            items_per_page (int, optional): Items per page. Defaults to 10.
            explore_around_rare (bool, optional): Whether to explore around rare items. Defaults to True.
        """

        self.max_queries = max_queries
        self.items_per_page = items_per_page
        self.dspy_lm = dspy_lm
        self.top_best_queries = top_best_queries
        self.explore_around_rare = explore_around_rare
        self.max_depth = max_depth
        self.learn_query = learn_query
        self.top_rarest_items = top_rarest_items

    def __call__(
        self, api: QuiddityAgentAPI, collection: DataCollection, context: ExhaustiveSearchInputContext
    ) -> tuple[DataCollection, ExhaustiveSearchOutputContext]:
        relevance_column = api.create_relevance_column(context.user_input)

        s = dspy.make_signature(
            "user_query: str, language_code: str -> search_queries: list[str]",
            """Generate detailed list of potential search queries to find documents relevant to user query. Include synonyms.
            For languages with compound words like German, split compounds into single words, e.g. "Wirtschaftswissenschaften" -> ["Wirtschaftswissenschaften", "Wirtschaft", "Wissenschaften"].
            Output queries in language, given by language_code""",
        )
        queries_gen = dspy.ChainOfThought(s)

        dataset = Dataset.objects.get(id=api.settings.dataset_id)
        candidate_queries = []
        # generate queries for all languages in the dataset
        for lang in dataset.languages or ["en"]:
            with dspy.context(lm=self.dspy_lm):
                # take first N queries
                candidate_queries.extend(
                    queries_gen(user_query=context.user_input, language_code=lang).search_queries[: self.max_queries]
                )

        # stage 1: search for the best queries
        api.update_message(f"Searching for the best queries...")
        queries: list[tuple[str, float, SearchTask]] = []
        items_counter = {}
        all_items: list[CollectionItem] = []
        for q in candidate_queries:
            items, task = api.search(q, num_search_results=self.items_per_page, blocking=True)
            all_items.extend(items)
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
            for page in range(2, self.max_depth + 1):
                new_items = api.continue_search(task, process_columns=True, blocking=True)
                all_items.extend(new_items)
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
            rare_item_ids = sorted({k: len(v) for k, v in items_counter.items()}, key=lambda x: x[1])[
                -self.top_rarest_items :
            ]
            for item_id in rare_item_ids:
                rare_item = items_counter[item_id][0]
                if abstract := rare_item.metadata.get("abstract"):
                    items, task = api.search(abstract, num_search_results=self.items_per_page, blocking=True)
                    all_items.extend(items)
                    mean_relevance = sum([c.relevance for c in items]) / len(items)
                    if mean_relevance > 0.5:
                        for page in range(2, self.max_depth + 1):
                            new_items = api.continue_search(task, process_columns=True, blocking=True)
                            all_items.extend(new_items)
                            if not new_items:
                                break
                            next_page_relevance = sum([c.relevance for c in new_items]) / len(new_items)
                            if mean_relevance < 0.5 * next_page_relevance:
                                collection.log_explanation("Mean relevance dropped below 50%, stopping exploration")
                                break

        unique_items = list({item.item_id: item for item in all_items}.values())
        if self.learn_query and unique_items:
            # ignore all the machinery of dataset schemas for now, just assume its full_text_chunk_embeddings
            vector_fields = [
                f
                for f in dataset.schema.object_fields.values()
                if f["identifier"] in dataset.schema.default_search_fields and f["field_type"] == "VECTOR"
            ]
            chunk_vector_field_name = "full_text_chunk_embeddings"
            abstract_vector_field_name = "embedding_e5"
            if any(
                field not in [v["identifier"] for v in vector_fields]
                for field in [chunk_vector_field_name, abstract_vector_field_name]
            ):
                logging.warning("Required vector field(s) for query learning not found")
                return collection, ExhaustiveSearchOutputContext(rated_queries=rated_queries, **context.model_dump())

            gens = [v["generator_id"] for v in vector_fields]
            if len(set(gens)) > 1:
                raise ValueError("Same generator must be used for all vector fields for now")
            generator = Generator.objects.get(identifier=gens[0])
            emb_model_id = generator.default_parameters["model_name"]  # type: ignore

            vector_client = VectorSearchEngineClient.get_instance()
            if "instruct" in emb_model_id:
                inp = get_detailed_instruct(
                    "Given a user query, retrieve relevant passages that help to answer the question",
                    rated_queries[0]["query"],
                )
            else:
                inp = rated_queries[0]["query"]

            vector = get_local_embeddings([inp], model_name=emb_model_id)[0]
            X_train = []
            Y_train = []
            # firstly collect vectors of abstracts
            resp = vector_client.get_items_by_ids(
                dataset=dataset,  # type: ignore
                ids=[u.item_id for u in unique_items if u.item_id],
                vector_field=abstract_vector_field_name,
                is_array_field=False,
                return_vectors=True,
            )
            for record, item_relevance in zip(resp, [u.relevance for u in unique_items if u.item_id]):
                X_train.append(record.vector[abstract_vector_field_name])
                Y_train.append(item_relevance)
            # then collect vectors of chunks
            for item in unique_items:
                resp = vector_client.get_best_sub_items(
                    dataset.actual_database_name, chunk_vector_field_name, item.item_id, vector, with_vectors=True, limit=1  # type: ignore
                )
                for sub_item in resp:
                    X_train.append(sub_item.vector["full_text_chunk_embeddings"])
                    Y_train.append(item.relevance)

            if not Y_train or len(set(Y_train)) == 1:
                logging.warning("Need both relevant and irrelevant items to learn, skipping learning")
                return collection, ExhaustiveSearchOutputContext(rated_queries=rated_queries, **context.model_dump())
            model = LogisticRegressionCV(class_weight="balanced", max_iter=1000)
            pca = PCA(n_components=0.95)  # Keep 95% of variance

            X_reduced = pca.fit_transform(np.array(X_train))
            model.fit(X_reduced, Y_train)
            # Get vector in original space by inverse-transforming coefficients
            coeff_original = pca.inverse_transform(model.coef_).squeeze()  # Back to original space
            new_vector = coeff_original / np.linalg.norm(coeff_original)
            new_items, task = api.search(
                "", vector=list(new_vector), num_search_results=self.items_per_page, blocking=True
            )
            first_relevance = sum([c.relevance for c in new_items]) / len(new_items)
            for page in range(2, self.max_depth + 1):
                new_items = api.continue_search(task, process_columns=True, blocking=True)
                if not new_items:
                    break
                mean_relevance = sum([c.relevance for c in new_items]) / len(new_items)
                if mean_relevance < first_relevance * 0.5:
                    collection.log_explanation(
                        "Mean relevance dropped below 50% of the first page, stopping exploration"
                    )
                    break

        return collection, ExhaustiveSearchOutputContext(rated_queries=rated_queries, **context.model_dump())
