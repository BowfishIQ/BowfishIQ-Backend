Map locations, boat ramps, and public reports accept an optional `user_id`.

- Create: include `user_id` in the existing model payload to store the owner. Omission or `null` is allowed.
- List and detail GET: pass `?user_id=<id>` to restrict results to that owner. Existing pagination, search, status, and soft-delete filters still apply.
- Update: pass the required query parameter `?user_id=<id>` to require that the stored owner matches. `user_id` is not an update payload field. The ID is used for verification and saved as `updated_by`; it never replaces or clears the owner. Include at least one field to update.
- Delete: pass the required query parameter `?user_id=<id>` to require a matching owner. The soft delete records this ID as `deleted_by`. `deleted_by` is no longer an endpoint parameter.

List and detail responses include `user_details` as a JSON object with `_id`, `name`, `first_name`, `last_name`, and `profile_image` when those profile fields exist. Credentials and private account fields are excluded. `user_details` is `null` for absent/deleted users and anonymous posts. Existing `user_id` fields remain available.

Public reports retain their current multipart payload and image upload interface; put the owner inside the `public_report` JSON field on create, and pass `user_id` in the query string on update.

Update and delete reject missing or blank query IDs, even when an ID is supplied in the payload. The database write matches both the record ID and owner, so mismatched owners cannot modify the record. Records without an owner cannot be updated or deleted through these endpoints until an owner is assigned separately. Create and fetch behavior remains unchanged. These endpoints still use caller-supplied IDs; ownership matching does not authenticate the caller.
