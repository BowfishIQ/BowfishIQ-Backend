# Fish count API

Set the following values in `.env`, then restart the FastAPI server:

```dotenv
OPENAI_API_KEY=your-api-key
OPENAI_FISH_MODEL=gpt-4.1
```

`OPENAI_FISH_MODEL` can be changed to a model supporting image inputs and
structured outputs. The key is read only on the server. Without a key, the
endpoint returns HTTP 503; the rest of the application still starts normally.

Send one static JPEG, PNG, or WebP photo (maximum 20 MB) as the `image` field:

```sh
curl -X POST http://localhost:8000/fish-count/ -F "image=@catch.jpg"
```

You can also upload a photo through `POST /fish-count/` in `/docs`.

The first pass inventories fish with anatomical evidence. The second pass
independently reviews the same original image and the complete first inventory,
reconciling duplicate parts, missed fish, and family assignments. Both passes
use the mandatory Gar/Sucker and Carp/Buffalo anatomy rules. All family names
are constrained to the eleven broad families. The server derives group counts
and the final total from audited rows rather than trusting model totals.

Example response:

```json
{
  "status": "success",
  "data": {
    "auditedFish": [
      {"id": 1, "draftId": 1, "region": "left/top", "family": "Gar", "evidence": "long cylindrical body and extended beak-like snout"}
    ],
    "groups": [{"family": "Gar", "count": 1}],
    "finalTotal": 1,
    "confidence": 80,
    "note": null
  }
}
```

New fish found by the reviewer have `draftId: null`. Only families with positive
counts are included in `groups`. Photos without visible fish return empty lists
and `finalTotal: 0`. Confidence is the model's estimate on a 0–100 scale, not a
measured accuracy guarantee. Notes describe visible limitations.

Errors use FastAPI's `{"detail": "..."}` format: 400 for invalid/empty images,
413 for oversized images, 415 for unsupported/animated images, 422 for a missing
upload field, 503 for missing configuration or AI rate limits, 504 for AI
timeouts, and 502 for failed/refused/incomplete or invalid AI results.

The image is sent to OpenAI twice, in memory, and is not saved locally. Responses
use `store=False`. Each pass has a 120-second timeout and automatic SDK retries
are disabled. A successful call makes two model requests.

Implementation references:
[OpenAI vision inputs](https://developers.openai.com/api/docs/guides/images-vision)
and [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
