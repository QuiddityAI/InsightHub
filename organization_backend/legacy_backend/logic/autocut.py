import logging

import numpy as np

from ..utils.helpers import normalize_array


class AutocutStrategy(object):
    KNEE_POINT = "knee_point"
    NEAREST_NEIGHBOUR_DISTANCE_RATIO = "nearest_neighbour_distance_ration"
    STATIC_THRESHOLD = "static_threshold"


def get_number_of_useful_items(scores: list[float], min_items: int, strategy: str, min_score: float = 0.5, max_relative_decline: float = 1.0) -> dict:
    scores_np = np.array(scores)
    if len(scores) == 0 or len(scores) <= min_items:
        return {"count": len(scores), "reason": "l"}
    if scores[0] < min_score:
        # If the first score is already below the minimum score it means that none of
        # the results were relevant.
        # In this case, looking for the knee point (or any other strategy) would return
        # a wrong result (maybe even at the end of the list).
        return {"count": min_items, "reason": "scores are below minimum"}
    if strategy == AutocutStrategy.STATIC_THRESHOLD:
        count = max(min_items, int(np.argmin(np.abs(scores_np - min_score))))
        return {"count": count, "reason": "static threshold"}
    elif strategy == AutocutStrategy.KNEE_POINT:
        return _get_number_of_useful_items_using_knee_point(scores_np, min_items)
    elif strategy == AutocutStrategy.NEAREST_NEIGHBOUR_DISTANCE_RATIO:
        return _get_number_of_useful_items_using_distance_difference(scores_np, min_items, max_relative_decline)
    else:
        logging.error(f"Unknown autocut strategy: {strategy}")
        return {"count": len(scores), "reason": "unknown strategy"}


def _get_number_of_useful_items_using_knee_point(scores: np.ndarray, min_items: int) -> dict:
    assert len(scores) > max(min_items, 1)
    normalized_scores = normalize_array(scores)
    count = len(scores)
    difference_to_diagonal = normalized_scores - (count - np.array(range(count))) / count
    if np.max(np.abs(difference_to_diagonal)) < 0.05:
        # the curve is almost linear, the knee point would not be reliable
        # (linear could mean that all results are relevant or none, but as all are
        # above the min_score (see above), it is asssumed that all are relevant)
        return {"count": count, "reason": "curve is almost flat"}
    if difference_to_diagonal[len(scores) // 2] > 0:
        # concave ("knee"), scores are always decreasing
        index = int(np.argmax(difference_to_diagonal))
        count = max(index, min_items)
        return {"count": count, "reason": f"knee point of concave curve {index}"}
    else:
        # convex ("ellbow"), scores are always decreasing
        index = int(np.argmin(difference_to_diagonal))
        count = max(index, min_items)
        return {"count": count, "reason": f"ellbow point of convex curve {index}"}


def _get_number_of_useful_items_using_distance_difference(scores: np.ndarray, min_items: int, max_relative_decline: float) -> dict:
    # max_relative_decline is the maximum allowed decrease in the score from one element to the next
    # with 1.0 meaning that for the normalized scores (!) the "angle" to the next element should
    # not be greater than 45° (a gradient of -1)
    # (this is not the actual "Nearest Neighbour Distance Ration" algorithm, for that
    # see here: https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-statistics/h-how-average-nearest-neighbor-distance-spatial-st.htm)
    assert len(scores) > max(min_items, 1)
    normalized_scores = normalize_array(scores)
    diff_to_next_item = np.abs(np.diff(normalized_scores))
    max_diff = max_relative_decline / (len(scores) - 1)
    above_threshold = diff_to_next_item > max_diff
    if not np.any(above_threshold):
        # none of the difference is larger then the threshold
        # -> consider all elements to be relevant
        return {"count": len(scores), "reason": "difference is small everywhere"}
    first_index_above_threshold = int(np.argmax(above_threshold)) + 1
    count = max(first_index_above_threshold, min_items)
    return {"count": count, "reason": f"first item with diff above threshold {first_index_above_threshold}"}
