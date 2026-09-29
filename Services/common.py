from math import ceil
import math
from PIL import Image
import os
import re
from typing import Optional, List
from fastapi import APIRouter, Depends, Body, Request, UploadFile, File, Form
import uuid
from pathlib import Path


def replace_nan_with_default(data, default_value=0):
    if isinstance(data, list):
        return [replace_nan_with_default(item, default_value) for item in data]
    elif isinstance(data, dict):
        return {
            key: replace_nan_with_default(value, default_value)
            for key, value in data.items()
        }
    elif isinstance(data, float) and (math.isnan(data) or math.isinf(data)):
        return default_value
    return data


def paginate(collection, query, page=1, limit=10):
    try:
        skip = (page - 1) * limit
        # Check if the query contains a $match stage
        match_stage = next((stage for stage in query if "$match" in stage), None)
        # Create the total pipeline with conditional match stage
        total_pipeline = [match_stage] if match_stage else []
        total_pipeline.append({"$group": {"_id": None, "count": {"$sum": 1}}})
        # Create the data pipeline
        data_pipeline = query + [{"$skip": skip}, {"$limit": limit}]
        # Execute the pipelines using $facet
        pipeline = [{"$facet": {"data": data_pipeline, "total": total_pipeline}}]
        result = list(collection.aggregate(pipeline))[0]
        page_data = replace_nan_with_default(result["data"])
        total_count = result["total"][0]["count"] if result["total"] else 0
        total_pages = ceil(total_count / limit)

        return {
            "page": page,
            "limit": limit,
            "total": total_count,
            "totalPages": total_pages,
            "data": page_data,
            "start_count": skip,
            "end_count": min(skip + limit, total_count),
        }

    except Exception as e:
        return {"message": str(e), "status": "error"}


def convert_oid_to_str(maindata):
    data = []
    for doc in maindata:
        doc["_id"] = str(doc["_id"])
        data.append(doc)
    return data


def sanitize_filename(filename: str) -> str:
    filename = filename.replace(" ", "_")
    filename = re.sub(r"[^a-zA-Z0-9_\-\.]", "", filename)
    return filename


def resize_image(filename, mainFileName, PATH_FILES):

    sizes = [
        {"width": 100, "height": 100, "path": "100/"},
        {"width": 300, "height": 300, "path": "300/"},
    ]

    for size in sizes:
        os.makedirs(PATH_FILES + size["path"], exist_ok=True)
        size_defined = size["width"], size["height"]
        image = Image.open(PATH_FILES + mainFileName, mode="r")
        image.thumbnail(size_defined)
        image.save(
            PATH_FILES + size["path"] + filename + ".webp",
            "webp",
            optimize=True,
            quality=10,
        )
    image = Image.open(PATH_FILES + mainFileName, mode="r")
    image.save(PATH_FILES + filename + ".webp", "webp", optimize=True, quality=10)
    # os.remove(PATH_FILES + mainFileName)


async def save_multiple_files(files: List[UploadFile], folder: str):
    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)
    saved_files = []

    for file in files:
        ext = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        path = folder_path / filename

        with open(path, "wb") as f:
            f.write(await file.read())

        saved_files.append(path.as_posix())  # always forward slash

    return saved_files


async def save_file(file: UploadFile, folder: str):
    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)

    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    path = folder_path / filename

    with open(path, "wb") as f:
        f.write(await file.read())

    return path.as_posix()  # always forward slash
