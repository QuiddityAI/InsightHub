import logging
import time

from data_backend_client import upload_files, files_in_folder


def import_files(path, dataset_id, max_items=1000000):
    # update_database_layout(dataset_id)
    # done by upload_files route

    batch = []
    batch_size = 10
    total_items = 0
    extensions = (".doc", ".docx", ".pdf", ".ppt", ".pptx", ".xls", ".xlsx", ".txt", )

    for file_path in files_in_folder(path, extensions=extensions):

        batch.append(file_path)
        total_items += 1

        if len(batch) >= batch_size:
            t1 = time.time()
            upload_files(dataset_id, "filesystem_file_german", 1, 10, "office_document", file_paths=batch, exclude_prefix=path)
            t2 = time.time()
            print(f"Duration: {t2 - t1:.3f}s, time per item: {((t2 - t1)/len(batch))*1000:.2f} ms")
            batch = []

        if total_items >= max_items:
            break

    if batch:
        t1 = time.time()
        upload_files(dataset_id, "filesystem_file_german", 1, 10, "office_document", file_paths=batch, exclude_prefix=path)
        t2 = time.time()
        print(f"Duration: {t2 - t1:.3f}s, time per item: {((t2 - t1)/len(batch))*1000:.2f} ms")


if __name__ == "__main__":
    import_files("/data/remondis/", 96, 20)
