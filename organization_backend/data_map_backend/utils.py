from .models import ObjectField


def get_vector_field_dimensions(field: ObjectField):
    return field.generator.embedding_space.dimensions if field.generator and field.generator.embedding_space else \
        (field.embedding_space.dimensions if field.embedding_space else (field.index_parameters or {}).get('vector_size'))
