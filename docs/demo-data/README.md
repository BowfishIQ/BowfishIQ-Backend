# River Arrow Crew demo data

Seven linked players, five trips (three regular, two scouting), and two fictional
map locations. All seven members participate in every trip; captain and shooter
roles rotate. All users and trips are active and not deleted. Dates span
25 September–11 October 2026 for date/range filtering.

The application has no persistent team entity or team ID. This fixture represents
one team through the same seven `crew_details.user_id` references and matching
`team_details` names on every trip. The team name is recorded in `trip_notes`.
Fish are identified by name; `fish_id` is null because no fish catalogue exists.
Images are empty because no image files are supplied.

## Generate or insert

```powershell
# Generate local JSON only; no database connection.
python seed_demo.py

# Insert into the database configured in db.py.
python seed_demo.py --apply
```

The insert command creates missing records and skips previously seeded records.
It never replaces existing records. It checks seed-ID/email collisions before
inserting. If a database error interrupts insertion, rerun the same command to
insert the remaining records. It does not change the existing superadmin seed.

JSON arrays use MongoDB Extended JSON (`{"$oid": "..."}`) for document `_id` values.
User references inside trips remain strings, matching the application models.
Files correspond to collections `user`, `trip_details`, and `map_location`.
Importing through the seed command preserves BSON ObjectIds. `manifest.json`
contains user/trip IDs, credentials, example API URLs, and expected counts.

## Demo accounts

Every account uses email/password login (`login_type: 2`) with password
`BowfishDemo@123`. Password fields in `user.json` contain bcrypt hashes.

| Name | Email |
| --- | --- |
| Alex Morgan | alex.morgan@example.com |
| Jamie Reed | jamie.reed@example.com |
| Taylor Brooks | taylor.brooks@example.com |
| Jordan Hayes | jordan.hayes@example.com |
| Casey Parker | casey.parker@example.com |
| Riley Bennett | riley.bennett@example.com |
| Sam Carter | sam.carter@example.com |

## Test the trip APIs after insertion

Alex's user ID: `bf1000000000000000000001`.

```text
/users/bf1000000000000000000001/trip-details?page=1&limit=2
/users/bf1000000000000000000001/trip-details?scope=owner
/users/bf1000000000000000000001/trip-details?date=02-10-2026
/users/bf1000000000000000000001/trip-details?start_date=2026-10-01&end_date=2026-10-12
/users/bf1000000000000000000001/trip-details/summary
```

Default all-day summary for any member: **5 trips, 3 regular, 2 scouting,
73 fish caught, 87 seen but not shot, 35 crew entries, 35 team entries**.
Catches: 47 Carp, 17 Buffalo, 9 Gar. Alex owns two trips and is captain on two,
shooter on one, guest on one, and other on one. October filtering returns three
trips, including one scouting trip, with 55 fish caught.
