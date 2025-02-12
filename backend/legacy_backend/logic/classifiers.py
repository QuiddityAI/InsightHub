# when using classifier class to color an attribute, it must have a version / last changed date in parameters to make caching work

# simple use cases:
# - use collection class (e.g. review paper) for saturation (or secondary opacity) property
#   but what if map by title but colorize by classifier on image embedding?
# - show classifier scores / tags in details modal (based on default search fields or overrides)
# - show recommendations / search by collection class (based on default search fields or overrides)

# workflow:
# - retrain button (per class, for all - but what if only one class of 10k tags changed? solved, if no annotation field is used)


import copy
import json
import logging
import time
from itertools import chain
from threading import Thread

import numpy as np

from data_map_backend.utils import DotDict
from legacy_backend.database_client.django_client import (
    get_collection,
    get_collection_items,
    get_dataset,
    set_trained_classifier,
)
from legacy_backend.database_client.text_search_engine_client import (
    TextSearchEngineClient,
)
from legacy_backend.database_client.vector_search_engine_client import (
    VectorSearchEngineClient,
)
from legacy_backend.logic.extract_pipeline import get_pipeline_steps
from legacy_backend.logic.generate_missing_values import (
    generate_missing_values_for_given_elements,
)
from legacy_backend.logic.search_common import get_document_details_by_id
from legacy_backend.utils.field_types import FieldType


def get_embedding_space_from_ds_and_field(ds_and_field: tuple[int, str]) -> DotDict:
    dataset: DotDict = get_dataset(ds_and_field[0])
    field = dataset.schema.object_fields[ds_and_field[1]]
    embedding_space = field.generator.embedding_space if field.generator else field.embedding_space
    return DotDict(embedding_space)


def _get_task_id(collection_id: int, class_name: str, embedding_space_identifier: int):
    return f"{collection_id}_{class_name}_{embedding_space_identifier}"


RETRAINING_TASKS = {}  # collection_id -> task status (class name, progress)


def get_retraining_status(collection_id: int, class_name: str, embedding_space_identifier: int):
    status = RETRAINING_TASKS.get(_get_task_id(collection_id, class_name, embedding_space_identifier))
    if isinstance(status, dict):
        status = copy.copy(status)
        if "thread" in status:
            del status["thread"]
        if status["status"] == "done":
            del RETRAINING_TASKS[_get_task_id(collection_id, class_name, embedding_space_identifier)]
    return status


def start_retrain(collection_id: int, class_name: str, embedding_space_identifier: int, deep_train=False):
    thread = Thread(target=_retrain_safe, args=(collection_id, class_name, embedding_space_identifier, deep_train))
    RETRAINING_TASKS[_get_task_id(collection_id, class_name, embedding_space_identifier)] = {
        "class_name": class_name,
        "progress": 0,
        "status": "running",
        "error": "",
        "thread": thread,
        "time_finished": None,
    }
    thread.start()
    # general clean up: delete other status after 5 minutes:
    for other_task_id, other_status in RETRAINING_TASKS.items():
        if other_status.get("time_finished") and time.time() - other_status["time_finished"] > 300:
            del RETRAINING_TASKS[other_task_id]


def _retrain_safe(collection_id, class_name, embedding_space_identifier, deep_train=False):
    # if deep_train, retrain using examples instead of decision vectors from parent collections
    # get all examples for class
    # get all embeddings for examples
    # train classifier
    # store classifier, best threshold, metrics

    try:
        _retrain(collection_id, class_name, embedding_space_identifier, deep_train)
    except Exception as e:
        task_id = _get_task_id(collection_id, class_name, embedding_space_identifier)
        RETRAINING_TASKS[task_id]["status"] = "error"
        RETRAINING_TASKS[task_id]["error"] = str(e)
        RETRAINING_TASKS[task_id]["time_finished"] = time.time()
        logging.exception(e)


def _retrain(collection_id, class_name, embedding_space_identifier, deep_train=False):
    # rudimentary implementation just for simple case of non-exclusive classes and item_id examples:
    collection = get_collection(collection_id)
    task_id = _get_task_id(collection_id, class_name, embedding_space_identifier)
    assert collection is not None
    examples = get_collection_items(collection_id, class_name, field_type=None, is_positive=None)
    positive_vectors = []
    negative_vectors = []
    vector_db_client = VectorSearchEngineClient.get_instance()
    included_dataset_ids = set()
    for i, example in enumerate(examples):
        RETRAINING_TASKS[task_id]["progress"] = i / len(examples)
        vector = None
        if example["field_type"] == FieldType.IDENTIFIER:
            dataset_id = example["dataset_id"]
            item_id = example["item_id"]
            # TODO: batch process
            dataset = get_dataset(dataset_id)
            source_fields = []
            dataset_specific_settings = next(
                filter(lambda item: item.dataset_id == dataset_id, collection.dataset_specific_settings), None
            )
            vector_field = None
            if dataset_specific_settings:
                source_fields = dataset_specific_settings.relevant_object_fields
            else:
                source_fields = dataset.schema.default_search_fields
            for field_name in chain(source_fields, dataset.schema.object_fields.keys()):
                if field_name in dataset.schema.object_fields:
                    field = dataset.schema.object_fields[field_name]
                    try:
                        field_embedding_space_identifier = (
                            field.generator.embedding_space.identifier
                            if field.generator
                            else field.embedding_space.identifier
                        )
                    except AttributeError:
                        field_embedding_space_identifier = None
                    if embedding_space_identifier == field_embedding_space_identifier:
                        vector_field = field.identifier
                        break
            if vector_field:
                included_dataset_ids.add((dataset_id, vector_field))
                try:
                    logging.warning(f"Getting vector for {dataset_id} {item_id} {vector_field}")
                    is_array_field = dataset.schema.object_fields[vector_field].is_array
                    results = vector_db_client.get_items_by_ids(
                        dataset, [item_id], vector_field, is_array_field, return_vectors=True, return_payloads=False
                    )
                except Exception as e:
                    logging.warning(e)
                    results = []
                if len(results) >= 1 and results[0].id == item_id:
                    vector = results[0].vector[vector_field]
                if not vector:
                    pipeline_steps, required_fields, _ = get_pipeline_steps(dataset, only_fields=[vector_field])
                    item = get_document_details_by_id(
                        dataset_id, item_id, fields=tuple(required_fields), database_name=dataset.actual_database_name
                    )
                    assert item is not None
                    generate_missing_values_for_given_elements(pipeline_steps, [item])
                    vector = item[vector_field]
        else:
            # not implemented yet
            vector = None
        if vector is not None:
            if example["is_positive"]:
                positive_vectors.append(vector)
            else:
                negative_vectors.append(vector)

    logging.warning(f"Positive vectors: {len(positive_vectors)}, negative vectors: {len(negative_vectors)}")
    decision_vector = None
    if positive_vectors:
        decision_vector = np.average(positive_vectors, axis=0)
        # if negative_vectors:
        #    decision_vector -= np.average(negative_vectors, axis=0)

    if decision_vector is not None:
        logging.warning(f"Decision vector created: {len(decision_vector)} dimensions")
        metrics_without_random_data = None
        metrics_with_random_data = None
        if negative_vectors:
            metrics_without_random_data = get_metrics(decision_vector, positive_vectors, negative_vectors)
        if included_dataset_ids:
            text_search_engine_client = TextSearchEngineClient.get_instance()
            negative_items_per_dataset = 20
            random_negative_vectors = []
            for dataset_id, vector_field in included_dataset_ids:
                dataset = get_dataset(dataset_id)
                random_items = text_search_engine_client.get_random_items(
                    dataset.actual_database_name, negative_items_per_dataset, []
                )
                is_array_field = dataset.schema.object_fields[vector_field].is_array
                results = vector_db_client.get_items_by_ids(
                    dataset,
                    [e["_id"] for e in random_items],
                    vector_field,
                    is_array_field,
                    return_vectors=True,
                    return_payloads=False,
                )
                for result in results:
                    vector = result.vector[vector_field]
                    random_negative_vectors.append(vector)
                # TODO: if vectors not in database, create them here on-the-fly
            if random_negative_vectors:
                negative_vectors = np.array(negative_vectors)
                random_negative_vectors = np.array(random_negative_vectors)
                negative_vectors = (
                    np.concatenate([negative_vectors, random_negative_vectors])
                    if len(negative_vectors) > 0
                    else random_negative_vectors
                )
                metrics_with_random_data = get_metrics(decision_vector, positive_vectors, negative_vectors)
        metrics = {
            "without_random_data": metrics_without_random_data,
            "with_random_data": metrics_with_random_data,
        }
        highest_score = metrics_without_random_data["highest_score"] if metrics_without_random_data else None
        best_threshold = metrics_without_random_data["best_threshold"] if metrics_without_random_data else None
        set_trained_classifier(
            collection_id,
            class_name,
            embedding_space_identifier,
            decision_vector.tolist(),
            highest_score,
            best_threshold,
            metrics,
        )
    else:
        logging.warning(f"Decision vector not created")

    RETRAINING_TASKS[task_id]["status"] = "done"
    RETRAINING_TASKS[task_id]["time_finished"] = time.time()


def get_metrics(decision_vector, positive_vectors, negative_vectors):
    positive_scores = np.dot(positive_vectors, decision_vector)
    negative_scores = np.dot(negative_vectors, decision_vector)
    all_scores = np.concatenate([positive_scores, negative_scores])
    all_labels = np.concatenate([np.ones(len(positive_scores)), np.zeros(len(negative_scores))])
    thresholds = np.sort(all_scores)
    # using midpoints between scores as thresholds:
    # for i in range(1, len(thresholds)):
    #     thresholds[i] = (thresholds[i - 1] + thresholds[i]) / 2
    best_f1 = 0
    best_threshold = 0
    best_precision = 0
    best_recall = 0
    epsilon = 1e-10
    for threshold in thresholds:
        predictions = all_scores > threshold
        true_positives = np.sum(predictions * all_labels)
        false_positives = np.sum(predictions * (1 - all_labels))
        false_negatives = np.sum((1 - predictions) * all_labels)
        precision = true_positives / (true_positives + false_positives + epsilon)
        recall = true_positives / (true_positives + false_negatives + epsilon)
        f1 = 2 * precision * recall / (precision + recall + epsilon)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
            best_precision = precision
            best_recall = recall
    metrics = {
        "highest_score": np.max(positive_scores),
        "best_f1": best_f1,
        "best_threshold": best_threshold,
        "best_precision": best_precision,
        "best_recall": best_recall,
    }
    return metrics


def _calculate_decision_vector_and_best_threshold_and_metrics(collection_id, class_name, embedding_space_identifier):
    # a) binary (single class, pos, neg): do below
    # b) multi class, single output (classification): get all vectors, train together (use other pos as strong neg)
    # c) multi class, multi output (tagging): do below for each class (use other pos as weak neg)
    # a and c are same thing

    # for collection and each parent: (or use decision vec from parent, recursive, if not deep_train flag?)
    # get all collection items
    # plus: examples from positive and negative annotation field (overrriden by examples), needs paging (not all at once)

    # for each example, get embedding and weighting
    # - ds and item_id: if embedding is in default_search fields (or field set in overrides), take that (what if there are two, for image and text?)
    # - ds and item_id: if set of default_search_fields matches source fields of an embeddings in the correct space (even if not in def.fields.), use that
    # - ds and item_id: if not, either look for embedding in other fields, or join source fields of default search fields and create embedding from that
    # - plain text: create embedding
    # - image url: create embedding
    # - vector: use if embedding space matches

    # -> list of vectors + weightings for pos and neg

    # a) take weighted average of pos, substract avg of neg?
    # then apply to both to get scores and take middle between pos and neg as threshold, calculate metrics

    # b) train a single layer, dot product network to optimize loss between pos (1.0) and neg (0.0)
    # walk through thresholds (AUC) and take the one with best F1 score

    # return decision_vector, threshold, metrics
    pass
