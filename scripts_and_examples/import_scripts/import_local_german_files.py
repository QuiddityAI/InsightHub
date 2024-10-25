import logging
import time
import os
import sys

from data_backend_client import upload_files, files_in_folder


def import_files(path, dataset_id, max_items=1000000):
    # update_database_layout(dataset_id)
    # done by upload_files route

    batch = []
    batch_size = 10
    total_items = 0
    extensions = (".doc", ".docx", ".pdf", ".ppt", ".pptx", ".xls", ".xlsx", ".txt", )

    for file_path in files_in_folder(path, extensions=extensions)[20:]:
        if "/_" in file_path:
            # this is probably a hidden file (e.g. a template)
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
    import_files("/data/remondis/", 96, 10)
