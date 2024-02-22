
# when using classifier class to color an attribute, it must have a version / last changed date in parameters to make caching work

# simple use cases:
# - use classifier class (e.g. review paper) for saturation (or secondary opacity) property
#   but what if map by title but colorize by classifier on image embedding?
# - show classifier scores / tags in details modal (based on default search fields or overrides)
# - show recommendations / search by classifier class (based on default search fields or overrides)

# workflow:
# - retrain button (per class, for all - but what if only one class of 10k tags changed? solved, if no annotation field is used)


import copy
from itertools import chain
import json
import logging
from threading import Thread
import time

import numpy as np

from utils.dotdict import DotDict
from utils.field_types import FieldType

from database_client.django_client import get_classifier, get_classifier_examples, get_dataset, get_classifier_decision_vector, set_classifier_decision_vector
from database_client.vector_search_engine_client import VectorSearchEngineClient
from database_client.text_search_engine_client import TextSearchEngineClient
from logic.extract_pipeline import get_pipeline_steps
from logic.generate_missing_values import generate_missing_values_for_given_elements
from logic.search import get_document_details_by_id


def get_embedding_space_from_ds_and_field(ds_and_field: tuple[int, str]) -> DotDict:
    dataset: DotDict = get_dataset(ds_and_field[0])
    field = dataset.object_fields[ds_and_field[1]]
    embedding_space = field.generator.embedding_space if field.generator else field.embedding_space
    return DotDict(embedding_space)


def get_training_status(classifier_id: int, class_name: str, target_vector_ds_and_field: tuple[int, str]):
    embedding_space_id = get_embedding_space_from_ds_and_field(target_vector_ds_and_field).id
    classifier = get_classifier(classifier_id)
    assert classifier is not None
    time_updated = None
    if classifier.trained_classifiers:
        time_updated = classifier.trained_classifiers.get(str(embedding_space_id), {}).get(class_name, {}).get('time_updated')
    status = {
        'embedding_space_id': embedding_space_id,
        'time_updated': time_updated,
    }
    return status


RETRAINING_TASKS = {}  # classifier_id -> task status (class name, progress)


def get_retraining_status(classifier_id):
    status = copy.copy(RETRAINING_TASKS.get(classifier_id))
    if isinstance(status, dict):
        if 'thread' in status:
            del status['thread']
        if status['status'] == 'done':
            del RETRAINING_TASKS[classifier_id]
    return status


def start_retrain(classifier_id: int, class_name: str, target_vector_ds_and_field: tuple[int, str], deep_train=False):
    embedding_space_id = get_embedding_space_from_ds_and_field(target_vector_ds_and_field).id
    thread = Thread(target=_retrain_safe, args=(classifier_id, class_name, embedding_space_id, deep_train))
    RETRAINING_TASKS[classifier_id] = {
        'class_name': class_name,
        'progress': 0,
        'status': 'running',
        'error': '',
        'thread': thread,
        'time_finished': None,
    }
    thread.start()
    # general clean up: delete other status after 5 minutes:
    for other_classifier_id, other_status in RETRAINING_TASKS.items():
        if other_status.get('time_finished') and time.time() - other_status['time_finished'] > 300:
            del RETRAINING_TASKS[other_classifier_id]


def _retrain_safe(classifier_id, class_name, embedding_space_id, deep_train=False):
    # if deep_train, retrain using examples instead of decision vectors from parent classifiers
    # get all examples for class
    # get all embeddings for examples
    # train classifier
    # store classifier, best threshold, metrics

    try:
        _retrain(classifier_id, class_name, embedding_space_id, deep_train)
    except Exception as e:
        RETRAINING_TASKS[classifier_id]['status'] = 'error'
        RETRAINING_TASKS[classifier_id]['error'] = str(e)
        RETRAINING_TASKS[classifier_id]['time_finished'] = time.time()
        logging.exception(e)


def _retrain(classifier_id, class_name, embedding_space_id, deep_train=False):
    # rudimentary implementation just for simple case of non-exclusive classes and item_id examples:
    classifier = get_classifier(classifier_id)
    assert classifier is not None
    examples = get_classifier_examples(classifier_id, class_name, field_type=None, is_positive=None)
    positive_vectors = []
    negative_vectors = []
    vector_db_client = VectorSearchEngineClient.get_instance()
    included_dataset_ids = set()
    for i, example in enumerate(examples):
        RETRAINING_TASKS[classifier_id]['progress'] = i / len(examples)
        vector = None
        if example['field_type'] == FieldType.IDENTIFIER:
            dataset_id, item_id = json.loads(example['value'])
            # TODO: batch process
            dataset = get_dataset(dataset_id)
            source_fields = []
            dataset_specific_settings = next(filter(lambda item: item.dataset_id == dataset_id, classifier.dataset_specific_settings), None)
            vector_field = None
            if dataset_specific_settings:
                source_fields = dataset_specific_settings.relevant_object_fields
            else:
                source_fields = dataset.default_search_fields
            for field_name in chain(source_fields, dataset.object_fields.keys()):
                if field_name in dataset.object_fields:
                    field = dataset.object_fields[field_name]
                    try:
                        field_embedding_space_id = field.generator.embedding_space.id if field.generator else field.embedding_space.id
                    except AttributeError:
                        field_embedding_space_id = None
                    if embedding_space_id == field_embedding_space_id:
                        vector_field = field.identifier
                        break
            if vector_field:
                included_dataset_ids.add((dataset_id, vector_field))
                try:
                    logging.warning(f'Getting vector for {dataset_id} {item_id} {vector_field}')
                    results = vector_db_client.get_items_by_ids(dataset_id, [item_id], vector_field, return_vectors=True, return_payloads=False)
                except Exception as e:
                    logging.warning(e)
                    results = []
                if len(results) >= 1 and results[0].id == item_id:
                    vector = results[0].vector[vector_field]
                if not vector:
                    pipeline_steps, required_fields, _ = get_pipeline_steps(dataset, only_fields=[vector_field])
                    item = get_document_details_by_id(dataset_id, item_id, fields=tuple(required_fields))
                    assert item is not None
                    generate_missing_values_for_given_elements(pipeline_steps, [item])
                    vector = item[vector_field]
        else:
            # not implemented yet
            vector = None
        if vector is not None:
            if example['is_positive']:
                positive_vectors.append(vector)
            else:
                negative_vectors.append(vector)

    logging.warning(f"Positive vectors: {len(positive_vectors)}, negative vectors: {len(negative_vectors)}")
    decision_vector = None
    if positive_vectors:
        decision_vector = np.average(positive_vectors, axis=0)
        #if negative_vectors:
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
                random_items = text_search_engine_client.get_random_items(dataset_id, negative_items_per_dataset, [])
                results = vector_db_client.get_items_by_ids(dataset_id, [e['_id'] for e in random_items], vector_field, return_vectors=True, return_payloads=False)
                for result in results:
                    vector = result.vector[vector_field]
                    random_negative_vectors.append(vector)
                # TODO: if vectors not in database, create them here on-the-fly
            if random_negative_vectors:
                negative_vectors = np.array(negative_vectors)
                random_negative_vectors = np.array(random_negative_vectors)
                negative_vectors = np.concatenate([negative_vectors, random_negative_vectors]) if len(negative_vectors) > 0 else random_negative_vectors
                metrics_with_random_data = get_metrics(decision_vector, positive_vectors, negative_vectors)
        metrics = {
            'without_random_data': metrics_without_random_data,
            'with_random_data': metrics_with_random_data,
        }
        set_classifier_decision_vector(classifier_id, class_name, embedding_space_id, decision_vector.tolist(), metrics)
    else:
        logging.warning(f"Decision vector not created")


    RETRAINING_TASKS[classifier_id]['status'] = 'done'
    RETRAINING_TASKS[classifier_id]['time_finished'] = time.time()


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
        'highest_score': np.max(positive_scores),
        'best_f1': best_f1,
        'best_threshold': best_threshold,
        'best_precision': best_precision,
        'best_recall': best_recall,
    }
    return metrics


def _calculate_decision_vector_and_best_threshold_and_metrics(classifier_id, class_name, embedding_space_id):
    # a) binary (single class, pos, neg): do below
    # b) multi class, single output (classification): get all vectors, train together (use other pos as strong neg)
    # c) multi class, multi output (tagging): do below for each class (use other pos as weak neg)
    # a and c are same thing

    # for classifier and each parent: (or use decision vec from parent, recursive, if not deep_train flag?)
    # get all classifier examples
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
