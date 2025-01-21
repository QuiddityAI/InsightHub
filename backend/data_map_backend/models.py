from collections import defaultdict
import datetime
import json
import logging
import random
import string
import threading
import os

import numpy as np
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.utils.safestring import mark_safe
import requests

from simple_history.models import HistoricalRecords

from .data_backend_client import (
    DATA_BACKEND_HOST,
    get_item_by_id,
    delete_dataset_content,
    get_global_question_context,
)
from .chatgpt_client import get_chatgpt_response_using_history


BACKEND_AUTHENTICATION_SECRET = os.getenv("BACKEND_AUTHENTICATION_SECRET", "not_set")

# create requests session with BACKEND_AUTHENTICATION_SECRET as header:
backend_client = requests.Session()
backend_client.headers.update({"Authorization": BACKEND_AUTHENTICATION_SECRET})


class FieldType(models.TextChoices):
    TEXT = "TEXT", "Prose Text"
    STRING = "STRING", "Exact String"
    IDENTIFIER = "IDENTIFIER", "Identifier / ID"
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
    TAG = "TAG", "Tag / Keyword / Category"
    IMAGE = "IMAGE", "Image"
    AUDIO = "AUDIO", "Audio"
    VIDEO = "VIDEO", "Video"
    FOREIGN_KEY = "FOREIGN_KEY", "Reference to other element"
    BOOL = "BOOL", "Bool"
    ATTRIBUTES = "ATTRIBUTES", "Attributes (dict)"
    ARBITRARY_OBJECT = "ARBITRARY_OBJECT", "Non-indexed object"
    CHUNK = "CHUNK", "Text Chunk with Metadata"


class LanguageAnalysis(models.TextChoices):
    ENGLISH = "english", "English"
    GERMAN = "german", "German"
    FRENCH = "french", "French"
    SPANISH = "spanish", "Spanish"
    CZECH = "czech", "Czech"
    RUSSIAN = "russian", "Russian"
    HINDI = "hindi", "Hindi"


class SourcePlugin(models.TextChoices):
    INTERNAL_OPENSEARCH_QDRANT = (
        "INTERNAL_OPENSEARCH_QDRANT",
        "Internal DB (OpenSearch + Qdrant)",
    )
    REMOTE_DATASET = "REMOTE_DATASET", "Remote Visual Data Map Dataset"
    BRAVE_WEB_API = "BRAVE_WEB_API", "Brave Web Search API"
    BING_WEB_API = "BING_WEB_API", "Bing Web Search API"
    SEMANTIC_SCHOLAR_API = "SEMANTIC_SCHOLAR_API", "Semantic Scholar API"
    KLEINANZEIGEN = "KLEINANZEIGEN", "Kleinanzeigen Search"


class User(AbstractUser):
    # assume user didn't accept cookies by default
    accepted_cookies = models.BooleanField(verbose_name="Cookies accepted", default=False, blank=False, null=False)

    # # assume user didn't accept sending emails by default
    accepted_emails = models.BooleanField(
        verbose_name="Emails allowed",
        default=False,
        blank=False,
        null=False,
    )

    preferences = models.JSONField(
        verbose_name="Preferences",
        help_text="User preferences",
        default=dict,
        blank=True,
        null=False,
    )

    # if we'll want to include dj-stripe
    # subscription = models.ForeignKey(
    #     "djstripe.Subscription",
    #     null=True,
    #     blank=True,
    #     on_delete=models.SET_NULL,
    #     help_text="The user's Stripe Subscription object, if it exists",
    # )
    # customer = models.ForeignKey(
    #     "djstripe.Customer",
    #     null=True,
    #     blank=True,
    #     on_delete=models.SET_NULL,
    #     help_text="The user's Stripe Customer object, if it exists",
    # )

    def __str__(self):
        return "{}".format(self.email)


class EmbeddingSpace(models.Model):
    identifier = models.CharField(
        verbose_name="Identifier",
        help_text="Do not change this after being used elsewhere",
        max_length=200,
        primary_key=True,
        unique=True,
        blank=False,
        null=False,
    )
    name = models.CharField(verbose_name="Display Name", max_length=200, blank=False, null=False)
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=True, null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    dimensions = models.IntegerField(
        verbose_name="Dimensions",
        help_text="Vector size of the embedding",
        blank=False,
        null=False,
    )

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Embedding Space"
        verbose_name_plural = "Embedding Spaces"


class Generator(models.Model):
    identifier = models.CharField(
        verbose_name="Identifier",
        help_text="Do not change this after being used elsewhere",
        max_length=200,
        primary_key=True,
        unique=True,
        blank=False,
        null=False,
    )
    name = models.CharField(verbose_name="Display Name", max_length=200, blank=False, null=False)
    description = models.TextField(verbose_name="Description", blank=True, null=True)
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=True, null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    requires_context = models.BooleanField(
        verbose_name="Requires context",
        default=False,
        blank=False,
        null=False,
        help_text="Requires a set of other documents, generates a non-universal result",
    )
    requires_multiple_input_fields = models.BooleanField(
        verbose_name="Requires multiple input fields",
        default=False,
        blank=False,
        null=False,
        help_text="Requires multiple different input fields to generate a result",
    )
    returns_multiple_fields = models.BooleanField(
        verbose_name="Returns multiple fields",
        default=False,
        blank=False,
        null=False,
        help_text="Returns multiple different fields as result",
    )
    module = models.CharField(verbose_name="Module", max_length=200, blank=False, null=False)
    embedding_space = models.ForeignKey(
        verbose_name="Embedding Space",
        to=EmbeddingSpace,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    is_preferred_for_search = models.BooleanField(
        verbose_name="Is preferred for search",
        help_text="Enabled this if this generator is optimized for short search queries",
        default=False,
        blank=False,
        null=False,
    )
    default_parameters = models.JSONField(verbose_name="Default Parameters", blank=True, null=True)
    parameter_description = models.TextField(verbose_name="Parameter Description", blank=True, null=True)
    input_type = models.CharField(
        verbose_name="Input Type",
        max_length=50,
        choices=FieldType.choices,
        default=FieldType.TEXT,
        blank=False,
        null=False,
    )
    input_is_array = models.BooleanField(
        verbose_name="Input is array / can be multiple",
        default=False,
        blank=False,
        null=False,
    )
    input_description = models.TextField(verbose_name="Input Description", blank=True, null=True)
    output_type = models.CharField(
        verbose_name="Output Type",
        max_length=50,
        choices=FieldType.choices,
        default=FieldType.VECTOR,
        blank=False,
        null=False,
    )
    output_is_array = models.BooleanField(
        verbose_name="Output is array / can be multiple",
        default=False,
        blank=False,
        null=False,
    )
    output_description = models.TextField(verbose_name="Output Description", blank=True, null=True)
    text_similarity_threshold = models.FloatField(
        verbose_name="Text Similarity Threshold",
        help_text="The minimum score / similarity a text query must have compared to this field to be considered relevant / similar",
        blank=True,
        null=True,
    )
    image_similarity_threshold = models.FloatField(
        verbose_name="Image Similarity Threshold",
        help_text="The minimum score / similarity an image query must have compared to this field to be considered relevant / similar",
        blank=True,
        null=True,
    )

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Generator"
        verbose_name_plural = "Generators"


class Organization(models.Model):
    name = models.CharField(verbose_name="Name", max_length=200, blank=False, null=False)
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=True, null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    members = models.ManyToManyField(verbose_name="Members", to=User, blank=True)
    is_public = models.BooleanField(
        verbose_name="Is public",
        help_text="Whether this organization is visible to everyone on the internet",
        default=False,
        blank=False,
        null=False,
    )
    domains = models.JSONField(
        verbose_name="Domains",
        help_text="List of domains where this organization is visible",
        default=list,
        blank=True,
        null=False,
    )
    default_dataset_selection = models.ManyToManyField(
        verbose_name="Default Dataset Selection",
        help_text="",
        to="Dataset",
        related_name="+",
        blank=True,
    )
    schemas_for_user_created_datasets = models.ManyToManyField(
        verbose_name="Schemas for User-Created Datasets",
        help_text="",
        to="DatasetSchema",
        related_name="+",
        blank=True,
    )
    # --- Whitelabeling: ---
    tool_title = models.CharField(
        verbose_name="Tool Title",
        help_text="Title of the tool in the frontend",
        max_length=80,
        blank=True,
        null=True,
    )
    tool_logo_url = models.CharField(
        verbose_name="Tool Logo URL",
        help_text="URL of the tool logo in the frontend",
        max_length=200,
        blank=True,
        null=True,
    )
    tool_intro_text = models.TextField(
        verbose_name="Tool Intro Text",
        help_text="Intro text of the tool, HTML is allowed",
        blank=True,
        null=True,
    )
    tool_accent_color = models.CharField(
        verbose_name="Tool Accent Color (Hex)",
        help_text="Accent color of the tool in the frontend, e.g. #ff0000",
        max_length=7,
        blank=True,
        null=True,
    )

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"


class ImportConverter(models.Model):
    display_name = models.CharField(verbose_name="Name", max_length=200, blank=False, null=False)
    identifier = models.CharField(
        verbose_name="Identifier",
        help_text="Do not change this after being used elsewhere",
        max_length=200,
        unique=True,
        primary_key=True,
        blank=False,
        null=False,
    )
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=True, null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    description = models.TextField(verbose_name="Description", blank=True, null=True)
    module = models.CharField(verbose_name="Code Module Name", max_length=200, blank=False, null=False)
    parameters = models.JSONField(verbose_name="Parameters", default=dict, blank=True, null=True)
    example_file_url = models.CharField(verbose_name="Example File URL", max_length=200, blank=True, null=True)
    manual_insert_form = models.JSONField(
        verbose_name="Manual Insert Form",
        help_text='A list of fields like [{"identifier": "field_name", "label": "Field Label", "type": "text", "required": true}]',
        default=list,
        blank=True,
        null=True,
    )

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.display_name}"

    class Meta:
        verbose_name = "Import Converter"
        verbose_name_plural = "Import Converters"


class ExportConverter(models.Model):
    display_name = models.CharField(verbose_name="Name", max_length=200, blank=False, null=False)
    identifier = models.CharField(
        verbose_name="Identifier",
        help_text="Do not change this after being used elsewhere",
        max_length=200,
        primary_key=True,
        unique=True,
        blank=False,
        null=False,
    )
    universally_applicable = models.BooleanField(
        verbose_name="Universally Applicable",
        help_text="Whether this converter is applicable to all datasets",
        default=False,
        blank=False,
        null=False,
    )
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=True, null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    description = models.TextField(verbose_name="Description", blank=True, null=True)
    module = models.CharField(verbose_name="Code Module Name", max_length=200, blank=False, null=False)
    parameters = models.JSONField(verbose_name="Parameters", default=dict, blank=True, null=True)
    preview_as_text = models.BooleanField(
        verbose_name="Preview as text",
        help_text="If the result should be shown in the UI as text in addition to a download link",
        default=False,
        blank=False,
        null=False,
    )

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.display_name}"

    class Meta:
        verbose_name = "Export Converter"
        verbose_name_plural = "Export Converters"


def get_rendering_json_field_default(fields: list):
    val = {}
    val["required_fields"] = []
    for field in fields:
        val[field] = "(item) => { return null }"
    return val


def get_default_result_list_rendering():
    return get_rendering_json_field_default(["title", "subtitle", "body", "image", "url"])


# deprecated, but needed for old migrations
def get_default_collection_list_rendering():
    return get_rendering_json_field_default(["title", "subtitle", "body", "image", "url"])


def get_default_collection_item_rendering():
    return get_rendering_json_field_default(["title", "subtitle", "body", "image", "url"])


def get_default_hover_label_rendering():
    return get_rendering_json_field_default(["title", "subtitle", "image"])


def get_default_detail_view_rendering():
    return get_rendering_json_field_default(["title", "subtitle", "body", "image", "url"])


def get_default_translated_entity_name():
    return {"singular": {}, "plural": {}}


class DatasetSchema(models.Model):
    identifier = models.CharField(
        verbose_name="Identifier",
        help_text="Do not change this after being used elsewhere (or after creating fields, its the PK)",
        max_length=200,
        primary_key=True,
        unique=True,
        blank=False,
        null=False,
    )
    name = models.CharField(verbose_name="Display Name", max_length=200, blank=False, null=False)
    entity_name = models.CharField(
        verbose_name="Entity Name",
        help_text="The type of the entity, e.g. 'Product' or 'Article'",
        max_length=40,
        blank=True,
        null=True,
    )
    entity_name_plural = models.CharField(verbose_name="Entity Name (Plural)", max_length=40, blank=True, null=True)
    translated_entity_name = models.JSONField(
        verbose_name="Translated Entity Name",
        help_text="Translations of the entity name, e.g. {'singular': {'de': 'Produkt', 'fr': 'Produit'}, 'plural': {'de': 'Produkte', 'fr': 'Produits'}}",
        default=get_default_translated_entity_name,
        blank=True,
        null=False,
    )
    short_description = models.CharField(verbose_name="Short Description", max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=True, null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    primary_key = models.CharField(
        verbose_name="Primary Key",
        help_text="If set, this field is used to generate the internal '_id' field consistently, otherwise its a random UUID",
        max_length=200,
        blank=True,
        null=True,
    )
    direct_parent = models.CharField(
        verbose_name="Direct Parent",
        help_text="Field that contains the PK of the direct parent",
        max_length=200,
        blank=True,
        null=True,
    )
    all_parents = models.CharField(
        verbose_name="All Parents",
        help_text="Field that contains the PKs of all parents as an array",
        max_length=200,
        blank=True,
        null=True,
    )
    is_group_field = models.CharField(
        verbose_name="Is Group Field",
        help_text="Bool field that indicates if the item can have children",
        max_length=200,
        blank=True,
        null=True,
    )
    thumbnail_image = models.CharField(
        verbose_name="Thumbnail Image",
        help_text="Should point to a field with an image URL",
        max_length=200,
        blank=True,
        null=True,
    )
    descriptive_text_fields = models.JSONField(
        verbose_name="Descriptive Text Fields",
        help_text="For Word2Vec, Cluster Titles and more",
        default=list,
        blank=True,
        null=True,
    )
    default_search_fields = models.JSONField(
        verbose_name="Default Search Fields",
        help_text="Text or embedding fields (for hybrid search)",
        default=list,
        blank=True,
        null=True,
    )
    advanced_options = models.JSONField(
        verbose_name="Advanced Options",
        help_text="Advanced options for the dataset, like defaults for map creation etc.",
        default=dict,
        blank=True,
        null=True,
    )
    applicable_import_converters = models.ManyToManyField(
        verbose_name="Applicable Import Converters",
        to=ImportConverter,
        related_name="+",
        blank=True,
    )
    applicable_export_converters = models.ManyToManyField(
        verbose_name="Applicable Export Converters",
        to=ExportConverter,
        related_name="+",
        blank=True,
    )
    result_list_rendering = models.JSONField(
        verbose_name="Result List Rendering",
        default=get_default_result_list_rendering,
        blank=True,
        null=True,
    )
    hover_label_rendering = models.JSONField(
        verbose_name="Hover Label Rendering",
        default=get_default_hover_label_rendering,
        blank=True,
        null=True,
    )
    detail_view_rendering = models.JSONField(
        verbose_name="Detail View Rendering",
        default=get_default_detail_view_rendering,
        blank=True,
        null=True,
    )
    statistics = models.JSONField(
        verbose_name="Statistics",
        help_text="Statistics shown for the search results",
        default=dict,
        blank=True,
        null=True,
    )
    filter_prompts = models.TextField(
        verbose_name="Filter Prompts",
        help_text="Prompts for filter detection, start each with '# language: de / en / ...'",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Dataset Schema"
        verbose_name_plural = "Dataset Schemas"


class DatasetField(models.Model):
    identifier = models.CharField(verbose_name="Identifier", max_length=200, blank=False, null=False)
    name = models.CharField(verbose_name="Display Name", max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=True, null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    schema = models.ForeignKey(
        verbose_name="Schema",
        to=DatasetSchema,
        on_delete=models.CASCADE,
        related_name="object_fields",
        blank=False,
        null=False,
    )
    description = models.CharField(verbose_name="Description", max_length=200, blank=True, null=True)
    field_type = models.CharField(
        verbose_name="Type",
        max_length=50,
        choices=FieldType.choices,
        default=FieldType.TEXT,
        blank=False,
        null=False,
    )
    is_array = models.BooleanField(verbose_name="Is array", default=False, blank=False, null=False)
    language_analysis = models.CharField(
        verbose_name="Language Processing",
        help_text="Only applicable for 'Text' and 'Exact String' fields",
        max_length=50,
        choices=LanguageAnalysis.choices,
        blank=True,
        null=True,
    )
    additional_language_analysis = models.JSONField(
        verbose_name="Additional Language Processing",
        help_text="Only applicable for 'Text' fields, any of 'english, german, french, spanish, czech, russian, hindi'",
        default=list,
        blank=True,
        null=True,
    )
    embedding_space = models.ForeignKey(
        verbose_name="Embedding Space",
        help_text="If not set, embedding space of generator will be used",
        to=EmbeddingSpace,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    is_available_for_search = models.BooleanField(
        verbose_name="Available for fulltext or vector search",
        default=False,
        blank=False,
        null=False,
    )
    text_similarity_threshold = models.FloatField(
        verbose_name="Text Similarity Threshold",
        help_text="The minimum score / similarity a text query must have compared to this field to be considered relevant / similar (overriding the generators value)",
        blank=True,
        null=True,
    )
    image_similarity_threshold = models.FloatField(
        verbose_name="Image Similarity Threshold",
        help_text="The minimum score / similarity an image query must have compared to this field to be considered relevant / similar (overriding the generators value)",
        blank=True,
        null=True,
    )
    is_available_for_filtering = models.BooleanField(
        verbose_name="Available for filtering", default=False, blank=False, null=False
    )
    index_parameters = models.JSONField(verbose_name="Index Parameters", default=dict, blank=True, null=False)
    generator = models.ForeignKey(
        verbose_name="Generator",
        to=Generator,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    generator_parameters = models.JSONField(verbose_name="Generator Parameters", blank=True, null=True)
    generating_condition = models.TextField(verbose_name="Generating Condition", blank=True, null=True)
    source_fields = models.JSONField(
        verbose_name="Source Fields",
        help_text="List of source field identifiers, or dict generator input -> source field",
        default=list,
        blank=True,
        null=True,
    )
    should_be_generated = models.BooleanField(
        verbose_name="Generate on insert / change",
        help_text="Should be generated for new elements and when "
        "source fields are updated, not automatically generated for exisitng elements",
        default=False,
        blank=False,
        null=False,
    )

    def items_having_value_count(self, dataset):
        if not self.is_available_for_search and not self.is_available_for_filtering:
            # OpenSearch can't easily count values that are not indexed
            return "?"
        try:
            url = DATA_BACKEND_HOST + f"/data_backend/dataset/{dataset.id}/{self.identifier}/items_having_value_count"  # type: ignore
            result = backend_client.get(url)
            count = result.json()["count"]
            if self.field_type == FieldType.VECTOR and self.is_array:
                url = DATA_BACKEND_HOST + f"/data_backend/dataset/{dataset.id}/{self.identifier}/sub_items_having_value_count"  # type: ignore
                result = backend_client.get(url)
                sub_count = result.json()["count"]
                return f"{count} (~{sub_count / count:.0f} ppi)"
            else:
                return count
        except Exception as e:
            return repr(e)

    @property
    def actual_embedding_space(self):
        return self.embedding_space or self.generator.embedding_space if self.generator else None

    actual_embedding_space.fget.short_description = "Actual Embedding Space"  # type: ignore

    def __str__(self):
        return f"{self.identifier}"

    class Meta:
        unique_together = [["schema", "identifier"]]
        verbose_name = "Dataset Field"
        verbose_name_plural = "Dataset Fields"
        order_with_respect_to = "schema"


def generate_unique_database_name(name: str | None = None):
    if name:
        name = name[:100]
        return f"dataset_{name}_{''.join(random.choices(string.ascii_lowercase, k=6))}"
    return f"dataset_{''.join(random.choices(string.ascii_lowercase, k=6))}"


class Dataset(models.Model):
    name = models.CharField(verbose_name="Name", max_length=200, blank=False, null=False)
    schema = models.ForeignKey(
        verbose_name="Schema",
        to=DatasetSchema,
        on_delete=models.PROTECT,
        related_name="datasets",
        blank=False,
        null=False,
    )
    short_description = models.CharField(verbose_name="Short Description", max_length=200, blank=True, null=True)
    created_in_ui = models.BooleanField(
        verbose_name="Created in UI",
        help_text="Whether this dataset was created using the 'Create new dataset' button in the frontend",
        default=False,
        blank=False,
        null=False,
    )
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=True, null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    organization = models.ForeignKey(
        verbose_name="Organization",
        to=Organization,
        on_delete=models.PROTECT,
        related_name="datasets",
        blank=False,
        null=False,
    )
    is_public = models.BooleanField(
        verbose_name="Is public",
        help_text="Whether this dataset is available to everyone on the internet",
        default=False,
        blank=False,
        null=False,
    )
    is_organization_wide = models.BooleanField(
        verbose_name="Is organization-wide",
        help_text="Whether this dataset is available to all organization members. If not, its only available to admins.",
        default=False,
        blank=False,
        null=False,
    )
    admins = models.ManyToManyField(
        verbose_name="Admins",
        help_text="Users who can change the dataset and upload items to it",
        to=User,
        related_name="+",
        blank=True,
    )
    source_plugin = models.CharField(
        verbose_name="Source Plugin",
        max_length=50,
        choices=SourcePlugin.choices,
        default=SourcePlugin.INTERNAL_OPENSEARCH_QDRANT,
        blank=False,
        null=False,
    )
    source_plugin_parameters = models.JSONField(
        verbose_name="Source Plugin Parameters", default=dict, blank=True, null=True
    )
    database_name = models.CharField(
        verbose_name="Database Name",
        help_text="Name of the OpenSearch index and vector DB prefix, using 'dataset_&lt;id&gt;' if empty",
        max_length=100,
        default=generate_unique_database_name,
        blank=True,
        null=True,
    )
    advanced_options = models.JSONField(
        verbose_name="Advanced Options",
        help_text="Remote access tokens etc., also overrides schema advanced options",
        default=dict,
        blank=True,
        null=True,
    )
    filter_prompts = models.TextField(
        verbose_name="Filter Prompts",
        help_text="Prompts for filter detection, start each with '# language: de / en / ...'. Overrides those of the schema.",
        blank=True,
        null=True,
    )

    history = HistoricalRecords()

    @property
    def item_count(self):
        try:
            url = DATA_BACKEND_HOST + f"/data_backend/dataset/{self.id}/item_count"  # type: ignore
            result = backend_client.get(url)
            return result.json()["count"]
        except Exception as e:
            return repr(e)

    item_count.fget.short_description = "Current Item Count"  # type: ignore

    @property
    def random_item(self):
        try:
            url = DATA_BACKEND_HOST + f"/data_backend/dataset/{self.id}/random_item"  # type: ignore
            result = backend_client.get(url)
            item = result.json()["item"]

            def replace_long_arrays(value):
                if isinstance(value, list):
                    if len(value) > 50:
                        return f"&lt;Array of length {len(value)}&gt;"
                    else:
                        return [replace_long_arrays(v) for v in value]
                else:
                    return value

            for key in item.get("_source", {}).keys():
                item["_source"][key] = replace_long_arrays(item["_source"][key])
            return mark_safe(
                json.dumps(item, indent=2, ensure_ascii=False).replace(" ", "&nbsp").replace("\n", "<br>")
            )
        except Exception as e:
            return repr(e)

    random_item.fget.short_description = "Random Item"  # type: ignore

    @property
    def actual_database_name(self):
        return self.database_name or f"dataset_{self.id}"  # type: ignore

    actual_database_name.fget.short_description = "Actual Database Name"  # type: ignore

    @property
    def merged_advanced_options(self):
        return {**self.schema.advanced_options, **self.advanced_options}  # type: ignore

    def delete_content(self):
        delete_dataset_content(self.id)  # type: ignore
        collection_items = CollectionItem.objects.filter(dataset_id=self.id)  # type: ignore
        collection_items.delete()

    def delete_with_content(self):
        self.delete_content()
        self.delete()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"


class GenerationTask(models.Model):
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=False, null=False)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    dataset = models.ForeignKey(
        verbose_name="Dataset",
        to=Dataset,
        on_delete=models.CASCADE,
        related_name="generation_tasks",
        blank=False,
        null=False,
    )
    field = models.ForeignKey(
        verbose_name="Field",
        to=DatasetField,
        on_delete=models.CASCADE,
        related_name="generation_tasks",
        blank=False,
        null=False,
    )
    regenerate_all = models.BooleanField(
        verbose_name="Regenerate all",
        help_text="Regenerate all items, not only those that have not been generated yet",
        default=False,
        blank=False,
        null=False,
    )
    clear_all_output_fields = models.BooleanField(
        verbose_name="Clear all output fields",
        help_text="Clear all output fields (for multi-output generators) before re-generating all items",
        default=False,
        blank=False,
        null=False,
    )
    batch_size = models.IntegerField(verbose_name="Batch Size", default=512, blank=False, null=False)
    stop_flag = models.BooleanField(verbose_name="Stop Flag", default=False, blank=False, null=False)

    class TaskStatus(models.TextChoices):
        NOT_RUNNING = "not_running", "Not Running"
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        FINISHED = "finished", "Finished"
        FAILED = "failed", "Failed"

    status = models.CharField(
        verbose_name="Status",
        max_length=50,
        choices=TaskStatus.choices,
        default="not_running",
        blank=False,
        null=False,
    )
    progress = models.FloatField(verbose_name="Progress", default=0, blank=False, null=False)
    log = models.TextField(verbose_name="Log", blank=True, null=True)

    def add_log(self, message: str):
        if self.log is None:
            self.log = ""
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log = self.log + f"{timestamp}: {message}\n"
        if len(self.log) > 10000:
            self.log = self.log[:4000] + "\n\n... (truncated) ...\n\n" + self.log[-5000:]
        self.save(update_fields=["log"])

    def __str__(self):
        return f"{self.dataset} - {self.field}"

    class Meta:
        verbose_name = "Generation Task"
        verbose_name_plural = "Generation Tasks"


class SearchHistoryItem(models.Model):
    name = models.CharField(verbose_name="Name", max_length=200, blank=False, null=False)
    display_name = models.CharField(
        verbose_name="Display Name",
        help_text="Name to be displayed in the frontend, including HTML markup",
        max_length=300,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=False, null=False)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    user = models.ForeignKey(verbose_name="User", to=User, on_delete=models.CASCADE, blank=True, null=True)
    organization = models.ForeignKey(
        verbose_name="Organization",
        to=Organization,
        related_name="+",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )
    parameters = models.JSONField(verbose_name="Parameters", blank=True, null=True)
    total_matches = models.IntegerField(verbose_name="Total Matches", blank=True, null=True)
    auto_relaxed = models.BooleanField(
        verbose_name="Auto Relaxed",
        help_text="Whether the search was automatically relaxed to find results",
        blank=True,
        null=True,
    )
    cluster_count = models.IntegerField(verbose_name="Cluster Count", blank=True, null=True)
    result_information = models.JSONField(verbose_name="Other Result Information", blank=True, null=True)

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
        null=False,
    )
    name = models.CharField(verbose_name="Name", max_length=200, blank=False, null=False)
    display_name = models.CharField(
        verbose_name="Display Name",
        help_text="Name to be displayed in the frontend, including HTML markup",
        max_length=300,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=False, null=False)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    user = models.ForeignKey(verbose_name="User", to=User, on_delete=models.CASCADE, blank=False, null=False)
    organization = models.ForeignKey(
        verbose_name="Organization",
        to=Organization,
        related_name="+",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )
    map_data = models.BinaryField(verbose_name="Data", blank=True, null=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Stored Map"
        verbose_name_plural = "Stored Maps"


def class_field_default():
    return ["_default"]


class DataCollection(models.Model):  # aka DataCollection / DataClassification
    name = models.CharField(verbose_name="Name", max_length=200, blank=False, null=False)
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=True, null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    created_by = models.ForeignKey(
        verbose_name="Created By",
        to=User,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )
    is_public = models.BooleanField(verbose_name="Is public", default=False, blank=False, null=False)
    related_organization = models.ForeignKey(
        verbose_name="Related Organization",
        help_text="Collections can be used across organizations, but they usually belong to one",
        to=Organization,
        related_name="+",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    parent_collection = models.ManyToManyField(  # only their text or image sources are extracted, or vectors if embedding space matches target space
        verbose_name="Parent Collection", to="self", symmetrical=False, blank=True
    )
    is_binary = models.BooleanField(  # needed? or deduct from class count? but storing is different
        verbose_name="Is binary", default=False, blank=False, null=False
    )
    allow_multi_class = models.BooleanField(verbose_name="Allow multi class", default=False, blank=False, null=False)
    class_names = models.JSONField(
        verbose_name="Class Names",
        help_text="Minimal list of classes shown in the UI, even if no items are present. More classes are deducted from items.",
        default=class_field_default,
        blank=True,
        null=True,
    )
    default_threshold = models.FloatField(verbose_name="Default Threshold", default=0.5, blank=False, null=False)
    per_class_thresholds = models.JSONField(
        verbose_name="Per Class Thresholds",
        help_text="block classes e.g. from parents, using weight of -1",
        blank=True,
        null=True,
    )
    items_last_changed = models.DateTimeField(
        verbose_name="Items Last Changed",
        help_text="Last time items were added or their relevance was changed",
        default=timezone.now,
        blank=False,
        null=False,
    )
    table_columns = models.JSONField(verbose_name="Table Columns", help_text="", default=list, blank=True, null=True)
    columns_with_running_processes = models.JSONField(
        verbose_name="Current Extraction Processes",
        help_text="",
        default=list,
        blank=True,
        null=False,
    )
    agent_is_running = models.BooleanField(verbose_name="Agent is running", default=False, blank=False, null=False)
    cancel_agent_flag = models.BooleanField(verbose_name="Cancel Agent Flag", default=False, blank=False, null=False)
    current_agent_step = models.CharField(
        verbose_name="Current Agent Step",
        help_text="",
        max_length=200,
        blank=True,
        null=True,
    )
    search_sources = models.JSONField(
        verbose_name="Search Sources",
        help_text="A list of active and past search sources",
        default=list,
        blank=True,
        null=False,
    )
    search_tasks = models.JSONField(
        verbose_name="Search Tasks",
        help_text="List of executed search tasks",
        default=list,
        blank=True,
        null=False,
    )
    last_search_task = models.JSONField(
        verbose_name="Last Search Task",
        help_text="if search mode is still active, this is the current search task",
        default=dict,
        blank=True,
        null=False,
    )
    explanation_log = models.JSONField(
        verbose_name="Explanation Log",
        help_text="List of explanations what was done (e.g. using AI)",
        default=list,
        blank=True,
        null=False,
    )
    map_metadata = models.JSONField(
        verbose_name="Map Metadata",
        help_text="Last update, progress, readiness etc.",
        default=dict,
        blank=True,
        null=False,
    )
    map_data = models.JSONField(
        verbose_name="Map Data",
        help_text="The actual map data like positions and labels",
        default=dict,
        blank=True,
        null=False,
    )
    filters = models.JSONField(
        verbose_name="Filters",
        help_text="Visibility filters",
        default=list,
        blank=True,
        null=False,
    )
    ui_settings = models.JSONField(
        verbose_name="UI Settings",
        help_text="Settings for the frontend",
        default=dict,
        blank=True,
        null=False,
    )

    @property
    def actual_classes(self) -> list:
        classes = defaultdict(lambda: [0, 0])
        for class_name in self.class_names or ["_default"]:
            classes[class_name] = [0, 0]
        for example in CollectionItem.objects.filter(collection=self):
            for c in example.classes or ["_default"]:
                classes[c][0 if example.is_positive else 1] += 1
        classes_list_of_dicts = []
        for c, v in classes.items():
            classes_list_of_dicts.append({"name": c, "positive_count": v[0], "negative_count": v[1]})
        return sorted(classes_list_of_dicts, key=lambda x: x["name"])

    def actual_classes_formatted(self):
        return mark_safe(
            json.dumps(self.actual_classes, indent=2, ensure_ascii=False).replace(" ", "&nbsp").replace("\n", "<br>")
        )

    actual_classes_formatted.short_description = "Actual Classes"

    @property
    def writing_task_count(self):
        return WritingTask.objects.filter(collection=self).count()

    writing_task_count.fget.short_description = "Writing Task Count"  # type: ignore

    # def simplified_trained_classifiers(self):
    #     data = copy.deepcopy(self.trained_classifiers) or {}
    #     for embedding_space_data in data.values():
    #         for class_name in embedding_space_data:
    #             if "decision_vector" in embedding_space_data[class_name]:
    #                 embedding_space_data[class_name]["decision_vector"] = f"&ltarray of length {len(embedding_space_data[class_name]['decision_vector'])}, stdev {np.std(embedding_space_data[class_name]['decision_vector']):.4f}&gt"
    #     return mark_safe(json.dumps(data, indent=2, ensure_ascii=False).replace(" ", "&nbsp").replace("\n", "<br>"))
    # simplified_trained_classifiers.short_description = "Trained Classifiers"

    def log_explanation(self, explanation: str, save=True):
        self.explanation_log.append({"time": timezone.now().isoformat(), "explanation": explanation})
        if save:
            self.save(update_fields=["explanation_log"])

    def __str__(self):
        return f"{self.name}"

    objects = models.Manager().defer("map_data")

    class Meta:
        verbose_name = "Data Collection"
        verbose_name_plural = "Data Collections"


class DatasetSpecificSettingsOfCollection(models.Model):
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=True, null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    collection = models.ForeignKey(
        verbose_name="Collection",
        to=DataCollection,
        on_delete=models.CASCADE,
        related_name="dataset_specific_settings",
        blank=False,
        null=False,
    )
    dataset = models.ForeignKey(
        verbose_name="Dataset",
        to=Dataset,
        on_delete=models.CASCADE,
        related_name="+",
        blank=False,
        null=False,
    )
    relevant_object_fields = models.ManyToManyField(
        verbose_name="Relevant Object Fields",
        help_text="The 'source' fields (text or image) for items from this dataset, using default search fields (or their sources for vectors) if empty",
        to="DatasetField",
        related_name="+",
        blank=True,
    )
    positive_annotation_field = models.ForeignKey(
        verbose_name="Positive Annotation Field",
        help_text="binary: bool field, exclusive: single tag, non-exclusive: tag array field",  # or class probability field (not yet, only makes sense if regression is supported)
        to="DatasetField",
        related_name="+",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    negative_annotation_field = models.ForeignKey(
        verbose_name="Negative Annotation Field",
        help_text="binary: bool field, exclusive: single tag, non-exclusive: tag array field",
        to="DatasetField",
        related_name="+",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.collection.name} - {self.dataset.name}"

    class Meta:
        verbose_name = "Dataset Specific Settings"
        verbose_name_plural = "Dataset Specific Settings"
        unique_together = [["collection", "dataset"]]


def get_random_string():
    return "".join(random.choices(string.ascii_lowercase, k=9))


class COLUMN_META_SOURCE_FIELDS:
    DESCRIPTIVE_TEXT_FIELDS = "_descriptive_text_fields"
    FULL_TEXT_SNIPPETS = "_full_text_snippets"


class CollectionColumn(models.Model):
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=True, null=True)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    collection = models.ForeignKey(
        verbose_name="Collection",
        to=DataCollection,
        on_delete=models.CASCADE,
        related_name="columns",
        blank=False,
        null=False,
    )
    name = models.CharField(verbose_name="Name", max_length=200, blank=False, null=False)
    identifier = models.CharField(
        verbose_name="Identifier",
        help_text="Do not change this after being used elsewhere",
        max_length=200,
        default=get_random_string,
        blank=False,
        null=False,
    )
    field_type = models.CharField(
        verbose_name="Type",
        max_length=50,
        choices=FieldType.choices,
        default=FieldType.TEXT,
        blank=False,
        null=False,
    )
    expression = models.TextField(
        verbose_name="Expression",
        help_text="Question / Prompt / Math / Code expression to generate this column",
        blank=True,
        null=True,
    )
    prompt_template = models.TextField(
        verbose_name="Prompt Template",
        help_text="Template for the prompt if this column uses an LLM. If empty, a default template is used. "
        + "There are some special variables like {{ document }} and {{ expression }} that can be used.",
        blank=True,
        null=True,
    )
    source_fields = models.JSONField(
        verbose_name="Source Fields",
        help_text="List of source fields to be used for this column",
        default=list,
        blank=True,
        null=False,
    )
    module = models.CharField(verbose_name="Code Module Name", max_length=200, blank=True, null=True)
    parameters = models.JSONField(verbose_name="Parameters", default=dict, blank=True, null=False)
    auto_run_for_approved_items = models.BooleanField(
        verbose_name="Auto Run for Approved Items", default=False, blank=False, null=False
    )
    auto_run_for_candidates = models.BooleanField(
        verbose_name="Auto Run for Candidates", default=False, blank=False, null=False
    )

    def __str__(self):
        return f"{self.collection.name} - {self.name}"

    class Meta:
        verbose_name = "Collection Column"
        verbose_name_plural = "Collection Columns"
        unique_together = [["collection", "identifier"]]
        order_with_respect_to = "collection"


class CollectionItem(models.Model):
    collection = models.ForeignKey(
        verbose_name="Collection",
        to=DataCollection,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        db_index=True,
        related_name="items",
    )
    date_added = models.DateTimeField(
        verbose_name="Date added",
        default=timezone.now,
        editable=False,
        blank=False,
        null=False,
    )
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    relevance = models.IntegerField(
        verbose_name="Relevance",
        help_text="From +3 to -3. 0 is a new, non-reviewed candidate",
        default=3,
        blank=False,
        null=False,
    )
    search_source_id = models.CharField(
        verbose_name="Search Source ID",
        help_text="ID of the search source that generated this item",
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
    )
    search_score = models.FloatField(
        verbose_name="Search Score",
        help_text="Score from the search engine",
        blank=True,
        null=True,
    )
    is_positive = models.BooleanField(verbose_name="Is positive", default=True, blank=False, null=False)
    classes = models.JSONField(
        verbose_name="Classes",
        default=class_field_default,
        blank=False,
        null=False,
        db_index=True,
    )
    field_type = models.CharField(
        verbose_name="Type",
        help_text="Either IDENTIFIER, TEXT, IMAGE",
        # if you want to store a vector, use a parent collection connected to a dataset with only those vectors
        max_length=50,
        choices=FieldType.choices,
        default=FieldType.TEXT,
        blank=False,
        null=False,
    )
    origins = models.JSONField(
        verbose_name="Sources",
        help_text="Searches where this item came from",
        default=list,
        blank=True,
        null=True,
    )
    dataset_id = models.IntegerField(
        verbose_name="Dataset ID (in case this is an item reference aka IDENTIFIER)",
        blank=True,
        null=True,
        db_index=True,
    )
    item_id = models.CharField(
        verbose_name="Item ID (in case this is an item reference aka IDENTIFIER)",
        max_length=200,
        blank=True,
        null=True,
        db_index=True,
    )
    metadata = models.JSONField(
        verbose_name="Metadata",
        help_text="Item content except for full text etc.",
        default=dict,
        blank=True,
        null=True,
    )
    value = models.TextField(
        verbose_name="Value",
        help_text="Any non-identifier value, e.g. plain text or image URL",
        blank=True,
        null=True,
    )
    relevant_parts = models.JSONField(
        verbose_name="Relevant Parts",
        help_text="Highlights from text search, relevant chunks from vector search, image regions etc.",
        default=list,
        blank=True,
        null=True,
    )
    full_text = models.TextField(
        verbose_name="Full Text",
        help_text="Full text extracted from PDF or web page etc.",
        blank=True,
        null=True,
    )
    weight = models.FloatField(
        verbose_name="Weight",
        help_text="Weight for this example (e.g. small if just a product page view, high if product was bought)",
        default=1.0,
        blank=False,
        null=False,
    )
    column_data = models.JSONField(
        verbose_name="Column Data",
        help_text="Extracted answers, notes, etc.",
        default=dict,
        blank=True,
        null=False,
    )

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
        null=False,
    )
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    last_retrained_at = models.DateTimeField(verbose_name="Last Retrained at", blank=True, null=True)
    collection = models.ForeignKey(
        verbose_name="Collection",
        to=DataCollection,
        on_delete=models.CASCADE,
        related_name="trained_classifiers",
        blank=False,
        null=False,
    )
    class_name = models.CharField(verbose_name="Class", max_length=200, blank=False, null=False)
    embedding_space = models.ForeignKey(
        verbose_name="Embedding Space",
        to=EmbeddingSpace,
        related_name="+",
        on_delete=models.PROTECT,
        blank=False,
        null=False,
    )
    decision_vector = models.JSONField(verbose_name="decision_vector", blank=True, null=True)
    highest_score = models.FloatField(verbose_name="Highest Score", blank=True, null=True)
    threshold = models.FloatField(verbose_name="Threshold", default=0.5, blank=False, null=False)
    metrics = models.JSONField(verbose_name="Metrics", default=dict, blank=True, null=True)

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
        unique_together = [["collection", "class_name", "embedding_space"]]


class WritingTask(models.Model):
    name = models.CharField(verbose_name="Name", max_length=200, blank=False, null=False)
    collection = models.ForeignKey(
        verbose_name="Collection",
        to=DataCollection,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )
    class_name = models.CharField(verbose_name="Class", max_length=200, blank=False, null=False, default="_default")
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        editable=False,
        blank=False,
        null=False,
    )
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    is_processing = models.BooleanField(verbose_name="Is Processing", default=False, blank=False, null=False)
    source_fields = models.JSONField(verbose_name="Source Fields", default=list, blank=True, null=False)
    use_all_items = models.BooleanField(verbose_name="Use All Items", default=True, blank=False, null=False)
    selected_item_ids = models.JSONField(verbose_name="Selected Item IDs", default=list, blank=True, null=False)
    module = models.CharField(verbose_name="Code Module Name", max_length=200, blank=True, null=True)
    parameters = models.JSONField(verbose_name="Parameters", default=dict, blank=True, null=True)
    prompt = models.TextField(verbose_name="Prompt", blank=True, null=True)
    text = models.TextField(verbose_name="Text", blank=True, null=True)
    additional_results = models.JSONField(verbose_name="Additional Results", default=dict, blank=True, null=True)
    previous_versions = models.JSONField(verbose_name="Previous Versions", default=list, blank=True, null=False)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Writing Task"
        verbose_name_plural = "Writing Tasks"


class Chat(models.Model):
    name = models.CharField(verbose_name="Name", max_length=200, blank=True, null=True)
    created_by = models.ForeignKey(
        verbose_name="Created By",
        to=User,
        related_name="+",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )
    search_settings = models.JSONField(verbose_name="Search Settings", default=dict, blank=True, null=True)
    collection = models.ForeignKey(
        verbose_name="Collection",
        to=DataCollection,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    class_name = models.CharField(verbose_name="Class", max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(
        verbose_name="Created at",
        default=timezone.now,
        editable=False,
        blank=False,
        null=False,
    )
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    chat_history = models.JSONField(verbose_name="Chat History", default=list, blank=True, null=True)
    is_processing = models.BooleanField(verbose_name="Is Processing", default=False, blank=False, null=False)

    def add_question(self, question: str, user_id: int):
        assert isinstance(self.chat_history, list)
        self.chat_history.append(
            {
                "role": "user",
                "content": question,
                "date": timezone.now().isoformat(),
            }
        )
        self.is_processing = True
        self.save()

        obj = self

        def answer_question():
            system_prompt = (
                "You are a helpful assistant. You can answer questions based on the following items. "
                + "Answer in one or two concise sentences. "
                + "Mention the item identifier '[dataset_id, item_id]' you got the answer from after the sentence (only one identifier pair per square bracket). "
                + "If the provided information does not contain the answer, say that you couldn't find the information. "
            )

            if obj.collection is not None:
                collection_items = CollectionItem.objects.filter(
                    collection=self.collection, classes__contains=[obj.class_name]
                )
                included_items = 0
                for item in collection_items:
                    text = None
                    if item.field_type == FieldType.TEXT:
                        text = json.dumps({"_id": item.id, "text": item.value}, indent=2)  # type: ignore
                    if item.field_type == FieldType.IDENTIFIER:
                        assert item.dataset_id is not None
                        assert item.item_id is not None
                        fields = list(Dataset.objects.get(id=item.dataset_id).schema.descriptive_text_fields.all().values_list("identifier", flat=True))  # type: ignore
                        fields.append("_id")
                        full_item = get_item_by_id(item.dataset_id, item.item_id, fields)
                        text = json.dumps(full_item, indent=2)
                    if not text:
                        continue
                    included_items += 1
                    system_prompt += "\n" + text + "\n"
                    if included_items > 5:
                        break
            else:
                assert isinstance(obj.search_settings, dict)
                context = get_global_question_context(obj.search_settings)
                system_prompt += "\n\n" + context + "\n"
            logging.warning(system_prompt)

            history = []
            history.append({"role": "system", "content": system_prompt})
            for chat_item in obj.chat_history:  # type: ignore
                history.append(
                    {
                        "role": chat_item["role"],
                        "content": chat_item["content"],
                    }
                )
            usage_tracker = ServiceUsage.get_usage_tracker(user_id, "External AI")
            result = usage_tracker.track_usage(1, "chat answer")
            if result["approved"]:
                response_text = get_chatgpt_response_using_history(history)
            else:
                response_text = "AI usage limit exceeded."
            # response_text = "I'm sorry, I can't answer that question yet."

            obj.chat_history.append(  # type: ignore
                {
                    "role": "system",
                    "content": response_text,
                    "date": timezone.now().isoformat(),
                }
            )
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

    class Meta:
        verbose_name = "Chat"
        verbose_name_plural = "Chats"


class PeriodType(models.TextChoices):
    DAY = "day", "Day"
    WEEK = "week", "Week"
    MONTH = "month", "Month"
    YEAR = "year", "Year"


class ServiceUsagePeriod(models.Model):
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=False, null=False)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    service_usage = models.ForeignKey(
        verbose_name="Service Usage",
        to="ServiceUsage",
        on_delete=models.CASCADE,
        related_name="usage_periods",
        blank=False,
        null=False,
    )
    period = models.CharField(verbose_name="Period", max_length=50, blank=False, null=False)
    usage = models.FloatField(verbose_name="Usage", default=0, blank=False, null=False)
    usage_by_cause = models.JSONField(verbose_name="Usage by Cause", default=dict, blank=True, null=False)

    class Meta:
        verbose_name = "Service Usage Period"
        verbose_name_plural = "Service Usage Periods"
        unique_together = [["service_usage", "period"]]


class ServiceUsage(models.Model):
    created_at = models.DateTimeField(verbose_name="Created at", default=timezone.now, blank=False, null=False)
    changed_at = models.DateTimeField(
        verbose_name="Changed at",
        auto_now=True,
        editable=False,
        blank=False,
        null=False,
    )
    user = models.ForeignKey(
        verbose_name="User",
        to=User,
        on_delete=models.CASCADE,
        related_name="+",
        blank=False,
        null=False,
    )
    service = models.CharField(verbose_name="Service", max_length=200, blank=False, null=False)
    limit_per_period = models.FloatField(verbose_name="Limit per Period", default=50.0, blank=False, null=False)
    period_type = models.CharField(
        verbose_name="Period Type",
        max_length=50,
        choices=PeriodType.choices,
        default=PeriodType.MONTH,
        blank=False,
        null=False,
    )
    warning_ratio = models.FloatField(verbose_name="Warning Ratio", default=0.8, blank=False, null=False)

    def get_current_period(self) -> ServiceUsagePeriod:
        if self.period_type == PeriodType.DAY:
            period = timezone.now().strftime("%Y-%m-%d")
        elif self.period_type == PeriodType.WEEK:
            period = timezone.now().strftime("%Y-%W")
        elif self.period_type == PeriodType.MONTH:
            period = timezone.now().strftime("%Y-%m")
        elif self.period_type == PeriodType.YEAR:
            period = timezone.now().strftime("%Y")
        else:
            logging.warning(f"Unknown period type {self.period_type}")
            # default to year, which is the most conservative
            period = timezone.now().strftime("%Y")
        usage_period = ServiceUsagePeriod.objects.filter(service_usage=self, period=period).first()
        if usage_period is None:
            usage_period = ServiceUsagePeriod.objects.create(service_usage=self, period=period, usage=0)
            usage_period.save()
        return usage_period

    def track_usage(self, amount: float, cause: str):
        usage_period = self.get_current_period()
        if usage_period.usage + amount > self.limit_per_period:
            return {"approved": False, "error": "Limit exceeded"}
        usage_period.usage = models.F("usage") + amount
        if cause not in usage_period.usage_by_cause:
            usage_period.usage_by_cause[cause] = 0
        usage_period.usage_by_cause[cause] += amount
        usage_period.save()
        usage_period.refresh_from_db()

        warning_threshold = self.limit_per_period * self.warning_ratio
        should_warn = usage_period.usage > warning_threshold  # type: ignore
        return {"approved": True, "should_warn": should_warn}

    @staticmethod
    def get_usage_tracker(user_id: int, service: str):
        try:
            return ServiceUsage.objects.get(user_id=user_id, service=service)
        except ServiceUsage.DoesNotExist:
            return ServiceUsage.objects.create(user_id=user_id, service=service)

    class Meta:
        verbose_name = "Service Usage"
        verbose_name_plural = "Service Usages"
        unique_together = [["user", "service"]]
