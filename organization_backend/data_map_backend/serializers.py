from rest_framework import serializers as drf_serializers

from .models import ObjectSchema, ObjectField, Generator, EmbeddingSpace, SearchHistoryItem, ItemCollection, StoredMap


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

    class Meta:
        model = ObjectField
        exclude = ['created_at', 'changed_at', '_order', 'description']


class ObjectSchemaSerializer(drf_serializers.ModelSerializer):
    object_fields = ObjectFieldSerializer(many=True, read_only=True)
    primary_key = drf_serializers.StringRelatedField(many=False, read_only=True)
    thumbnail_image = drf_serializers.StringRelatedField(many=False, read_only=True)
    descriptive_text_fields = drf_serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = ObjectSchema
        exclude = ['created_at', 'changed_at']


class SearchHistoryItemSerializer(drf_serializers.ModelSerializer):
    user = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    schema = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)

    class Meta:
        model = SearchHistoryItem
        exclude = ['changed_at']


class ItemCollectionSerializer(drf_serializers.ModelSerializer):
    user = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    schema = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)

    class Meta:
        model = ItemCollection
        exclude = []


class StoredMapSerializer(drf_serializers.ModelSerializer):
    user = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    schema = drf_serializers.PrimaryKeyRelatedField(many=False, read_only=True)

    class Meta:
        model = StoredMap
        exclude = ['map_data']