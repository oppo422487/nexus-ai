# Gmail and conversation history

Added 27 October 2026 to the Python/Qt Mark engine. No Electron or web UI runtime was added. Google sign-in opens the system browser only for OAuth.

## One-time account connection

1. Open https://console.cloud.google.cপিসি কন্ট্রোল, সার্চ/ডকুমেন্টom/ and create/select a project.
2. Enable **Gmail API** in APIs & Services > Library.
3. Configure **Google Auth Platform** branding/audience. For a personal external test app, add your Gmail account as a test user. Workspace admin restrictions may apply.
4. In Data Access, add `gmail.readonly` and `gmail.send`. No delete or mailbox-modification permission is requested.
5. Create an OAuth client with application type **Desktop app**. Download its client JSON. This is different from the Gemini API key.
6. Click **Gmail কানেক্ট** in Nexa, then **OAuth JSON ফাইল বেছে দিন** to import the downloaded Desktop client JSON. The app validates and saves it as `config/gmail_client.json`. Do not share client/token files or include them in a friend-transfer archive.
7. Restart Nexa, click **Gmail কানেক্ট** in the sidebar, then sign in and grant permissions in Google's browser page. The app logs the connected account. Startup Gmail briefing becomes available on the next launch.

Official setup: https://developers.google.com/workspace/gmail/api/quickstart/python
Scopes: https://developers.google.com/workspace/gmail/api/auth/scopes

Google may require reauthorization when a test app's grant expires. Public distribution with restricted scopes can require Google's verification. This project is not a verified public Google application.

## Use

- “আমার নতুন মেইলগুলো দেখাও, বাংলায় সামারি করো।”
- “আমার টিচারের ঠিকানা teacher@example.com, teacher নামে মনে রাখো।” Confirm the address in the native dialog.
- “teacher-কে formal email draft করো, অসুস্থ বলে কাল ক্লাস করতে পারব না।”
- “এই draft পাঠাও।” Review recipient, subject and the **complete scrollable body**, then physically confirm. Cancel does not send.
- “ওই মেইলটির reply draft করো।” The tool can read the original and send a threaded reply after confirmation. Never infer an unknown address.
- “আগের কথোপকথনে QA project নিয়ে কী বলেছিলাম খুঁজে দেখো।”
- “সংরক্ষিত chat history মুছে দাও।” This asks for confirmation. It does not delete separate long-term memory or contacts.
- “Gmail disconnect করো।” Removes the local token; Google Account third-party access settings revoke the grant at Google.

## Startup and memory limits

After a Gmail account is connected, first engine connection per launch checks up to five unread inbox messages. Their sender, subject and snippets are shown in the content panel and provided to the current model for a short Bengali spoken briefing. Full mail is not read unless requested. This does not mark messages as read. Briefings may repeat unread mail on subsequent launches. Live network/model success is required; it is not a background notification service while the app is closed.

New user/assistant turns logged by the engine and typed native chat are saved in `memory/conversations.sqlite3`. Recall searches this archive without injecting the entire history into every prompt. It cannot recover earlier unarchived sessions or guarantee perfect recall. Contact aliases persist in `memory/gmail.sqlite3`, independently of conversation clear. Existing long-term memory remains supported.

Tokens are stored in `config/gmail_token.json`; these and local history/contact databases are sensitive local files. They are not an encrypted vault. Do not copy them to another person's computer. Connected Gmail snippets/body are provided to the configured AI provider when requesting summaries; use only an account you authorize for that purpose. Mail text is treated as untrusted input, not instructions or authorization to send.

## Validation

Seven isolated tests cover persistent contact lookup, unknown recipient rejection, header injection rejection, no send before approval/cancel, immutable reviewed payload, MIME threading, searchable history and read-only inbox calls. Gmail/model calls are mocked. No real mail has been sent or read during implementation. Live OAuth, inbox summaries and delivery remain unverified until an account is connected.

Backup: `../backups/before-gmail-history-20261027.zip` preserves the changed existing files. New files are additive. Existing document/PC test report remains separate.
