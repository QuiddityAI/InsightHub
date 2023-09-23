import copy
import json

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
import requests

from simple_history.models import HistoricalRecords

from .data_backend_client import data_backend_url


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

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"


def get_rendering_json_field_default(fields: list):
    val = {}
    val["required_fields"] = []
    for field in fields:
        val[field] = "(item) => { return null }"
    return val

def get_default_result_list_rendering():
    return get_rendering_json_field_default(['title', 'subtitle', 'body', 'image', 'url'])

def get_default_collection_list_rendering():
    return get_rendering_json_field_default(['title', 'subtitle', 'body', 'image', 'url'])

def get_default_hover_label_rendering():
    return get_rendering_json_field_default(['title', 'subtitle', 'image'])

def get_default_detail_view_rendering():
    return get_rendering_json_field_default(['title', 'subtitle', 'body', 'image', 'url'])


class ObjectSchema(models.Model):
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=False,
        null=False)
    name_plural = models.CharField(
        verbose_name="Name (Plural)",
        max_length=200,
        blank=False,
        null=False)
    short_description = models.CharField(
        verbose_name="Short Description",
        max_length=200,
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
        blank=False,
        null=False)
    primary_key = models.ForeignKey(
        verbose_name="Primary Key",
        to='ObjectField',
        related_name='+',
        on_delete=models.PROTECT,
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
        blank=True,
        null=True)
    default_search_fields = models.ManyToManyField(
        verbose_name="Default Search Fields",
        help_text="For combined search",
        to='ObjectField',
        related_name='+',
        blank=True,
        null=True)
    result_list_rendering = models.JSONField(
        verbose_name="Result List Rendering",
        default=get_default_result_list_rendering,
        blank=True,
        null=True)
    collection_list_rendering =  models.JSONField(
        verbose_name="Collection List Rendering",
        default=get_default_collection_list_rendering,
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

    history = HistoricalRecords()

    @property
    def item_count(self):
        url = data_backend_url + f'/data_backend/schema/{self.id}/item_count'
        result = requests.get(url)
        return result.json()["count"]
    item_count.fget.short_description = "Current Item Count"

    @property
    def random_item(self):
        url = data_backend_url + f'/data_backend/schema/{self.id}/random_item'
        result = requests.get(url)
        return mark_safe(json.dumps(result.json()["item"], indent=2).replace(" ", "&nbsp").replace("\n", "<br>"))
    item_count.fget.random_item = "Random Item"

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Object Schema"
        verbose_name_plural = "Object Schemas"


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
    schema = models.ForeignKey(
        verbose_name="Schema",
        to=ObjectSchema,
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

    def __str__(self):
        return f"{self.identifier}"

    class Meta:
        verbose_name = "Object Field"
        verbose_name_plural = "Object Fields"
        order_with_respect_to = "schema"


class SearchHistoryItem(models.Model):
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=False,
        null=False)
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
    schema = models.ForeignKey(
        verbose_name="Schema",
        to=ObjectSchema,
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


class ItemCollection(models.Model):
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=False,
        null=False)
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
    schema = models.ForeignKey(
        verbose_name="Schema",
        to=ObjectSchema,
        on_delete=models.CASCADE,
        blank=False,
        null=False)
    positive_ids = models.JSONField(
        verbose_name="Positive IDs",
        default=list,
        blank=False,
        null=False)
    negative_ids = models.JSONField(
        verbose_name="Negative IDs",
        default=list,
        blank=False,
        null=False)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Item Collection"
        verbose_name_plural = "Item Collections"


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
    schema = models.ForeignKey(
        verbose_name="Schema",
        to=ObjectSchema,
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
