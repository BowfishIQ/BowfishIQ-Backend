Trip create and update use the same required model payload and optional image uploads as public reports:

- `POST /trip-details/`
- `PUT /trip-detail/{trip_details_id}`

For file uploads, send `multipart/form-data` with `trip_details` containing a JSON string and one or more file parts named `images`. Swagger shows the file inputs on both endpoints. The JSON uses the updated model keys:

```json
{
  "crew_details": [
    {"user_id": "user-1", "user_name": "Alex", "user_role": ["1", "2"]}
  ],
  "team_details": [
    {"name": "Alex", "role": ["1", "2"], "shot_count": 3}
  ],
  "fish_location": ["1", "3"]
}
```

Send `{}` in `trip_details` for an upload without other trip fields. Files are saved under `uploads/trip_details` with unique filenames; their relative paths are stored in the trip's `images` list and returned by trip reads. Resolve these paths against the API base URL to display images.

On update, uploading files without an `images` key in the JSON retains the stored images and adds the new files. To select which existing images to retain, provide their paths in the JSON `images` list; new files are appended to that list. Use `"images": []` with files to replace the list, or without files to clear it. Updating other fields without uploading files leaves images unchanged. Clearing a list does not delete files from disk.

For requests without uploaded files, send the JSON as the `trip_details` form field; an `images` list of existing paths can be included in that JSON. Trip summaries count each crew/team role and fish location from the new lists, while continuing to read older scalar values and the legacy `posuser_role` key.
