

UPLOADED_FILES_FOLDER = "/data/quiddity_data/uploaded_files"


def store_thumbnail(png_data: bytes, sub_path):
    with open(f'{UPLOADED_FILES_FOLDER}/{sub_path}.thumbnail.png', 'wb') as f:
        f.write(png_data)
    return f'{sub_path}.thumbnail.png'
