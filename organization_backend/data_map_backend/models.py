from collections import defaultdict
import copy
import datetime
import json
import logging
import threading

import numpy as np
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
import requests

from simple_history.models import HistoricalRecords

from .data_backend_client import data_backend_url, get_item_by_id
from .chatgpt_client import get_chatgpt_response_using_history


class FieldType(models.TextChoices):
    TEXT = "TEXT", "Text"
    IDENTIFIER = "IDENTIFIER", "Identifier"
    FLOAT = "FLOAT", "Float"
    INTEGER = "INTEGER", "Integer"
    DATE = "DATE", "Date"
    DATETIME = "DATETIME", "Datetime"
    TIME = "TIME", "Time"
    VECTOR = "VECTOR", "Vector"
    CLASS_PROBABILITY = "CLASS_PROBABILITY", "Class Probability"
    FACE = "FACE", "Face"
    URL = "URL", "URL"
    GEO_COORDINATES = "GEO_COORDINATES", "Geo Coordinates"
    TAG = "TAG", "Tag"
    IMAGE = "IMAGE", "Image"
    AUDIO = "AUDIO", "Audio"
    VIDEO = "VIDEO", "Video"
    FOREIGN_KEY = "FOREIGN_KEY", "Reference to other element"
    BOOL = "BOOL", "Bool"
    ATTRIBUTES = "ATTRIBUTES", "Attributes (dict)"
    ARBITRARY_OBJECT = "ARBITRARY_OBJECT", "Non-indexed object"


class LanguageAnalysis(models.TextChoices):
    ENGLISH = "english", "English"
    GERMAN = "german", "German"
    FRENCH = "french", "French"
    SPANISH = "spanish", "Spanish"
    CZECH = "czech", "Czech"
    RUSSIAN = "russian", "Russian"
    HINDI = "hindi", "Hindi"


class SourcePlugin(models.TextChoices):
    INTERNAL_OPENSEARCH_QDRANT = "INTERNAL_OPENSEARCH_QDRANT", "Internal DB (OpenSearch + Qdrant)"
    BRAVE_WEB_API = "BRAVE_WEB_API", "Brave Web Search API"
    BING_WEB_API = "BING_WEB_API", "Bing Web Search API"
    SEMANTIC_SCHOLAR_API = "SEMANTIC_SCHOLAR_API", "Semantic Scholar API"


class EmbeddingSpace(models.Model):
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=False,
        null=False)
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        blank=True,
        null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False)
    dimensions = models.IntegerField(
        verbose_name="Dimensions",
        help_text="Vector size of the embedding",
        blank=False,
        null=False)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Embedding Space"
        verbose_name_plural = "Embedding Spaces"


class Generator(models.Model):
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=False,
        null=False)
    description = models.TextField(
        verbose_name="Description",
        blank=True,
        null=True)
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        blank=True,
        null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False)
    requires_context = models.BooleanField(
        verbose_name="Requires context",
        default=False,
        blank=False,
        null=False)
    module = models.CharField(
        verbose_name="Module",
        max_length=200,
        blank=False,
        null=False)
    embedding_space = models.ForeignKey(
        verbose_name="Embedding Space",
        to=EmbeddingSpace,
        on_delete=models.PROTECT,
        blank=True,
        null=True)
    is_preferred_for_search = models.BooleanField(
        verbose_name="Is preferred for search",
        help_text="Enabled this if this generator is optimized for short search queries",
        default=False,
        blank=False,
        null=False)
    default_parameters = models.JSONField(
        verbose_name="Default Parameters",
        blank=True,
        null=True)
    parameter_description = models.TextField(
        verbose_name="Parameter Description",
        blank=True,
        null=True)
    input_type = models.CharField(
        verbose_name="Input Type",
        max_length=50,
        choices=FieldType.choices,
        default=FieldType.TEXT,
        blank=False,
        null=False)
    input_is_array = models.BooleanField(
        verbose_name="Input is array / can be multiple",
        default=False,
        blank=False,
        null=False)
    input_description = models.TextField(
        verbose_name="Input Description",
        blank=True,
        null=True)
    output_type = models.CharField(
        verbose_name="Output Type",
        max_length=50,
        choices=FieldType.choices,
        default=FieldType.VECTOR,
        blank=False,
        null=False)
    output_is_array = models.BooleanField(
        verbose_name="Output is array / can be multiple",
        default=False,
        blank=False,
        null=False)
    output_description = models.TextField(
        verbose_name="Output Description",
        blank=True,
        null=True)
    text_similarity_threshold = models.FloatField(
        verbose_name="Text Similarity Threshold",
        help_text="The minimum score / similarity a text query must have compared to this field to be considered relevant / similar",
        blank=True,
        null=True)
    image_similarity_threshold = models.FloatField(
        verbose_name="Image Similarity Threshold",
        help_text="The minimum score / similarity an image query must have compared to this field to be considered relevant / similar",
        blank=True,
        null=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Generator"
        verbose_name_plural = "Generators"


class Organization(models.Model):
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=False,
        null=False)
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        blank=True,
        null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False)
    members = models.ManyToManyField(
        verbose_name="Members",
        to=User,
        blank=True)
    default_dataset_selection = models.ManyToManyField(
        verbose_name="Default Dataset Selection",
        help_text="",
        to='Dataset',
        related_name='+',
        blank=True)
    workspace_tool_title = models.CharField(
        verbose_name="Workspace Tool Title",
        help_text="Title of the workspace tool in the frontend",
        max_length=40,
        blank=True,
        null=True)
    workspace_tool_logo_url = models.CharField(
        verbose_name="Workspace Tool Logo URL",
        help_text="URL of the workspace tool logo in the frontend",
        max_length=200,
        blank=True,
        null=True)
    workspace_tool_intro_text = models.TextField(
        verbose_name="Workspace Tool Intro Text",
        help_text="Intro text of the workspace tool, HTML is allowed",
        blank=True,
        null=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"


class ImportConverter(models.Model):
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=False,
        null=False)
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        blank=True,
        null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False)
    description = models.TextField(
        verbose_name="Description",
        blank=True,
        null=True)
    module = models.CharField(
        verbose_name="Code Module Name",
        max_length=200,
        blank=False,
        null=False)
    parameters = models.JSONField(
        verbose_name="Parameters",
        default=dict,
        blank=True,
        null=True)
    example_file_url = models.CharField(
        verbose_name="Example File URL",
        max_length=200,
        blank=True,
        null=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Import Converter"
        verbose_name_plural = "Import Converters"


def get_rendering_json_field_default(fields: list):
    val = {}
    val["required_fields"] = []
    for field in fields:
        val[field] = "(item) => { return null }"
    return val

def get_default_result_list_rendering():
    return get_rendering_json_field_default(['title', 'subtitle', 'body', 'image', 'url'])

# deprecated, but needed for old migrations
def get_default_collection_list_rendering():
    return get_rendering_json_field_default(['title', 'subtitle', 'body', 'image', 'url'])

def get_default_collection_item_rendering():
    return get_rendering_json_field_default(['title', 'subtitle', 'body', 'image', 'url'])

def get_default_hover_label_rendering():
    return get_rendering_json_field_default(['title', 'subtitle', 'image'])

def get_default_detail_view_rendering():
    return get_rendering_json_field_default(['title', 'subtitle', 'body', 'image', 'url'])


class Dataset(models.Model):
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=False,
        null=False)
    entity_name = models.CharField(
        verbose_name="Entity Name",
        help_text="The type of the entity, e.g. 'Product' or 'Article'",
        max_length=40,
        blank=True,
        null=True)
    entity_name_plural = models.CharField(
        verbose_name="Entity Name (Plural)",
        max_length=40,
        blank=True,
        null=True)
    short_description = models.CharField(
        verbose_name="Short Description",
        max_length=200,
        blank=True,
        null=True)
    is_template = models.BooleanField(
        verbose_name="Template",
        help_text="Whether this dataset is a schema for creating new datasets in the UI. Templates are not used for data storage.",
        default=False,
        blank=False,
        null=False)
    origin_template = models.ForeignKey(
        verbose_name="Origin Template",
        to='self',
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True)
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        blank=True,
        null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False)
    organization = models.ForeignKey(
        verbose_name="Organization",
        to=Organization,
        on_delete=models.PROTECT,
        related_name="datasets",
        blank=False,
        null=False)
    is_public = models.BooleanField(
        verbose_name="Is public",
        default=False,
        blank=False,
        null=False)
    admins = models.ManyToManyField(
        verbose_name="Admins",
        help_text="Users who can change the dataset and upload items to it",
        to=User,
        related_name='+',
        blank=True)
    source_plugin = models.CharField(
        verbose_name="Source Plugin",
        max_length=50,
        choices=SourcePlugin.choices,
        default=SourcePlugin.INTERNAL_OPENSEARCH_QDRANT,
        blank=False,
        null=False)
    source_plugin_parameters = models.JSONField(
        verbose_name="Source Plugin Parameters",
        default=dict,
        blank=True,
        null=True)
    database_name = models.CharField(
        verbose_name="Database Name",
        help_text="Name of the OpenSearch index and vector DB prefix, using 'dataset_&lt;id&gt;' if empty",
        max_length=100,
        blank=True,
        null=True)
    primary_key = models.ForeignKey(
        verbose_name="Primary Key",
        to='ObjectField',
        related_name='+',
        on_delete=models.SET_NULL,
        blank=True,
        null=True)
    thumbnail_image = models.ForeignKey(
        verbose_name="Thumbnail Image",
        to='ObjectField',
        related_name='+',
        on_delete=models.SET_NULL,
        blank=True,
        null=True)
    descriptive_text_fields = models.ManyToManyField(
        verbose_name="Descriptive Text Fields",
        help_text="For Word2Vec and Cluster Titles",
        to='ObjectField',
        related_name='+',
        blank=True)
    default_search_fields = models.ManyToManyField(
        verbose_name="Default Search Fields",
        help_text="For combined search",
        to='ObjectField',
        related_name='+',
        blank=True)
    defaults = models.JSONField(
        verbose_name="Other Defaults",
        help_text="Default values for map parameters",
        default=dict,
        blank=True,
        null=True)
    applicable_import_converters = models.ManyToManyField(
        verbose_name="Applicable Import Converters",
        to=ImportConverter,
        related_name='+',
        blank=True)
    result_list_rendering = models.JSONField(
        verbose_name="Result List Rendering",
        default=get_default_result_list_rendering,
        blank=True,
        null=True)
    collection_item_rendering =  models.JSONField(
        verbose_name="Collection List Rendering",
        default=get_default_collection_item_rendering,
        blank=True,
        null=True)
    hover_label_rendering =  models.JSONField(
        verbose_name="Hover Label Rendering",
        default=get_default_hover_label_rendering,
        blank=True,
        null=True)
    detail_view_rendering =  models.JSONField(
        verbose_name="Detail View Rendering",
        default=get_default_detail_view_rendering,
        blank=True,
        null=True)
    statistics = models.JSONField(
        verbose_name="Statistics",
        help_text="Statistics shown for the search results",
        default=dict,
        blank=True,
        null=True)

    history = HistoricalRecords()

    @property
    def item_count(self):
        try:
            url = data_backend_url + f'/data_backend/dataset/{self.id}/item_count'  # type: ignore
            result = requests.get(url)
            return result.json()["count"]
        except Exception as e:
            return repr(e)
    item_count.fget.short_description = "Current Item Count"  # type: ignore

    @property
    def random_item(self):
        try:
            url = data_backend_url + f'/data_backend/dataset/{self.id}/random_item'  # type: ignore
            result = requests.get(url)
            item = result.json()["item"]
            for key in item.get("_source", {}).keys():
                if isinstance(item["_source"][key], list) and len(item["_source"][key]) > 50:
                    item["_source"][key] = f"&lt;Array of length {len(item['_source'][key])}&gt;"
            return mark_safe(json.dumps(item, indent=2, ensure_ascii=False).replace(" ", "&nbsp").replace("\n", "<br>"))
        except Exception as e:
            return repr(e)
    random_item.fget.short_description = "Random Item"  # type: ignore

    @property
    def actual_database_name(self):
        return self.database_name or f"dataset_{self.id}"  # type: ignore
    actual_database_name.fget.short_description = "Actual Database Name"  # type: ignore

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"


class ObjectField(models.Model):
    identifier = models.CharField(
        verbose_name="Identifier",
        max_length=200,
        blank=False,
        null=False)
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        blank=True,
        null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False)
    dataset = models.ForeignKey(
        verbose_name="Dataset",
        to=Dataset,
        on_delete=models.CASCADE,
        related_name='object_fields',
        blank=False,
        null=False)
    description = models.CharField(
        verbose_name="Description",
        max_length=200,
        blank=True,
        null=True)
    field_type = models.CharField(
        verbose_name="Type",
        max_length=50,
        choices=FieldType.choices,
        default=FieldType.TEXT,
        blank=False,
        null=False)
    is_array = models.BooleanField(
        verbose_name="Is array",
        default=False,
        blank=False,
        null=False)
    language_analysis = models.CharField(
        verbose_name="Language Processing",
        help_text="Only applicable for 'Text' fields",
        max_length=50,
        choices=LanguageAnalysis.choices,
        blank=True,
        null=True)
    embedding_space = models.ForeignKey(
        verbose_name="Embedding Space",
        help_text="If not set, embedding space of generator will be used",
        to=EmbeddingSpace,
        on_delete=models.PROTECT,
        blank=True,
        null=True)
    is_available_for_search = models.BooleanField(
        verbose_name="Available for fulltext or vector search",
        default=False,
        blank=False,
        null=False)
    text_similarity_threshold = models.FloatField(
        verbose_name="Text Similarity Threshold",
        help_text="The minimum score / similarity a text query must have compared to this field to be considered relevant / similar (overriding the generators value)",
        blank=True,
        null=True)
    image_similarity_threshold = models.FloatField(
        verbose_name="Image Similarity Threshold",
        help_text="The minimum score / similarity an image query must have compared to this field to be considered relevant / similar (overriding the generators value)",
        blank=True,
        null=True)
    is_available_for_filtering = models.BooleanField(
        verbose_name="Available for filtering",
        default=False,
        blank=False,
        null=False)
    index_parameters = models.JSONField(
        verbose_name="Index Parameters",
        blank=True,
        null=True)
    generator = models.ForeignKey(
        verbose_name="Generator",
        to=Generator,
        on_delete=models.PROTECT,
        blank=True,
        null=True)
    generator_parameters = models.JSONField(
        verbose_name="Generator Parameters",
        blank=True,
        null=True)
    generating_condition = models.TextField(
        verbose_name="Generating Condition",
        blank=True,
        null=True)
    source_fields = models.ManyToManyField(
        verbose_name="Source Fields",
        to='self',
        symmetrical=False,
        blank=True)
    should_be_generated = models.BooleanField(
        verbose_name="Generate on insert / change",
        help_text="Should be generated for new elements and when "\
        "source fields are updated, not automatically generated for exisitng elements",
        default=False,
        blank=False,
        null=False)

    history = HistoricalRecords()

    @property
    def items_having_value_count(self):
        if not self.is_available_for_search and not self.is_available_for_filtering:
            # OpenSearch can't easily count values that are not indexed
            return "?"
        try:
            url = data_backend_url + f'/data_backend/dataset/{self.dataset.id}/{self.identifier}/items_having_value_count'  # type: ignore
            result = requests.get(url)
            return result.json()["count"]
        except Exception as e:
            return repr(e)
    items_having_value_count.fget.short_description = "Items having this value"  # type: ignore

    @property
    def actual_embedding_space(self):
        return self.embedding_space or self.generator.embedding_space if self.generator else None
    actual_embedding_space.fget.short_description = "Actual Embedding Space"  # type: ignore

    def __str__(self):
        return f"{self.identifier}"

    class Meta:
        verbose_name = "Object Field"
        verbose_name_plural = "Object Fields"
        order_with_respect_to = "dataset"


class SearchHistoryItem(models.Model):
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=False,
        null=False)
    display_name = models.CharField(
        verbose_name="Display Name",
        help_text="Name to be displayed in the frontend, including HTML markup",
        max_length=300,
        blank=True,
        null=True)
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        blank=False,
        null=False)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False)
    user = models.ForeignKey(
        verbose_name="User",
        to=User,
        on_delete=models.CASCADE,
        blank=False,
        null=False)
    organization = models.ForeignKey(
        verbose_name="Organization",
        to=Organization,
        related_name='+',
        on_delete=models.CASCADE,
        blank=False,
        null=False)
    parameters = models.JSONField(
        verbose_name="Parameters",
        blank=True,
        null=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Search History Item"
        verbose_name_plural = "Search History Items"


class StoredMap(models.Model):
    id = models.CharField(
        verbose_name="ID",
        primary_key=True,
        editable=False,
        max_length=50,
        blank=False,
        null=False)
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=False,
        null=False)
    display_name = models.CharField(
        verbose_name="Display Name",
        help_text="Name to be displayed in the frontend, including HTML markup",
        max_length=300,
        blank=True,
        null=True)
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        blank=False,
        null=False)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False)
    user = models.ForeignKey(
        verbose_name="User",
        to=User,
        on_delete=models.CASCADE,
        blank=False,
        null=False)
    organization = models.ForeignKey(
        verbose_name="Organization",
        to=Organization,
        related_name='+',
        on_delete=models.CASCADE,
        blank=False,
        null=False)
    map_data = models.BinaryField(
        verbose_name="Data",
        blank=True,
        null=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Stored Map"
        verbose_name_plural = "Stored Maps"


def class_field_default():
    return ["_default"]


class DataCollection(models.Model):  # aka DataCollection / DataClassification
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=False,
        null=False)
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        blank=True,
        null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False)
    created_by = models.ForeignKey(
        verbose_name="Created By",
        to=User,
        on_delete=models.CASCADE,
        blank=False,
        null=False)
    is_public = models.BooleanField(
        verbose_name="Is public",
        default=False,
        blank=False,
        null=False)
    related_organization = models.ForeignKey(
        verbose_name="Related Organization",
        help_text="Collections can be used across organizations, but they usually belong to one",
        to=Organization,
        related_name='+',
        on_delete=models.SET_NULL,
        blank=True,
        null=True)
    parent_collection = models.ManyToManyField(  # only their text or image sources are extracted, or vectors if embedding space matches target space
        verbose_name="Parent Collection",
        to='self',
        symmetrical=False,
        blank=True)
    is_binary = models.BooleanField(  # needed? or deduct from class count? but storing is different
        verbose_name="Is binary",
        default=False,
        blank=False,
        null=False)
    allow_multi_class = models.BooleanField(
        verbose_name="Allow multi class",
        default=False,
        blank=False,
        null=False)
    class_names = models.JSONField(
        verbose_name="Class Names",
        help_text="Minimal list of classes shown in the UI, even if no items are present. More classes are deducted from items.",
        default=class_field_default,
        blank=True,
        null=True)
    default_threshold = models.FloatField(
        verbose_name="Default Threshold",
        default=0.5,
        blank=False,
        null=False)
    per_class_thresholds = models.JSONField(
        verbose_name="Per Class Thresholds",
        help_text="block classes e.g. from parents, using weight of -1",
        blank=True,
        null=True)
    items_last_changed = models.JSONField(
        verbose_name="Items Last Changed",
        help_text="For each class, the last time an item was added or removed",
        default=dict,
        blank=True,
        null=True)
    extraction_questions = models.JSONField(
        verbose_name="Extraction Questions",
        help_text="",
        default=list,
        blank=True,
        null=True)
    table_columns = models.JSONField(
        verbose_name="Table Columns",
        help_text="",
        default=list,
        blank=True,
        null=True)
    current_extraction_processes = models.JSONField(
        verbose_name="Current Extraction Processes",
        help_text="",
        default=list,
        blank=True,
        null=True)

    history = HistoricalRecords()

    @property
    def actual_classes(self) -> list:
        classes = defaultdict(lambda: [0, 0])
        for class_name in self.class_names or ['_default']:
            classes[class_name] = [0, 0]
        for example in CollectionItem.objects.filter(collection=self):
            for c in example.classes or ['_default']:
                classes[c][0 if example.is_positive else 1] += 1
        classes_list_of_dicts = []
        for c, v in classes.items():
            classes_list_of_dicts.append({
                "name": c,
                "positive_count": v[0],
                "negative_count": v[1]
            })
        return sorted(classes_list_of_dicts, key=lambda x: x["name"])


    def actual_classes_formatted(self):
        return mark_safe(json.dumps(self.actual_classes, indent=2, ensure_ascii=False).replace(" ", "&nbsp").replace("\n", "<br>"))
    actual_classes_formatted.short_description = "Actual Classes"

    # def simplified_trained_classifiers(self):
    #     data = copy.deepcopy(self.trained_classifiers) or {}
    #     for embedding_space_data in data.values():
    #         for class_name in embedding_space_data:
    #             if "decision_vector" in embedding_space_data[class_name]:
    #                 embedding_space_data[class_name]["decision_vector"] = f"&ltarray of length {len(embedding_space_data[class_name]['decision_vector'])}, stdev {np.std(embedding_space_data[class_name]['decision_vector']):.4f}&gt"
    #     return mark_safe(json.dumps(data, indent=2, ensure_ascii=False).replace(" ", "&nbsp").replace("\n", "<br>"))
    # simplified_trained_classifiers.short_description = "Trained Classifiers"


    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Data Collection"
        verbose_name_plural = "Data Collections"


class DatasetSpecificSettingsOfCollection(models.Model):
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        blank=True,
        null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False)
    collection = models.ForeignKey(
        verbose_name="Collection",
        to=DataCollection,
        on_delete=models.CASCADE,
        related_name='dataset_specific_settings',
        blank=False,
        null=False)
    dataset = models.ForeignKey(
        verbose_name="Dataset",
        to=Dataset,
        on_delete=models.CASCADE,
        related_name='+',
        blank=False,
        null=False)
    relevant_object_fields = models.ManyToManyField(
        verbose_name="Relevant Object Fields",
        help_text="The 'source' fields (text or image) for items from this dataset, using default search fields (or their sources for vectors) if empty",
        to='ObjectField',
        related_name='+',
        blank=True)
    positive_annotation_field = models.ForeignKey(
        verbose_name="Positive Annotation Field",
        help_text="binary: bool field, exclusive: single tag, non-exclusive: tag array field",  # or class probability field (not yet, only makes sense if regression is supported)
        to='ObjectField',
        related_name='+',
        on_delete=models.SET_NULL,
        blank=True,
        null=True)
    negative_annotation_field = models.ForeignKey(
        verbose_name="Negative Annotation Field",
        help_text="binary: bool field, exclusive: single tag, non-exclusive: tag array field",
        to='ObjectField',
        related_name='+',
        on_delete=models.SET_NULL,
        blank=True,
        null=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.collection.name} - {self.dataset.name}"

    class Meta:
        verbose_name = "Dataset Specific Settings"
        verbose_name_plural = "Dataset Specific Settings"
        unique_together = [['collection', 'dataset']]


class CollectionItem(models.Model):
    collection = models.ForeignKey(
        verbose_name="Collection",
        to=DataCollection,
        on_delete=models.CASCADE,
        blank=False,
        null=False)
    date_added = models.DateTimeField(
        verbose_name="Date added",
        default=timezone.now,
        editable=False,
        blank=False,
        null=False)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False)
    is_positive = models.BooleanField(
        verbose_name="Is positive",
        default=True,
        blank=False,
        null=False)
    classes = models.JSONField(
        verbose_name="Classes",
        default=class_field_default,
        blank=False,
        null=False)
    field_type = models.CharField(
        verbose_name="Type",
        help_text="Either IDENTIFIER, TEXT, IMAGE",
        # if you want to store a vector, use a parent collection connected to a dataset with only those vectors
        max_length=50,
        choices=FieldType.choices,
        default=FieldType.TEXT,
        blank=False,
        null=False)
    value = models.TextField(
        verbose_name="Value",
        help_text="Item ID, Text, Image URL",
        blank=True,
        null=True)
    weight = models.FloatField(
        verbose_name="Weight",
        help_text="Weight for this example (e.g. small if just a product page view, high if product was bought)",
        default=1.0,
        blank=False,
        null=False)
    extraction_answers = models.JSONField(
        verbose_name="Extraction Answers",
        help_text="",
        default=dict,
        blank=True,
        null=True)

    # def __str__(self):
    #     return f"{self.name}"

    class Meta:
        verbose_name = "Collection Item"
        verbose_name_plural = "Collection Item"


class TrainedClassifier(models.Model):
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        editable=False,
        blank=False,
        null=False)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False)
    last_retrained_at = models.DateTimeField(
        verbose_name="Last Retrained at",
        blank=True,
        null=True)
    collection = models.ForeignKey(
        verbose_name="Collection",
        to=DataCollection,
        on_delete=models.CASCADE,
        related_name='trained_classifiers',
        blank=False,
        null=False)
    class_name = models.CharField(
        verbose_name="Class",
        max_length=200,
        blank=False,
        null=False)
    embedding_space = models.ForeignKey(
        verbose_name="Embedding Space",
        to=EmbeddingSpace,
        related_name='+',
        on_delete=models.PROTECT,
        blank=False,
        null=False)
    decision_vector = models.JSONField(
        verbose_name="decision_vector",
        blank=True,
        null=True)
    highest_score = models.FloatField(
        verbose_name="Highest Score",
        blank=True,
        null=True)
    threshold = models.FloatField(
        verbose_name="Threshold",
        default=0.5,
        blank=False,
        null=False)
    metrics = models.JSONField(
        verbose_name="Metrics",
        default=dict,
        blank=True,
        null=True)

    history = HistoricalRecords()

    def decision_vector_stats(self):
        if self.decision_vector is None:
            return "No decision vector"
        return f"Length: {len(self.decision_vector)} Mean: {np.mean(self.decision_vector):.3f}, Stdev: {np.std(self.decision_vector):.3f}"
    decision_vector_stats.short_description = "Decision Vector Stats"

    def is_up_to_date(self):
        if self.last_retrained_at is None:
            return False
        items_last_changed = self.collection.items_last_changed.get(self.class_name, timezone.now().isoformat())  # type: ignore
        try:
            items_last_changed = datetime.datetime.fromisoformat(items_last_changed)
        except Exception:
            return False
        return self.last_retrained_at >= items_last_changed  # type: ignore

    def __str__(self):
        return f"{self.collection.name}: {self.class_name} ({self.embedding_space.name})"

    class Meta:
        verbose_name = "Trained Classifier"
        verbose_name_plural = "Trained Classifiers"
        unique_together = [['collection', 'class_name', 'embedding_space']]


class CollectionChat(models.Model):
    collection = models.ForeignKey(
        verbose_name="Collection",
        to=DataCollection,
        on_delete=models.CASCADE,
        blank=False,
        null=False)
    class_name = models.CharField(
        verbose_name="Class",
        max_length=200,
        blank=False,
        null=False)
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        editable=False,
        blank=False,
        null=False)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False)
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=True,
        null=True)
    chat_history = models.JSONField(
        verbose_name="Chat History",
        default=list,
        blank=True,
        null=True)
    is_processing = models.BooleanField(
        verbose_name="Is Processing",
        default=False,
        blank=False,
        null=False)


    def add_question(self, question: str):
        assert isinstance(self.chat_history, list)
        self.chat_history.append({
            "role": "user",
            "content": question,
            "date": timezone.now().isoformat(),
        })
        self.is_processing = True
        self.save()

        obj = self

        def answer_question():
            system_prompt = "You are a helpful assistant. You can answer questions based on the following items. " + \
                "Answer in one concise sentence. Mention the item id you got the answer from in brackets after the sentence. If you need more information, ask for it."
            collection_items = CollectionItem.objects.filter(collection=self.collection)
            included_items = 0
            for item in collection_items:
                if obj.class_name not in item.classes:
                    continue
                text = None
                if item.field_type == FieldType.TEXT:
                    text = json.dumps({"_id": item.id, "text": item.value}, indent=2)  # type: ignore
                if item.field_type == FieldType.IDENTIFIER:
                    ds_id, item_id = json.loads(item.value)  # type: ignore
                    fields = list(Dataset.objects.get(id=ds_id).descriptive_text_fields.all().values_list("identifier", flat=True))
                    fields.append("_id")
                    full_item = get_item_by_id(ds_id, item_id, fields)
                    text = json.dumps(full_item, indent=2)
                if not text:
                    continue
                included_items += 1
                system_prompt += "\n" + text + "\n"
                if included_items > 5:
                    break

            history = []
            history.append({"role": "system", "content": system_prompt})
            for chat_item in obj.chat_history:  # type: ignore
                history.append({
                    "role": chat_item["role"],
                    "content": chat_item["content"],
                })

            response_text = get_chatgpt_response_using_history(history)
            #response_text = "I'm sorry, I can't answer that question yet."

            obj.chat_history.append({  # type: ignore
                "role": "system",
                "content": response_text,
                "date": timezone.now().isoformat(),
            })
            obj.is_processing = False
            obj.save()

        def safe_answer_question():
            obj.is_processing = True
            obj.save()
            try:
                answer_question()
            except Exception as e:
                logging.error("Error in answer_question", e)
                obj.is_processing = False
                obj.save()

        try:
            thread = threading.Thread(target=safe_answer_question)
            thread.start()
        except Exception as e:
            logging.error("Error in add_question", e)
            obj.is_processing = False
            obj.save()
