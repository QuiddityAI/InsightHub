from rest_framework import serializers as drf_serializers

from .models import Classifier, ClassifierExample, Dataset, ObjectField, Generator, EmbeddingSpace, Organization, SearchHistoryItem, ItemCollection, StoredMap


class EmbeddingSpaceSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = EmbeddingSpace
        exclude = ['created_at', 'changed_at']


class GeneratorSerializer(drf_serializers.ModelSerializer):
    embedding_space = EmbeddingSpaceSerializer(read_only=True)

    class Meta:
        model = Generator
        exclude = ['created_at', 'changed_at']


class ObjectFieldSerializer(drf_serializers.ModelSerializer):
    source_fields = drf_serializers.StringRelatedField(many=True, read_only=True)
    generator = GeneratorSerializer(read_only=True)
    embedding_space = EmbeddingSpaceSerializer(read_only=True)

    class Meta:
        model = ObjectField
        exclude = ['created_at', 'changed_at', '_order', 'description']


class OrganizationSerializer(drf_serializers.ModelSerializer):
    datasets = drf_serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Organization
        exclude = ['created_at', 'changed_at']


class DatasetSerializer(drf_serializers.ModelSerializer):
    object_fields = ObjectFieldSerializer(many=True, read_only=True)
    primary_key = drf_serializers.StringRelatedField(many=False, read_only=True)
    thumbnail_image = drf_serializers.StringRelatedField(many=False, read_only=True)
    descriptive_text_fields = drf_serializers.StringRelatedField(many=True, read_only=True)
    default_search_fields = drf_serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Dataset
        exclude = ['created_at', 'changed_at']


class SearchHistoryItemSerializer(drf_serializers.ModelSerializer):
    user = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    dataset = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)

    class Meta:
        model = SearchHistoryItem
        exclude = ['changed_at']


class ItemCollectionSerializer(drf_serializers.ModelSerializer):
    user = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    dataset = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)

    class Meta:
        model = ItemCollection
        exclude = []


class ClassifierSerializer(drf_serializers.ModelSerializer):
    user = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    dataset = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    parent_classifiers = drf_serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    relevant_object_fields = drf_serializers.StringRelatedField(many=True, read_only=True)
    positive_annotation_field = drf_serializers.StringRelatedField(many=False, read_only=True)
    negative_annotation_field = drf_serializers.StringRelatedField(many=False, read_only=True)
    actual_classes = drf_serializers.ReadOnlyField()

    class Meta:
        model = Classifier
        exclude = []


class ClassifierExampleSerializer(drf_serializers.ModelSerializer):
    classifier = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)

    class Meta:
        model = ClassifierExample
        exclude = []


class StoredMapSerializer(drf_serializers.ModelSerializer):
    user = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    dataset = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)

    class Meta:
        model = StoredMap
        exclude = ['map_data']