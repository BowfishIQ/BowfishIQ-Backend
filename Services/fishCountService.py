import base64
from collections import Counter

from fastapi import HTTPException
from openai import APIError, APITimeoutError, OpenAI, RateLimitError
from pydantic import ValidationError

from config import OPENAI_API_KEY, OPENAI_FISH_MODEL
from Models.FishCount import FISH_FAMILIES, FishAudit, FishGroup, FishInventory
from Services.fishCountPrompts import INVENTORY_PROMPT, REVIEW_PROMPT


def _run_pass(client, image_url, instructions, text, schema):
    response = client.responses.parse(
        model=OPENAI_FISH_MODEL,
        instructions=instructions,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": text},
                {"type": "input_image", "image_url": image_url, "detail": "high"},
            ],
        }],
        text_format=schema,
        max_output_tokens=12000,
        store=False,
    )
    if response.status != "completed" or response.output_parsed is None:
        raise HTTPException(502, "AI audit did not return a complete result")
    return schema.model_validate(response.output_parsed)


def count_fish(image_bytes, mime_type):
    if not OPENAI_API_KEY:
        raise HTTPException(503, "Fish counting is not configured. Set OPENAI_API_KEY and restart the server.")

    image_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    try:
        with OpenAI(api_key=OPENAI_API_KEY, timeout=120.0, max_retries=0) as client:
            draft = _run_pass(
                client, image_url, INVENTORY_PROMPT,
                "Inventory every distinct visible fish in this original photo.", FishInventory,
            )
            if [row.id for row in draft.fish] != list(range(1, len(draft.fish) + 1)):
                raise ValueError("Non-sequential draft IDs")
            draft.total = len(draft.fish)
            audit = _run_pass(
                client, image_url, REVIEW_PROMPT,
                "Review the original photo independently. Junior inventory:\n" + draft.model_dump_json(),
                FishAudit,
            )

        # Never trust model-supplied totals; derive them from the verified rows.
        ids = [row.id for row in audit.auditedFish]
        draft_ids = [row.draftId for row in audit.auditedFish if row.draftId is not None]
        if len(ids) != len(set(ids)) or len(draft_ids) != len(set(draft_ids)):
            raise ValueError("Duplicate fish references")
        if not set(draft_ids).issubset({row.id for row in draft.fish}):
            raise ValueError("Unknown draft reference")
        for index, fish in enumerate(audit.auditedFish, start=1):
            fish.id = index
        counts = Counter(fish.family for fish in audit.auditedFish)
        audit.groups = [FishGroup(family=family, count=counts[family])
                        for family in FISH_FAMILIES if counts[family]]
        audit.finalTotal = len(audit.auditedFish)
        return {"status": "success", "data": audit.model_dump()}
    except APITimeoutError:
        raise HTTPException(504, "AI fish audit timed out") from None
    except RateLimitError:
        raise HTTPException(503, "AI service is currently unavailable; try again later") from None
    except APIError:
        raise HTTPException(502, "Unable to complete the AI fish audit") from None
    except (ValueError, ValidationError):
        raise HTTPException(502, "AI audit returned an invalid inventory") from None
