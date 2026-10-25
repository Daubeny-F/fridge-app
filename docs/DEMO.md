# A 6-minute Fridgewise demonstration

## 1. Introduce the problem (30 seconds)

“We forget what is in our fridge and buy food we already have. Fridgewise tracks ingredients, suggests recipes from them, and warns us before their expiry dates.”

Explain that the app uses a Python/Django backend, a JavaScript frontend, and a SQLite database. Show the architecture and database diagram in the README.

## 2. Show an existing kitchen (1 minute)

1. Start the app with `start.ps1`. Open http://127.0.0.1:8000/.
2. Sign in as `demo` using `FreshStart!2026`.
3. Point out the ingredient total, use-soon total, and ready-to-cook count.
4. Open **My fridge**. Search for `tomato`, switch categories, and change sorting.
5. Add a new ingredient with tomorrow's expiry date. Point out the reminder badge.
6. Edit its quantity, then refresh the browser to demonstrate database persistence.

## 3. Demonstrate recipe matching (1 minute)

1. Open **Recipe ideas** and select **Ready to cook**.
2. Open **Garden greens & feta**. Explain the green checks and cooking steps.
3. Save the recipe using the heart; show it in **Saved recipes**.
4. Open a recipe with missing ingredients and add them to the shopping list.
5. Open **Shopping list** and check off an item.

Explain that “ready” means all required ingredient names are present and non-expired. Amounts are displayed for the cook to verify; the algorithm does not perform unit conversion. Common aliases such as `tomatoes` and `tomato` are recognized.

## 4. Show reminders (1 minute)

1. Open **Expiry reminders**. Point out dates and warning badges.
2. Set an ingredient's date to yesterday; it appears as expired and no longer contributes to recipe matches.
3. In **Settings**, change the warning window and enable **Allow expiry reminder emails** for the demo.
4. Sign in as admin, open the demo user's fridge, and select **Email expiry reminder →**.
5. Review the recipient and contents, click **Save email preview**, then show the generated file in `outbox/`.
6. Explain that local previews are limited to one per user per day and that nothing is emailed automatically.

For an actual inbox demonstration, start with `start-gmail.ps1`, use an opted-in account with a real email address, and click **Send expiry reminder**. See `docs/EMAIL.md` for Gmail App Password setup.

## 5. Show accounts and administration (1 minute)

1. Sign out. Create a new account and show its empty fridge.
2. Explain that one user's ingredients, shopping list, and favorites are invisible to other home cooks.
3. Sign out and sign in as `admin` using the password printed during setup.
4. Open **Administration**. Show users and ingredients from all accounts.
5. Open a recipe and show that required ingredients and cooking steps can be edited.
6. Point out the distinction between a normal user, staff permissions, and a superuser.

Do not delete the sole administrator during the demonstration. Password recovery for this local lab is performed from the management terminal with `changepassword`.

## 6. Show evidence (30 seconds)

Run `.\.venv\Scripts\python.exe manage.py test` and show the passing functional/security tests. Show the database migration file and one test that prevents a user from modifying someone else's ingredients.

Close by discussing straightforward extensions: quantity-aware matching, PostgreSQL hosting, email verification/password reset, more recipes, and a Rust/Yew client using the same JSON API.
