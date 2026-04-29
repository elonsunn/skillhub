import json
import requests
from pathlib import Path


class SkillHubAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _raise_for_error(resp: requests.Response) -> None:
    if not resp.ok:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise SkillHubAPIError(resp.status_code, detail)


def list_packages(server: str, search: str = None, tag: str = None) -> list:
    params = {}
    if search:
        params["search"] = search
    if tag:
        params["tag"] = tag
    resp = requests.get(f"{server}/api/packages", params=params)
    _raise_for_error(resp)
    return resp.json()


def get_package(server: str, name: str):
    resp = requests.get(f"{server}/api/packages/{name}")
    if resp.status_code == 404:
        return None
    _raise_for_error(resp)
    return resp.json()


def download_package(server: str, name: str, version: str = None) -> bytes:
    if version is None:
        version = "latest"
    resp = requests.get(f"{server}/api/packages/{name}/{version}")
    _raise_for_error(resp)
    return resp.content


def push_package(server: str, name: str, zip_path: Path, metadata: dict) -> dict:
    with open(zip_path, "rb") as f:
        resp = requests.post(
            f"{server}/api/packages/{name}",
            files={"file": f},
            data={"metadata": json.dumps(metadata)},
        )
    _raise_for_error(resp)
    return resp.json()
