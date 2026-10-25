# Fridgewise JSON API

All routes require a Django session. Unauthenticated JSON requests return HTTP 401. Sign in through `/login/`. Mutations require the `X-CSRFToken` header using the page's CSRF cookie. The frontend helper in `static/app.js` demonstrates this. JSON payloads must be objects. Each user's fridge, favorites, settings, and shopping list are scoped on the server.

| Method | Route | Behavior |
| --- | --- | --- |
| GET | `/api/state/` | Current user, ingredients, personalized recipes, shopping list, settings, and server-local date |
| POST | `/api/ingredients/` | Create an ingredient |
| PUT | `/api/ingredients/{id}/` | Replace editable fields of an owned ingredient |
| DELETE | `/api/ingredients/{id}/` | Remove an owned ingredient |
| POST | `/api/recipes/{id}/favorite/` | Toggle a favorite; returns `{"favorite": true/false}` |
| POST | `/api/shopping/` | Add normalized names; duplicates are skipped |
| PUT | `/api/shopping/{id}/` | Update an owned item's checked state |
| DELETE | `/api/shopping/{id}/` | Remove an owned shopping item |
| PUT | `/api/settings/` | Update reminder preferences |
| GET | `/api/export/` | Download only the current user's inventory as CSV |

### Ingredient create/update

```json
{
  "name": "tomatoes",
  "category": "vegetables",
  "quantity": "300",
  "unit": "g",
  "expires_on": "2026-11-01"
}
```

Categories: `vegetables`, `fruit`, `dairy`, `protein`, `grains`, `pantry`.
Units: `g`, `kg`, `ml`, `l`, `pcs`, `pack`.
Quantity must be positive with at most two decimal places. Names are at most 80 characters and dates use ISO `YYYY-MM-DD`. Dates in the past are allowed to record existing expired items, but those items never match recipes. The owner is always the authenticated user; a supplied owner ID is ignored.

### Shopping list

```json
{"names": ["tomato", "chickpea"]}
```

The list must contain 1–50 nonempty strings, each at most 80 characters. Whitespace-only values are rejected. Check an item with `{"checked": true}`; strings such as `"true"` are not accepted.

### Preferences

```json
{"reminder_days": 3, "email_reminders": true}
```

The reminder window is an integer from 1 through 14. Enabling emails allows an administrator to send a reminder manually; it does not schedule any mail. The account needs an email address.

### Errors

- 400: `{"error": "message"}` or `{"errors": {"field": ["message"]}}`.
- 401: No authenticated session.
- 403: CSRF validation failure.
- 404: Record does not exist or does not belong to the user. Django may return an HTML 404 body.
- 405: HTTP method not supported.

Administrative CRUD is provided through `/admin/`, guarded by Django staff/model permissions. A superuser can manage every registered model.

The admin dashboard also provides `/admin/fridges/` (searchable user list) and `/admin/fridges/{user_id}/` (one user's inventory). These are server-rendered pages requiring staff access and the ingredient-view permission. Recipe creation at `/admin/kitchen/recipe/add/` accepts cooking steps one per line and ingredient rows; the saved records feed the existing personalized JSON API.

`GET /admin/fridges/{user_id}/reminder/` previews one user's expiry email without sending. `POST` to the same route requires CSRF and the signed confirmation from a fresh preview, staff access, ingredient-view permission, and `kitchen.add_reminderdelivery`. Recipient, actor, date, message, and relevant configuration changes are checked before sending. Consent, active account status, valid recipient, due ingredients, email setup, and daily duplicate checks are enforced on the server. File previews and email have separate delivery records and daily limits.
