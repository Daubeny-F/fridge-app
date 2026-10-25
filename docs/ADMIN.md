# Administrator guide

The local database has one administrator account: **admin**. Use the password printed during initial setup (also provided in the project handoff). Existing credentials are preserved; no second administrator is created by this update.

## Open the updated panel

If the app was already running when its code changed, stop it with Ctrl+C in its terminal and restart:

```powershell
.\start.ps1
```

Open **http://127.0.0.1:8000/admin/** and sign in as `admin`. You can also sign in through the normal app and choose **Administration** in its sidebar. Ordinary home-cook accounts do not have access to this panel.

## Look inside any user's fridge

1. On the admin dashboard, choose **Browse users’ fridges**.
2. Search by username or name, or browse the paginated list. Empty and inactive accounts are included.
3. Choose **View fridge** beside a user.
4. Read ingredient names, categories, quantities, expiry dates, and freshness indicators.
5. Use **Edit ingredient** to update or remove an ingredient in Django's existing editor.
6. Use **Add ingredient for this user** to add an entry with that user already selected as its owner.

The regular **Users** list and each user's edit page also have a **View fridge** link. These administrative views do not sign you in as the user or change their records merely by viewing them.

## Add more recipes

1. On the admin dashboard, choose **+ Add a recipe**.
2. Enter a title and short description, choose a category, and set minutes and servings.
3. Choose one of the six included illustration styles.
4. In **Cooking steps**, write one step per line. No JSON syntax is needed.
5. Add ingredient rows with a name and required amount. Use **Add another recipe ingredient** for additional rows.
6. Choose **Save**. At least one ingredient and one cooking step are required.

Example:

| Field | Value |
| --- | --- |
| Title | Simple tomato salad |
| Description | Fresh tomatoes, cucumber, and a bright lemon dressing. |
| Category | Vegan |
| Minutes | 10 |
| Servings | 2 |
| Art | Salad |
| Ingredient 1 | tomato — 300 g |
| Ingredient 2 | cucumber — 1 |
| Ingredient 3 | lemon — 1 |

Cooking steps:

```text
Wash and slice the tomatoes and cucumber.
Mix lemon juice with a little olive oil, salt, and pepper.
Toss the vegetables with the dressing and serve.
```

Saved recipes are available to every account when its recipe view reloads. Each account receives its own matching results based on its non-expired fridge ingredients. Ingredient names are normalized, so common aliases such as `tomatoes` and `tomato` match. Duplicate aliases within a recipe are rejected. Match percentages still measure ingredient presence rather than sufficient quantities.

To update or delete a recipe, open **Recipes** and select its title. Existing cooking steps appear as editable lines. Deleting a recipe also removes users' saved links to it, as defined by the database relationships.

## Send an expiry email

On a user's fridge, choose **Email expiry reminder →**, review the recipient and message, then use **Send expiry reminder** (Gmail) or **Save email preview** (local mode). The user must have allowed email reminders and have qualifying ingredients. No message is sent automatically. See [the Gmail email guide](EMAIL.md) for account prerequisites and `start-gmail.ps1`.

## Access control

The `admin` superuser can manage all registered records. The fridge browser additionally checks `kitchen.view_ingredient`, and edit/add links check the corresponding model permissions. A staff account without ingredient-view permission cannot browse other fridges. Signups remain ordinary accounts with personal fridges.

Sending reminders additionally requires `kitchen.add_reminderdelivery`; read-only staff cannot use the send page. Reminder receipts are read-only audit records and distinguish previews from actual email submissions.

For a forgotten local admin password, run:

```powershell
.\.venv\Scripts\python.exe manage.py changepassword admin
```
