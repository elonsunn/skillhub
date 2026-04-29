import os
from fastapi import APIRouter

router = APIRouter()
STORAGE_ROOT = os.getenv("STORAGE_ROOT", "storage")
