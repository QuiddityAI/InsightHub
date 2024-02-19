
# when using classifier class to color an attribute, it must have a version / last changed date in parameters to make caching work

# simple use cases:
# - use classifier class (e.g. review paper) for saturation (or secondary opacity) property
#   but what if map by title but colorize by classifier on image embedding?
# - show classifier scores / tags in details modal (based on default search fields or overrides)
# - show recommendations / search by classifier class (based on default search fields or overrides)

# workflow:
# - retrain button (per class, for all - but what if only one class of 10k tags changed? solved, if no annotation field is used)


import copy
from threading import Thread
import time

from utils.dotdict import DotDict

from database_client.django_client import get_classifier, get_dataset


def get_decision_vector(classifier_id, class_name, embedding_space_id):
    classifier = get_classifier(classifier_id)
    assert classifier is not None
    if not classifier.trained_classifiers:
        return None
    # TODO: decision_vectors might be stripped from classifier, might need to retrieve them separately
    decision_vector = classifier.trained_classifiers.get(embedding_space_id, {}).get(class_name, {}).get('decision_vector')
    return decision_vector


def _get_embedding_space_id_from_ds_and_field(ds_and_field: tuple[int, str]):
    dataset: DotDict = get_dataset(ds_and_field[0])
    field = dataset.object_fields[ds_and_field[1]]
    embedding_space_id = field.generator.embedding_space.id if field.generator else field.embedding_space.id
    return embedding_space_id


def get_training_status(classifier_id: int, class_name: str, target_vector_ds_and_field: tuple[int, str]):
    embedding_space_id = _get_embedding_space_id_from_ds_and_field(target_vector_ds_and_field)
    classifier = get_classifier(classifier_id)
    assert classifier is not None
    time_updated = None
    if classifier.trained_classifiers:
        time_updated = classifier.trained_classifiers.get(embedding_space_id, {}).get(class_name, {}).get('time_updated')
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
    embedding_space_id = _get_embedding_space_id_from_ds_and_field(target_vector_ds_and_field)
    thread = Thread(target=_retrain, args=(classifier_id, class_name, embedding_space_id, deep_train))
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


def _retrain(classifier_id, class_name, embedding_space_id, deep_train=False):
    # if deep_train, retrain using examples instead of decision vectors from parent classifiers
    # get all examples for class
    # get all embeddings for examples
    # train classifier
    # store classifier, best threshold, metrics

    classifier = get_classifier(classifier_id)



    for i in range (10):
        RETRAINING_TASKS[classifier_id]['progress'] = i / 10.0
        time.sleep(0.3)


    RETRAINING_TASKS[classifier_id]['status'] = 'done'
    RETRAINING_TASKS[classifier_id]['time_finished'] = time.time()


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
