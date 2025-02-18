import pickle
import time
from typing import Any, List, Optional

import requests
from pydantic import Field
from quiddity_client.utils import FileUploadManager
from requests.exceptions import RequestException

from data_map_backend.models import (
    RunSearchTaskPayload,
    SearchResult,
    SearchTaskSettings,
)


class QuiddityClient:
    COOKIES_FILE = "cookies.pkl"

    def __init__(
        self, username: str, password: str, organization_id: int = 1, api_base: str = "http://localhost:56440"
    ):
        self.username = username
        self.password = password
        self.api_base = api_base
        self.session = requests.Session()
        self.user_id = None
        self.organization_id = organization_id
        self.login_url = f"{self.api_base}/org/login_from_app/"
        self.current_user_url = f"{self.api_base}/org/data_map/get_current_user"

        self.load_cookies()
        if not self.is_logged_in():
            self.login()
        if not self.is_logged_in():
            raise ValueError("Login failed")

    def login(self):
        try:
            response = self.session.post(
                self.login_url,
                data={"email": self.username, "password": self.password},
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
            response = self.session.get(self.current_user_url)
            if response.status_code != 200:
                return False
            self.user_id = response.json().get("id")
            return self.user_id is not None
        except RequestException:
            return False

    def get_current_user(self):
        try:
            self.load_cookies()
            response = self.session.get(self.current_user_url)
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
                f"{self.api_base}/api/v1/search/perform_search",
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
        response = self.session.post(f"{self.api_base}/org/data_map/create_dataset_from_schema", json=payload)
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
        response = self.session.post(f"{self.api_base}/org/data_map/available_organizations")
        response.raise_for_status()
        resp = response.json()
        res = {}
        for org in resp:
            res[org["id"]] = org["datasets"]
        return res

    def _is_running(self, dataset_id: int, task_id: str) -> dict[str, Any]:
        payload = {"dataset_id": dataset_id}
        resp = self.session.post(f"{self.api_base}/data_backend/upload_files/status", json=payload)
        resp.raise_for_status()
        tasks = resp.json()
        task = [task for task in tasks if task["task_id"] == task_id]
        if not task:
            return dict(running=False)
        task = task[0]
        if task["is_running"]:
            return dict(running=True)
        if "inserted_ids" in task:
            return dict(running=False, inserted_ids=[t[1] for t in task["inserted_ids"]])
        return dict(running=False)

    def upload_files(
        self,
        file_paths: List[str],
        dataset_id: int,
        schema_identifier: str = "filesystem_file_english",
        import_converter: str = "office_document",
        block: bool = True,
    ) -> None | list[str]:
        # Create the form-data fields
        data = {
            "dataset_id": dataset_id,
            "schema_identifier": schema_identifier,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "import_converter": import_converter,
        }

        with FileUploadManager(file_paths) as files:
            response = self.session.post(f"{self.api_base}/api/v1/ingest/upload_files", data=data, files=files)

        task_id = response.json().get("task_id")
        if block:
            is_running = True
            while is_running:
                time.sleep(1)
                resp = self._is_running(dataset_id, task_id)
                is_running = resp["running"]
            return resp.get("inserted_ids")

    def remove_items(self, dataset_id: int, item_ids: List[str]) -> bool:
        payload = {"dataset_id": dataset_id, "item_ids": item_ids}

        try:
            response = self.session.post(f"{self.api_base}/org/data_map/remove_items", json=payload)
            response.raise_for_status()
            return True
        except RequestException as e:
            print(f"Remove items request failed: {e}")
            return False
