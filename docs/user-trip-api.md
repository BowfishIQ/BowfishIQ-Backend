# User trip details and summary APIs

## 1. Paginated trip details

`GET /users/{user_id}/trip-details`

Examples:

```text
/users/USER_ID/trip-details
/users/USER_ID/trip-details?page=2&limit=20
/users/USER_ID/trip-details?date=12-10-2026
/users/USER_ID/trip-details?start_date=2026-10-01&end_date=2026-10-12
/users/USER_ID/trip-details?trip_id=TRIP_OBJECT_ID
/users/USER_ID/trip-details?scope=owner&trip_type=2
```

Response follows the existing pagination shape:

```json
{
  "status": "success",
  "data": {
    "page": 1,
    "limit": 10,
    "total": 1,
    "totalPages": 1,
    "data": [{"_id": "TRIP_OBJECT_ID", "user_id": "USER_ID", "date": "12-10-2026"}],
    "start_count": 0,
    "end_count": 1
  }
}
```

The `data` array returns all existing trip model fields. Default order is newest
trip date first; `sort_order=asc` returns oldest first. Creation time and trip ID
break ties. Trips without a valid date sort after dated trips in descending order.

`lake_locations` returns full map-location objects instead of IDs:

```json
"lake_locations": [
  {
    "_id": "bf3000000000000000000001",
    "name": "Demo Lake - North Cove",
    "country": "United States",
    "state": "Missouri",
    "city": "Demo City",
    "zip_code": "00000",
    "latitude": "38.2500",
    "longitude": "-93.4000",
    "status": 1,
    "created_at": "2026-09-20 12:00:00"
  }
]
```

Available creation/update audit fields are also returned. Location order follows
the stored references. Missing, invalid, or soft-deleted locations are omitted;
trips with no resolved locations return `lake_locations: []`. Records are resolved
in one batch for the requested page. Trip writes still accept location IDs, and
the `lake_location_id` filter still accepts an ID.

## 2. Summary counts

`GET /users/{user_id}/trip-details/summary`

```text
/users/USER_ID/trip-details/summary
/users/USER_ID/trip-details/summary?start_date=2026-10-01&end_date=2026-10-12
/users/USER_ID/trip-details/summary?date=12-10-2026&trip_type=2
/users/USER_ID/trip-details/summary?trip_id=TRIP_OBJECT_ID
```

Returns `{"status": "success", "data": {...}}` with:

| Field | Meaning |
| --- | --- |
| `total_trips` | Unique matching trips |
| `owned_trips`, `crew_trips` | Trips owned by / listing this user as active crew; these can overlap |
| `regular_trips`, `scouting_trips` | Trip types 1 and 2 |
| `total_fish_caught` | Sum of active `fish_shot_details.count` across matching trips |
| `total_fish_seen_not_shot` | Sum of `fish_see_not_shot_count` |
| `total_team_shots` | Sum of active `team_details.shot_count`; separate from fish catches |
| `total_crew_entries`, `total_team_entries` | Active entries accumulated across trips; repeated members count again |
| `total_images` | Number of trip image entries |
| `largest_fish_weight_lb`, `largest_fish_length_inches` | Maximum recorded active catch measurements |
| `user_role_counts` | Number of trips the requested user participated in as captain, shooter, spotter, guest, other |
| `team_role_counts` | Number of active team entries by role across matching trips |
| `fish_counts` | Catch counts grouped by fish ID and name |
| `breakdowns` | Trip counts by trip type, status, water type/salinity/clarity/movement/level/base, wind/direction, fish location, launch ramp |

`user_role_counts` and `team_role_counts` always contain `captain`, `shooter`,
`spotter`, `guest`, and `other`. Roles accept codes `1`–`5` or the corresponding
names, ignoring case and surrounding whitespace. Unknown/missing roles count as
`other`. Duplicate crew entries for the same user and role within one trip count
once in `user_role_counts`. A user with multiple roles can count in multiple roles
for one trip. No role is inferred from trip ownership or a team member's name.
Crew/team/fish entries with status 0 or 2 are excluded; null/missing nested status
is treated as active. Empty results return zeros and empty breakdowns.

**Schema limit:** catches belong to the trip, not an individual shooter.
`team_details` has no `user_id`, and `crew_details` has no catch/shot count.
Consequently `total_fish_caught` and `total_team_shots` are trip/team totals,
not personal catches. Personal catch counts require a user ID on catch or team
records. `user_role_counts` uses only `crew_details.user_id` and `posuser_role`.

## Shared filters

| Query parameter | Values / behavior |
| --- | --- |
| `date` | Exact trip date, `DD-MM-YYYY` or `YYYY-MM-DD` |
| `start_date`, `end_date` | Inclusive date range; either endpoint may be omitted |
| `trip_id` | MongoDB trip ObjectId; always combined with the user filter |
| `scope` | `all` (default): owner or active crew; `owner`: only owned trips; `crew`: only active crew trips |
| `trip_type` | 1 regular, 2 scouting |
| `status` | 0 inactive, 1 active, 2 blocked; omitted includes all trip statuses |
| `water_type` | 1 lake/reservoir, 2 river/creek, 3 pond/small water, 4 coastal |
| `water_salinity` | 1 freshwater, 2 brackish, 3 saltwater |
| `lake_location_id` | A location ID in the trip's `lake_locations` array |

Omit all date parameters for **all days**. Do not combine `date` with range
parameters. Date filters use the trip's `date`, not `created_at`, and correctly
compare dates across months/years. Undated/malformed-date records remain in
all-day results but are excluded when a date filter is applied.

List-only parameters: `page` (default 1, minimum 1), `limit` (default 10, 1–100),
`sort_order` (`desc` or `asc`). Summary covers all matching trips with no pagination.
Both APIs exclude soft-deleted trips and accept string user IDs or MongoDB
ObjectId strings, matching both string and BSON references. Invalid parameters
return HTTP 422. A valid unknown user/trip returns an empty result.

Date conversion supports the current string schema. For large collections,
migrating to a BSON trip date and adding indexes on owner/crew IDs and trip dates
would improve range filtering. These endpoints follow the existing public trip
routes; a supplied user ID is a filter, not proof of authorization.
