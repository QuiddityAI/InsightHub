import time
import os

from data_backend_client import upload_files, files_in_folder
import csv

csv_log = []


def import_files(path, dataset_id, max_items=1000000):
    # update_database_layout(dataset_id)
    # done by upload_files route

    batch = []
    batch_size = 10
    total_items = 0
    extensions = (".doc", ".docx", ".pdf", ".ppt", ".pptx", ".xls", ".xlsx", ".txt", )
    skip_first = 0
    csv_log.append([dataset_id, max_items, path, skip_first])

    for i, file_path in enumerate(files_in_folder(path, extensions=extensions)):
        if i < skip_first:
            continue
        if "/_" in file_path:
            # this is probably a hidden file (e.g. a template)
            continue
        if file_path.split("/")[-1].startswith("~$"):
            # this is probably a temporary file
            continue

        # fix problems with surrogateescape encoding:
        try:
            file_path.encode("utf-8")
        except UnicodeEncodeError:
            # there is a non-utf-8 character in the path, use ISO-8859-1 to decode it
            iso_file_path = file_path.encode("utf-8", "surrogateescape")
            file_path = iso_file_path.decode("ISO-8859-1")
            utf8_file_path = file_path.encode("utf-8")
            print(f"Fixing encoding of file path: {iso_file_path} -> {utf8_file_path} ({file_path})")
            for part in range(len(file_path.split("/"))):
                part_path = "/".join(file_path.split("/")[:part+1])
                if not part_path:
                    continue
                if not os.path.exists(part_path):
                    base_folder = "/".join(part_path.split("/")[:-1]).encode("utf-8")
                    end = part_path.split("/")[-1]
                    utf8_end = end.encode("utf-8")
                    iso_end = end.encode("ISO-8859-1")
                    orig_path = os.path.join(base_folder, iso_end)
                    new_path = os.path.join(base_folder, utf8_end)
                    print(f"Renaming folder / file: {orig_path} -> {new_path} ({part_path})")
                    os.rename(orig_path, new_path)

        # if file bigger than 50MB, skip it
        file_size_bytes = os.path.getsize(file_path)
        if file_size_bytes > 50 * 1024 * 1024:
            print(f"File too big: {file_path}")
            csv_log.append([i, total_items, file_path, "file too big"])
            continue
        if file_size_bytes == 0:
            print(f"Empty file: {file_path}")
            csv_log.append([i, total_items, file_path, "empty file"])
            continue

        batch.append(file_path)
        total_items += 1
        print(file_path.split("/")[-1])

        if len(batch) >= batch_size:
            print(f"Uploading batch of {len(batch)} items, index {i}")
            t1 = time.time()
            result = upload_files(dataset_id, "filesystem_file_german", 1, 10, "office_document", file_paths=batch, exclude_prefix=path)
            t2 = time.time()
            duration = t2 - t1
            per_item = duration / len(batch)
            print(f"--- Duration: {duration:.3f}s, time per item: {per_item:.2f} s")
            csv_log.append([i, total_items, duration, per_item])
            for failed_file in result['status']['failed_files']:
                csv_log.append([i, total_items, failed_file['filename'], 'failed: ' + failed_file['reason']])
            failed_filenames = [failed_file['filename'] for failed_file in result['status']['failed_files']]
            for file in batch:
                if file.split("/")[-1] not in failed_filenames:
                    csv_log.append([i, total_items, file, "success"])
            batch = []

        if total_items >= max_items:
            break

    if batch:
        t1 = time.time()
        result = upload_files(dataset_id, "filesystem_file_english", 1, 10, "office_document_en", file_paths=batch, exclude_prefix=path)
        t2 = time.time()
        duration = t2 - t1
        per_item = duration / len(batch)
        print(f"--- Duration: {duration:.3f}s, time per item: {per_item:.2f} s")
        csv_log.append([i, total_items, duration, per_item])
        for failed_file in result['status']['failed_files']:
            csv_log.append([i, total_items, failed_file['filename'], 'failed: ' + failed_file['reason']])
        failed_filenames = [failed_file['filename'] for failed_file in result['status']['failed_files']]
        for file in batch:
            if file.split("/")[-1] not in failed_filenames:
                csv_log.append([i, total_items, file, "success"])

    print(f"Total items: {total_items}")


if __name__ == "__main__":
    try:
        import_files("/data2/datasets/realkie_business_documents/charities/files/", 102, 150)
    finally:
        with open(f"import_log_{time.strftime('%Y%m%d_%H%M%S')}.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerows(csv_log)

