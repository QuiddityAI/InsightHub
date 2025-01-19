import os
import mimetypes


class FileUploadManager:
    """Context manager to handle file uploads for requests."""
    def __init__(self, file_paths):
        self.file_paths = file_paths
        self.files = {}

    def __enter__(self):
        """Initialize file handling and return the file dictionary."""
        self.open_files = []  # List to store open file objects
        for idx, file_path in enumerate(self.file_paths):
            try:
                # Get MIME type using mimetypes
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    mime_type = "application/octet-stream"  # Default MIME type if unknown

                # Open the file and store the file object
                file_obj = open(file_path, "rb")
                self.open_files.append(file_obj)

                # Add to the files dictionary
                self.files[f"file_{idx}"] = (os.path.basename(file_path), file_obj, mime_type)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")

        return self.files  # Return the file dictionary for usage

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close all file objects when exiting the context."""
        for file_obj in self.open_files:
            file_obj.close()
