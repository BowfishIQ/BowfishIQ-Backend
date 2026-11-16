# Lakes API

Lake records are stored in the `lakes` collection. Routes follow the existing
boat-ramp API response format (`status`, `message`, and/or `data`).

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/lakes/` | Create a lake from a JSON body |
| GET | `/lakes/{page}` | List lakes; optional `limit`, `status`, `search_query`, `user_id` query parameters |
| GET | `/lake/{lake_id}` | Read one lake; optional `user_id` filter |
| PUT | `/lake/{lake_id}?user_id=OWNER` | Update supplied fields only |
| DELETE | `/lake/{lake_id}?user_id=OWNER` | Soft-delete a lake |

Example create body:

```json
{
  "user_id": "user-1",
  "name": "Stockton Lake",
  "country": "United States",
  "state": ["Missouri"],
  "latitude": 37.8,
  "longitude": -93.7,
  "water_type": "Lake",
  "water_data": null,
  "gauge_data": "station-1"
}
```

All business fields retain the model's optional behavior. `state` accepts null
or a list with zero, one, or two strings on both create and update. Latitude is
limited to -90 through 90 and longitude to -180 through 180. Create status is
0 (inactive), 1 (active, the default), or 2 (blocked).

`water_data`, when supplied and non-null, must be a valid MongoDB ObjectId string
referencing an existing, undeleted document in the same `lakes` collection.
It is stored and returned as an ID string. `water_type` and `gauge_data` remain
optional strings; no external gauge lookup or water-type enumeration is defined
by the model. Name, address, water type, and exact document ID are searchable.

Updates preserve omitted fields and allow explicit null to clear optional fields.
The body cannot change `user_id`. Update and delete require a nonblank query
`user_id` matching the stored owner, following the existing API convention.
This is a record ownership check using a caller-supplied ID, not authenticated
identity verification. Records created without an owner cannot be updated or
deleted through these owner-scoped endpoints.

Create sets audit timestamps on the server and clears deletion metadata. Update
records `updated_at` and `updated_by`; delete records `deleted_at` and `deleted_by`.
Reads, updates, deletes, and reference checks exclude deleted records. Deleting a
lake does not cascade to other lakes that reference it. List results include all
statuses unless a status filter is supplied. List and detail responses include
the same public user profile lookup used by other location resources.

Invalid request field types or model constraints return HTTP 422. Service errors
(invalid IDs, missing records/references, empty updates, invalid pagination) use
the existing HTTP 200 response envelope with `status: "error"`.
