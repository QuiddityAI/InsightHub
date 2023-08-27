from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

from simple_history.models import HistoricalRecords


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
    identifier = models.CharField(
        verbose_name="Identifier",
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
    embedding_space = models.ForeignKey(
        verbose_name="Embedding Space",
        to=EmbeddingSpace,
        on_delete=models.PROTECT,
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
    result_list_rendering = models.TextField(
        verbose_name="Rendering (Result List)",
        blank=True,
        null=True)
    collection_list_rendering = models.TextField(
        verbose_name="Rendering (Collection List)",
        blank=True,
        null=True)
    hover_label_rendering = models.TextField(
        verbose_name="Rendering (Hover Label)",
        blank=True,
        null=True)
    detail_view_rendering = models.TextField(
        verbose_name="Rendering (Detail View)",
        blank=True,
        null=True)
    thumbnail_image = models.ForeignKey(
        verbose_name="Thumbnail Image",
        to='ObjectField',
        on_delete=models.SET_NULL,
        blank=True,
        null=True)

    history = HistoricalRecords()

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
    is_required = models.BooleanField(
        verbose_name="Required",
        default=False,
        blank=False,
        null=False)
    is_available_for_search = models.BooleanField(
        verbose_name="Available for fuzzy text or vector search",
        default=False,
        blank=False,
        null=False)
    is_available_for_filtering = models.BooleanField(
        verbose_name="Available for filtering",
        default=False,
        blank=False,
        null=False)
    generator = models.ForeignKey(
        verbose_name="Generator",
        to=Generator,
        on_delete=models.PROTECT,
        blank=True,
        null=True)
    generator_parameters = models.CharField(
        verbose_name="Generator Parameters",
        max_length=200,
        blank=True,
        null=True)
    generating_condition = models.CharField(
        verbose_name="Generating Condition",
        max_length=200,
        blank=True,
        null=True)
    source_fields = models.ManyToManyField(
        verbose_name="Source Fields",
        to='self',
        symmetrical=False,
        blank=True)
    should_be_generated = models.BooleanField(
        verbose_name="Should be generated",
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
