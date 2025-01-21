from rest_framework import serializers as drf_serializers

from .models import (
    Chat,
    CollectionColumn,
    DataCollection,
    DatasetField,
    DatasetSchema,
    DatasetSpecificSettingsOfCollection,
    CollectionItem,
    Dataset,
    ExportConverter,
    ImportConverter,
    Generator,
    EmbeddingSpace,
    Organization,
    SearchHistoryItem,
    SearchTask,
    StoredMap,
    TrainedClassifier,
    WritingTask,
)


class EmbeddingSpaceSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = EmbeddingSpace
        exclude = ["created_at", "changed_at"]


class GeneratorSerializer(drf_serializers.ModelSerializer):
    embedding_space = EmbeddingSpaceSerializer(read_only=True)

    class Meta:
        model = Generator
        exclude = ["created_at", "changed_at", "parameter_description"]


class DatasetFieldSerializer(drf_serializers.ModelSerializer):
    generator = GeneratorSerializer(read_only=True)
    embedding_space = EmbeddingSpaceSerializer(read_only=True)
    actual_embedding_space = EmbeddingSpaceSerializer(many=False, read_only=True)

    class Meta:
        model = DatasetField
        exclude = ["created_at", "changed_at", "_order"]


class OrganizationSerializer(drf_serializers.ModelSerializer):
    datasets = drf_serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    default_dataset_selection = drf_serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Organization
        exclude = ["created_at", "changed_at", "members"]


class ImportConverterSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = ImportConverter
        exclude = ["created_at", "changed_at"]


class ExportConverterSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = ExportConverter
        exclude = ["created_at", "changed_at"]


class DatasetSchemaSerializer(drf_serializers.ModelSerializer):
    object_fields = DatasetFieldSerializer(many=True, read_only=True)
    applicable_import_converters = ImportConverterSerializer(many=True, read_only=True)
    applicable_export_converters = ExportConverterSerializer(many=True, read_only=True)

    class Meta:
        model = DatasetSchema
        exclude = ["created_at", "changed_at"]


class DatasetSerializer(drf_serializers.ModelSerializer):
    admins = drf_serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    actual_database_name = drf_serializers.ReadOnlyField()
    schema = DatasetSchemaSerializer(many=False, read_only=True)
    merged_advanced_options = drf_serializers.ReadOnlyField()

    class Meta:
        model = Dataset
        exclude = ["created_at", "changed_at"]


class SearchHistoryItemSerializer(drf_serializers.ModelSerializer):
    user = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    organization = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)

    class Meta:
        model = SearchHistoryItem
        exclude = ["changed_at"]


class DatasetSpecificSettingsOfCollectionSerializer(drf_serializers.ModelSerializer):
    dataset = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    relevant_object_fields = drf_serializers.StringRelatedField(many=True, read_only=True)
    positive_annotation_field = drf_serializers.StringRelatedField(many=False, read_only=True)
    negative_annotation_field = drf_serializers.StringRelatedField(many=False, read_only=True)

    class Meta:
        model = DatasetSpecificSettingsOfCollection
        exclude = ["created_at", "changed_at"]


class CollectionColumnSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = CollectionColumn
        exclude = ["created_at", "changed_at"]


class SearchTaskSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = SearchTask
        exclude = []


class CollectionSerializer(drf_serializers.ModelSerializer):
    user = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    related_organization = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    parent_collection = drf_serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # dataset_specific_settings = DatasetSpecificSettingsOfCollectionSerializer(many=True, read_only=True)
    columns = CollectionColumnSerializer(many=True, read_only=True)
    actual_classes = drf_serializers.ReadOnlyField()
    writing_task_count = drf_serializers.ReadOnlyField()
    most_recent_search_task = SearchTaskSerializer(many=False, read_only=True)

    class Meta:
        model = DataCollection
        exclude = ["map_data"]


class CollectionItemSerializer(drf_serializers.ModelSerializer):
    collection = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)

    class Meta:
        model = CollectionItem
        exclude = []


class TrainedClassifierSerializer(drf_serializers.ModelSerializer):
    collection = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    embedding_space = EmbeddingSpaceSerializer(many=False, read_only=True)
    is_up_to_date = drf_serializers.ReadOnlyField()

    class Meta:
        model = TrainedClassifier
        exclude = []


class WritingTaskSerializer(drf_serializers.ModelSerializer):
    collection = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)

    class Meta:
        model = WritingTask
        exclude = []


class StoredMapSerializer(drf_serializers.ModelSerializer):
    user = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    organization = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)

    class Meta:
        model = StoredMap
        exclude = ["map_data"]


class ChatSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = Chat
        exclude = ["created_at", "changed_at"]
