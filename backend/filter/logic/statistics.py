from data_map_backend.models import DataCollection, Dataset
from data_map_backend.views.other_views import (
    get_dataset_cached,
    get_filtered_collection_items,
)
from legacy_backend.logic.search import get_items_by_ids


def get_statistic_data(
    collection: DataCollection, class_name: str, dataset_id: int, required_fields: list[str], statistic_settings: dict
):
    filtered_collection_items, reference_ds_and_item_id = get_filtered_collection_items(collection, class_name)
    filtered_collection_items = filtered_collection_items.filter(dataset_id=dataset_id)

    dataset: Dataset = get_dataset_cached(dataset_id)
    data_item_ids = [item.item_id for item in filtered_collection_items]
    data_items: list[dict] = get_items_by_ids(dataset.id, data_item_ids, required_fields)  # type: ignore
    items_by_dataset = {dataset_id: {item["_id"]: item for item in data_items}}
    ds_and_item_ids = [(item.dataset_id, item.item_id) for item in filtered_collection_items]

    y_counts = {}
    y_values = {}
    for ds_and_item_id in ds_and_item_ids:
        assert isinstance(ds_and_item_id[0], int)
        assert isinstance(ds_and_item_id[1], str)
        ds_items = items_by_dataset.get(ds_and_item_id[0])
        if not ds_items:
            continue
        item = ds_items.get(ds_and_item_id[1])
        assert item is not None

        categories = (
            item[statistic_settings["x"]]
            if statistic_settings["x_type"] == "array_item_category"
            else [item[statistic_settings["x"]]]
        )
        if categories is None:
            continue
        for category in categories:
            y_counts[category] = y_counts.get(category, 0) + 1
        for y_params in statistic_settings["y"]:
            value = item.get(y_params["field"]) if y_params.get("field") else None
            for category in categories:
                if category not in y_values:
                    y_values[category] = {}
                y_values[category][y_params["name"]] = y_values[category].get(y_params["name"], 0) + (value or 0)

    for y_params in statistic_settings["y"]:
        if y_params["type"] == "mean":
            for category in y_values:
                y_values[category][y_params["name"]] = round(y_values[category][y_params["name"]] / y_counts[category])

    max_columns = statistic_settings.get("max_columns", 20)
    union_of_top_n_categories_per_y = []
    for y_params in statistic_settings["y"]:
        top_n_categories = []
        if y_params["type"] == "mean":
            top_n_categories = sorted(y_counts.keys(), key=lambda k: y_values[k][y_params["name"]], reverse=True)[
                : max_columns // len(statistic_settings["y"])
            ]
        else:
            top_n_categories = sorted(y_counts.keys(), key=lambda k: y_counts[k], reverse=True)[
                : max_columns // len(statistic_settings["y"])
            ]
        union_of_top_n_categories_per_y = list(set(union_of_top_n_categories_per_y + top_n_categories))

    union_of_top_n_categories_per_y.sort(key=lambda k: max(y_values[k].values()) / len(y_values[k]), reverse=True)
    categories = union_of_top_n_categories_per_y
    if statistic_settings.get("order_by") == "x":
        categories.sort()

    series = []
    for y_params in statistic_settings["y"]:
        series.append(
            {
                "name": y_params["name"],
                "data": [
                    y_values[k].get(y_params["name"], 0) if y_params["type"] == "mean" else y_counts.get(k, 0)
                    for k in categories
                ],
            }
        )

    return {
        "categories": categories,
        "series": series,
    }
