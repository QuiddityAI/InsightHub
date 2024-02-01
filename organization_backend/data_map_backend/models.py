from collections import defaultdict
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

def get_default_classifier_example_rendering():
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
    is_public = models.BooleanField(
        verbose_name="Is public",
        default=False,
        blank=False,
        null=False)
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
    result_list_rendering = models.JSONField(
        verbose_name="Result List Rendering",
        default=get_default_result_list_rendering,
        blank=True,
        null=True)
    classifier_example_rendering =  models.JSONField(
        verbose_name="Collection List Rendering",
        default=get_default_classifier_example_rendering,
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
        try:
            url = data_backend_url + f'/data_backend/dataset/{self.id}/item_count'
            result = requests.get(url)
            return result.json()["count"]
        except Exception as e:
            return repr(e)
    item_count.fget.short_description = "Current Item Count"

    @property
    def random_item(self):
        try:
            url = data_backend_url + f'/data_backend/dataset/{self.id}/random_item'
            result = requests.get(url)
            item = result.json()["item"]
            for key in item.get("_source", {}).keys():
                if isinstance(item["_source"][key], list) and len(item["_source"][key]) > 50:
                    item["_source"][key] = f"&lt;Array of length {len(item['_source'][key])}&gt;"
            return mark_safe(json.dumps(item, indent=2, ensure_ascii=False).replace(" ", "&nbsp").replace("\n", "<br>"))
        except Exception as e:
            return repr(e)
    item_count.fget.random_item = "Random Item"

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
        try:
            url = data_backend_url + f'/data_backend/dataset/{self.dataset.id}/{self.identifier}/items_having_value_count'
            result = requests.get(url)
            return result.json()["count"]
        except Exception as e:
            return repr(e)
    items_having_value_count.fget.short_description = "Items having this value"

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
    dataset = models.ForeignKey(
        verbose_name="Dataset",
        to=Dataset,
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
    dataset = models.ForeignKey(
        verbose_name="Dataset",
        to=Dataset,
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
    dataset = models.ForeignKey(
        verbose_name="Dataset",
        to=Dataset,
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


class Classifier(models.Model):  # aka DataCollection / DataClassification
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
    dataset = models.ForeignKey(
        verbose_name="Dataset",
        to=Dataset,
        on_delete=models.SET_NULL,
        blank=True,
        null=True)
    created_by = models.ForeignKey(
        verbose_name="User",
        to=User,
        on_delete=models.CASCADE,
        blank=False,
        null=False)
    is_public = models.BooleanField(
        verbose_name="Is public",
        default=False,
        blank=False,
        null=False)
    parent_classifiers = models.ManyToManyField(  # only their text or image sources are extracted, or vectors if embedding space matches target space
        verbose_name="Parent Classifiers",
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
        help_text="If empty, either deducted from classes or if data doesn't have classed, converted classifier name is used",
        default=list,
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
    relevant_object_fields = models.ManyToManyField(  # the "source" of the classifier, e.g. text or image
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
    trained_classifiers = models.JSONField(
        verbose_name="Trained Classifiers",
        help_text="For each embedding space, and there for each class, a 'decision' vector to be applied with dotproduct (plus time_updated)",
        blank=True,
        null=True)

    history = HistoricalRecords()

    @property
    def actual_classes(self) -> list:
        classes = defaultdict(lambda: [0, 0])
        for class_name in self.class_names or []:
            classes[class_name] = [0, 0]
        for example in ClassifierExample.objects.filter(classifier=self):
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

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Classifier"
        verbose_name_plural = "Classifiers"


class ClassifierExample(models.Model):  # aka DataCollection / DataClassification Entry
    classifier = models.ForeignKey(
        verbose_name="Classifier",
        to=Classifier,
        on_delete=models.CASCADE,
        blank=False,
        null=False)
    date_added = models.DateTimeField(
        verbose_name="Date added",
        default=timezone.now,
        blank=True,
        null=True)
    is_positive = models.BooleanField(
        verbose_name="Is positive",
        default=True,
        blank=False,
        null=False)
    classes = models.JSONField(
        verbose_name="Classes",
        default=list,
        blank=True,
        null=True)
    field_type = models.CharField(
        verbose_name="Type",
        help_text="Either IDENTIFIER, TEXT, IMAGE",
        # if you want to store a vector, use a parent classifier connected to a dataset with only those vectors
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

    # def __str__(self):
    #     return f"{self.name}"

    class Meta:
        verbose_name = "Classifier Example"
        verbose_name_plural = "Classifier Examples"
