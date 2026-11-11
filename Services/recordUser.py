def user_details_stages():
    """Join public profile fields without exposing credentials or dropping old records."""
    return [
        {
            "$lookup": {
                "from": "user",
                "let": {
                    "user_id": "$user_id",
                    "object_id": {
                        "$convert": {
                            "input": "$user_id", "to": "objectId",
                            "onError": None, "onNull": None,
                        }
                    },
                },
                "pipeline": [
                    {"$match": {
                        "$expr": {"$in": ["$_id", ["$$user_id", "$$object_id"]]},
                        "deleted_at": {"$in": ["", None]},
                    }},
                    {"$project": {
                        "_id": {"$toString": "$_id"},
                        "name": 1, "first_name": 1, "last_name": 1,
                        "profile_image": 1,
                    }},
                ],
                "as": "user_details",
            }
        },
        {"$set": {"user_details": {
            "$cond": [
                {"$eq": ["$post_anonymous", True]},
                None,
                {"$ifNull": [{"$arrayElemAt": ["$user_details", 0]}, None]},
            ]
        }}},
    ]
