# Send expiry reminders manually through Gmail

The app sends an email only after an administrator reviews a user's reminder and presses **Send expiry reminder**. Startup never sends emails and no reminder worker or scheduler runs.

## 1. Prepare your sender Gmail account

In your own browser, turn on **2-Step Verification** for the Google account that will send the messages. Open [Google App Passwords](https://myaccount.google.com/apppasswords), create an App Password named **Fridgewise**, and keep it for the terminal prompt below. Use the generated 16-character App Password rather than your normal Google password.

Google requires 2-Step Verification for App Passwords. The option may be unavailable for accounts using only security keys, some school/work accounts, or Advanced Protection. If unavailable, use an eligible sender account or implement OAuth as a separate integration. See [Google's App Password help](https://support.google.com/accounts/answer/185833?hl=en). Create the credential yourself; do not paste it into a chat or source file.

## 2. Start the app in Gmail mode

Stop the existing server with Ctrl+C in the terminal that started it. This also stops an old reminder worker if you are upgrading from the previous startup script.

In the project folder:

```powershell
.\start-gmail.ps1
```

The script asks for:

1. The Gmail address to send from.
2. The App Password in a hidden prompt.

It configures Gmail SMTP at `smtp.gmail.com`, port `587`, using TLS, with the sender address as the SMTP username and From address. These settings follow [Google's Gmail SMTP guidance](https://knowledge.workspace.google.com/admin/gmail/send-email-from-a-printer-scanner-or-app).

The password is passed to Django through the process environment. It is not written to files, stored in the application database, printed, or passed in command-line arguments. When the script finishes, it restores its previous environment values. Enter the password again on the next Gmail-mode startup. The script does not send a test email at startup.

`start.ps1` continues to support local file previews when no SMTP environment override is present. `.env.example` is a reference only, not an automatically loaded secrets file.

## 3. Prepare the recipient

- The user must have a real email address under **Admin → Users**. A demo `example.com` address cannot receive real mail and is blocked in SMTP mode.
- The user enables **Allow expiry reminder emails** in **Settings**. If it is disabled, the admin preview explains why the Send button is unavailable.
- At least one fridge ingredient must be past its date or expire within that user's chosen warning window (1–14 days).
- Inactive accounts are excluded.

## 4. Send with the button

1. Open http://127.0.0.1:8000/admin/ and sign in as the administrator.
2. Choose **Browse users’ fridges → View fridge** for the intended recipient.
3. Click **Email expiry reminder →**.
4. Check **To**, **From**, **Subject**, and the full message body.
5. Press **Send expiry reminder**.

The message lists only that user's qualifying ingredients, quantities, and dates. The recipient comes from the selected user's database record; a submitted form cannot redirect mail to another address. Opening the preview does not send anything. The preview is valid for ten minutes and must be refreshed if relevant details change.

Success means the SMTP server accepted the message. Check the recipient's inbox and spam folder to confirm final receipt. Network or authentication errors display a generic error without exposing credentials or provider replies; unsuccessful attempts do not create a success receipt and can be retried.

There is a database-enforced limit of one email per user per calendar date in Europe/Bucharest. Double-clicking, refreshing, or resubmitting the same form does not intentionally send another copy that day. Admin → **Reminder deliveries** records the user, recipient, date/time, channel, ingredient count, and requesting admin.

## Local demonstration without credentials

Run `start.ps1` without SMTP environment overrides. The preview page explicitly says **Local preview mode**, and the final button says **Save email preview**. Clicking saves an email in the ignored `outbox/` folder and reports that no email was sent. A local preview has a separate daily limit, so it will not block a later real Gmail send.

## Troubleshooting

- **Email reminders not enabled:** the recipient enables the setting in their account.
- **No ingredients in the window:** add an ingredient with an appropriate date, or adjust the warning window.
- **Demo email address:** replace it in Admin → Users with a real recipient address.
- **Local preview instead of Send:** stop the server and start with `start-gmail.ps1`.
- **Could not send:** verify the sender address, its Google App Password, internet connection, and account eligibility. Changing the Google account password revokes its App Passwords; generate a replacement if necessary, as described in Google's help.
- **Already sent today:** check Reminder deliveries. The next manual send is available on the next calendar date; there is no automatic send at midnight.

No real Gmail message is sent by the automated tests. You must configure the sender locally and perform the final inbox test yourself.
