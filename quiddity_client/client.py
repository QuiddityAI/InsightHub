from datetime import datetime
import pickle
import time
import requests
from requests.exceptions import RequestException
from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict
from .models import SearchTaskSettings, RunSearchTaskPayload, SearchResult
from .utils import FileUploadManager


class QuiddityClient:
    API_BASE_URL = "http://localhost:56440"
    LOGIN_URL = f"{API_BASE_URL}/org/login_from_app/"
    API_URL = f"{API_BASE_URL}/org/data_map/get_current_user"
    COOKIES_FILE = "cookies.pkl"

    def __init__(self, username: str, password: str, organization_id: int = 1):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.user_id = None
        self.organization_id = organization_id
        self.load_cookies()
        if not self.is_logged_in():
            self.login()
        if not self.is_logged_in():
            raise ValueError("Login failed")

    def login(self):
        try:
            response = self.session.post(
                self.LOGIN_URL,
                data={"username": self.username, "password": self.password},
            )
            response.raise_for_status()
            with open(self.COOKIES_FILE, "wb") as f:
                pickle.dump(self.session.cookies, f)
        except RequestException as e:
            print(f"Login failed: {e}")

    def load_cookies(self):
        try:
            with open(self.COOKIES_FILE, "rb") as f:
                self.session.cookies.update(pickle.load(f))
        except FileNotFoundError:
            print("Cookies file not found. Please login first.")

    def is_logged_in(self):
        try:
            response = self.session.get(self.API_URL)
            if response.status_code != 200:
                return False
            self.user_id = response.json().get("id")
            return True
        except RequestException:
            return False

    def get_current_user(self):
        try:
            self.load_cookies()
            response = self.session.get(self.API_URL)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            print(f"API request failed: {e}")
            return None

    def perform_search(
        self,
        dataset_id: int,
        user_input: str,
        collection_id: int,
        class_name: str = "_default",
        **kwargs,
    ):
        settings = SearchTaskSettings(dataset_id=dataset_id, user_input=user_input, **kwargs)
        payload = RunSearchTaskPayload(collection_id=collection_id, class_name=class_name, search_task=settings)
        try:
            response = self.session.post(
                f"{self.API_BASE_URL}/api/v1/search/perform_search",
                json=payload.model_dump(),
            )
            response.raise_for_status()
            return [SearchResult.model_validate(r) for r in response.json()]
        except RequestException as e:
            print(f"Search request failed: {e}")
            return None

    def create_dataset(
        self, name: str, schema_identifier: str = "filesystem_file_english", from_ui: bool = True
    ) -> int:
        payload = {
            "name": name,
            "organization_id": self.organization_id,
            "schema_identifier": schema_identifier,
            "from_ui": from_ui,
        }
        response = self.session.post(f"{self.API_BASE_URL}/org/data_map/create_dataset_from_schema", json=payload)
        response.raise_for_status()
        resp = response.json()
        return resp["id"]

    def list_datasets(self) -> dict[int, list[int]]:
        """
        Retrieves a list of datasets for each organization.

        Sends a POST request to the specified URL to fetch available organizations and their datasets.
        Parses the JSON response and constructs a dictionary mapping organization IDs to their respective datasets.

        Returns:
            dict[int, list[int]]: A dictionary where the keys are organization IDs and the values are lists of dataset IDs.

        Raises:
            requests.exceptions.HTTPError: If the HTTP request returned an unsuccessful status code.
        """
        response = self.session.post(f"{self.API_BASE_URL}/org/data_map/available_organizations")
        response.raise_for_status()
        resp = response.json()
        res = {}
        for org in resp:
            res[org["id"]] = org["datasets"]
        return res

    def _is_running(self, dataset_id: str) -> Optional[str]:
        payload = {"dataset_id": dataset_id}
        resp = self.session.post(f"{self.API_BASE_URL}/data_backend/upload_files/status", json=payload)
        resp.raise_for_status()
        tasks = resp.json()
        is_running = [task["is_running"] for task in tasks]
        if any(is_running):
            return True
        return False

    def upload_files(
        self,
        file_paths: List[str],
        dataset_id: int,
        schema_identifier: str = "filesystem_file_english",
        import_converter: str = "office_document",
        block: bool = True,
    ) -> None:
        # Create the form-data fields
        data = {
            "dataset_id": dataset_id,
            "schema_identifier": schema_identifier,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "import_converter": import_converter,
        }

        with FileUploadManager(file_paths) as files:
            response = self.session.post(f"{self.API_BASE_URL}/api/v1/ingest/upload_files", data=data, files=files)

        task_id = response.json().get("task_id")
        if block:
            while self._is_running(dataset_id):
                time.sleep(1)
