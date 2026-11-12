# Kalaburagi Grievance Tracker — SOLVATHON 2026, Problem Statement 2

Team: Tony Madhuri (leader) and Abhinav Reddy, IIIT Raichur.
Problem statement 2: Follow-up and Reminder System for Grievance Tracking.

This is a student prototype that runs on sample data. It is not an official government system, and the timelines in it are placeholders that each department must replace.

It grew out of our earlier Chennai complaint portal. The workflow (register, route, assign, escalate, confirm) was reused. The district data, the reminders, the communication log, Kannada, documents, the police pilot and the DC dashboard are new for this hackathon.

## What the problem statement asks, and where it is

| Asked for | Where it is in the portal |
|---|---|
| Register a grievance with documents | Register Complaint: 3 photos for everyday complaints, up to 3 photos or PDFs for police complaints (JPEG, PNG, WebP, PDF, checked by file content, 4 MB each). Officers open them from the complaint. |
| Kannada and English | Switch on every citizen page. A complaint written in Kannada gets Kannada follow-up messages, detected from the text. |
| Department and officer assignment | The type of complaint sets the department. The taluk and level set the officer. 6 departments, 16 complaint types, 11 taluks, 65 wards (sample data). |
| Status and action history | Track Complaint shows the steps and a history. Officers add notes. Every action is stored with its time and actor. |
| Automatic reminders | At 50% and at 80% of each time limit the officer is reminded. Each reminder is sent once per level. It goes to the officer's Notices screen, to the complaint history and to a communication log, and the citizen is told. |
| Overdue monitoring | A background check every 30 seconds marks complaints past their limit. The DC overview counts them. |
| Escalation | When the limit passes, the complaint moves up one level (station, sub-division, division, department head, DC Office). A citizen who says "not fixed" also moves it up. |
| Communication history | The log of every message, per complaint, for officers. Citizens see their own messages on Track Complaint. |
| Interactive dashboard | District overview for the DC Office: pending, overdue, escalated, resolved, by department and by taluk, how high up pending complaints are, the oldest pending complaints, and the average days to resolve. It refreshes every 5 seconds. |
| Police Department pilot | 5 categories: cybercrime, financial fraud, lost property, public safety and traffic, complaint involving individuals. The portal only registers and tracks. The text says that whether an FIR is filed is decided only by authorised police officials. |

## Run it

You need Python 3.12 or 3.13. No internet and no model are needed.

```
python -m pip install -r requirements.txt
python -m pytest -q
python portal/manage.py seed-demo --password "a-long-password"
python portal/manage.py seed-sample   # optional: invented citizens and complaints
python portal/server.py --demo-minutes 2
```

Open http://127.0.0.1:8000. Kalaburagi is the default district. To run the old Chennai data, set `PORTAL_DISTRICT=chennai`.

`--demo-minutes 2` makes every time limit 2 minutes, so reminders and escalation happen while you watch. A citizen's login code is shown on screen when no SMS service is set up.

Demo accounts (password is the one you gave to seed-demo): `district.head` is the DC Office. Each department has `water.depot`, `water.deputy_ae`, `water.area_engineer`, `water.superintendent_engineer`, and the same for `roads`, `health`, `sanitation`, `police` and `general`. Officers log in on the first screen under Officer Login.

## Put it online (GitHub and Render)

The portal needs only Python, so any host that runs a Dockerfile works. These steps use Render's free plan.

1. Make a new GitHub repository (for example `kalaburagi-grievance-tracker`). In the project folder run:
   ```
   git init
   git add .
   git commit -m "Kalaburagi Grievance Tracker for Solvathon 2026"
   git branch -M main
   git remote add origin https://github.com/<your-user>/kalaburagi-grievance-tracker.git
   git push -u origin main
   ```
2. On render.com sign in with GitHub. Choose New, then Blueprint, pick the repository, and press Apply. `render.yaml` sets everything up. Render asks for `DEMO_PASSWORD`: type a password of at least 8 characters. That is the password of every demo officer account, including `district.head`.
3. When the build finishes (about 3 minutes), Render shows the link, for example `https://kalaburagi-grievance-tracker.onrender.com`.

Things to know about the free plan:
- The service sleeps after about 15 minutes without visitors. The first visit after that takes about a minute to wake it. Open the link a few minutes before you present.
- It has no disk. Every restart clears the data and loads the invented sample data again (`SEED_SAMPLE=1`), so the dashboards are never empty.
- `COMPLAINT_PORTAL_DEMO_MINUTES=3` makes every new time limit 3 minutes, so judges can see reminders and escalation. Delete that setting in Render to use the sample days instead.
- Without an SMS service, login codes are shown on screen, so anyone with the link can sign in as any citizen. That is fine for a demo with invented data. Do not put real complaints or real mobile numbers in it, and give the officer password only to the judges.
- The AI sorting option (a local model or Gemini) is off online. The keyword sorting does not need any API key. Never put an API key in the repository.

## WhatsApp chat bot (optional, and it works with the demo data)

Citizens can do everything by chatting with one WhatsApp number, in English or Kannada, without a password. WhatsApp
itself proves the phone number.

| They send | What happens |
|---|---|
| a number from the menu, or "hi" | the menu: 1 register, 2 track, 3 my complaints, 4 confirm a fix, 5 website login code, 6 language |
| a description of the problem in their own words | with Claude on, it works out the kind and category and asks only for what is missing; without it, it asks with menus |
| the questions for a new complaint | kind, category, description, place (text or a location pin, or "same" for home), 3 photos for everyday complaints (police: optional), a check, then submit |
| a complaint ID | its status, office, deadline and latest update |
| "4" after an officer marks a complaint resolved | confirm it is fixed (a code closes it) or say it is not (it moves up a level) |

The other direction: once someone has written to the bot, the portal's follow-ups (registered, officer reminded,
escalated, marked resolved) are also pushed to their WhatsApp. The communication log shows the channel.

Safety points built in: a new Emergency complaint first says to call 112; police complaints show the notice that FIR
decisions stay with police officials; the Claude model only picks from fixed lists and never writes what the bot says
or the complaint that is filed; webhooks are accepted only with a valid signature; a number can send at most 20
messages a minute; Claude calls are capped per day.

### Set it up with the Twilio WhatsApp sandbox (about 10 minutes, free)

1. Create a Twilio account. In the console open Messaging, Try it out, Send a WhatsApp message. It shows the sandbox
   number (+1 415 523 8886) and a join message such as `join silver-tiger`.
2. From each phone that will test it, send that join message to the sandbox number. The join lasts 72 hours, so repeat
   it before the demo.
3. In Render, Environment, add these variables (never put them in GitHub):
   `WHATSAPP_PROVIDER` = `twilio`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` = `+14155238886`,
   `PUBLIC_URL` = `https://kalaburagi-grievance-tracker.onrender.com`, and optionally `WHATSAPP_JOIN_TEXT` = your join
   message (it fills the website's chat link). Add `ANTHROPIC_API_KEY` to let Claude read free-text messages.
4. In the Twilio console, on the sandbox settings page, set "When a message comes in" to
   `https://kalaburagi-grievance-tracker.onrender.com/api/whatsapp` with method POST. Save.
5. Send "hi" from your phone. The menu should come back.

The WhatsApp Cloud API (Meta) works too: set `WHATSAPP_PROVIDER=meta`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`,
`WHATSAPP_VERIFY_TOKEN` (any text you invent) and `WHATSAPP_APP_SECRET`, and point the webhook at the same `/api/whatsapp`
address. Meta lets us send free-form messages only within 24 hours of the person's last message. For later updates set
`WHATSAPP_UPDATE_TEMPLATE` to an approved utility template whose body is `{{1}}`.

Login codes for the website also go to the person's WhatsApp when the chat is on (and no separate SMS provider is set).
If the message cannot be sent, the code is shown on screen as before.

Things to know:
- Render's free plan sleeps after 15 minutes. Twilio waits about 15 seconds for the webhook, so a message sent to a
  sleeping service is lost. Open the website a few minutes before the demo, or ping it every 10 minutes (for example
  with a free uptime monitor).
- Twilio's free-form messages work only within 24 hours of the person's last message. Reminders in the demo come within
  minutes, so this does not matter there.
- The phone number is the identity. Do not use it for real complaints until a real provider, a privacy notice and the
  department's approval are in place.
- With a Claude key set, the text of free-form messages goes to Anthropic's API. Use invented data in the demo.
- Cost: the bot uses the small, cheap model by default and stops after `WHATSAPP_AI_DAILY_LIMIT` calls a day (300).
- The bot's Kannada is a first draft, like the rest. Have a Kannada speaker read `complaint_tools/complaint_portal/wa_bot.py`.

## Demo script for Round 1 (5 minutes)

Start the server with `--demo-minutes 2` and have two browser windows ready: one logged in as a citizen, one as `district.head`. Sign the citizen up beforehand (name, mobile 9876543210, any address in Kalaburagi).

1. (30 s) Citizen window, English. Open Register Complaint. Choose Not emergency, Roads and Footpaths, add 3 photos, describe a pothole, submit. Show the complaint ID, the department, the "Follow-up due" time and the message the citizen receives.
2. (30 s) Switch the language to Kannada. Register a second complaint in Kannada (for example about no water supply). Show that the confirmation message is in Kannada.
3. (30 s) Register a police complaint (cybercrime). Show the notice that the portal only registers and tracks, and that an FIR is decided by police officials.
4. (60 s) DC window. Open Notices. About a minute after registering, the 50% reminders appear by themselves. Open one complaint: show the documents, the history and the communication log.
5. (60 s) District overview. Show pending, by department, by taluk and the oldest pending list.
6. (60 s) Wait for the 2-minute limit. The complaint moves up to the sub-division officer. Show the escalation in the history and the new notice. Then, as the citizen, open Track Complaint and show the messages to the citizen.
7. (30 s) As an officer, mark one complaint resolved. As the citizen, confirm it. Show it counted as Resolved in the overview.

If something goes wrong, `python portal/manage.py check-overdue` runs the reminder and escalation check once, from the command line.

## Slide outline (10 minutes: about 3 for the pitch, 5 for the demo, 2 for questions)

1. The problem: citizens file a grievance and then do not know where it is. Officers forget. Nobody sees what is overdue.
2. What we built: register once, route to the right department, remind the officer before the limit, escalate when it passes, tell the citizen at every step.
3. How a complaint moves: station, sub-division, division, department head, DC Office. A reminder at 50% and 80%.
4. Kannada and English, documents, and the police pilot with its rule that officials decide FIR matters.
5. The DC dashboard: pending, overdue, escalated, by department and taluk.
6. Live demo.
7. Feasibility and what is next: real timelines from each department, a real SMS provider, and a review of the Kannada by a native speaker. It runs on a laptop with only Python, and the same code runs Chennai or Kalaburagi from a data pack.

## Honest limits (say these if asked)

- The time limits for Kalaburagi are sample numbers made by us. They are not from any department.
- The taluks and wards are real taluk names, but ward numbers 56 to 65 are placeholders and no street-level matching exists.
- The Kannada text (screens, messages, keywords) is a first draft. A native speaker should review it. History entries and the router's draft message stay in English.
- Reminders are not sent by SMS. They are kept in the portal log, and pushed to WhatsApp for people who have chatted with the bot (within 24 hours of their last message). Real SMS needs a provider and approved message templates.
- Officer and worker screens are in English only.
- The Flutter app in this repository was not updated or compiled for this version. The web portal is the demo.
- Login codes appear on screen when no SMS service is set up. This is for the demo only.

## Where things are

- `data/charter_kalaburagi.json`: departments, complaint types, time limits, escalation levels, Kannada names.
- `data/kalaburagi_zones.csv`, `data/kalaburagi_wards.csv`: taluks and wards.
- `complaint_tools/complaint_portal/workflow.py`: the portal logic, reminders (`send_reminders`) and the DC summary (`district_summary`).
- `complaint_tools/complaint_portal/messages.py`: the follow-up message texts in English and Kannada.
- `portal/assets/i18n.js`: the Kannada switch for the screens.
- `tests/test_solvathon.py`: tests for everything above.


## Final round additions (12 Nov 2026)

- `/share` shows a QR code and link for the live site, and how to use three devices (citizen phone, worker phone, officer laptop). `/qr.svg` and `/qr.png` make the code (add `?u=<address>` for another link).
- `/about` ("How it works") lists the agents and models and where each is used, where the number of days come from, and the datasets. It reads the charter and data files, so it always matches what the portal does.
- Data is kept when the host restarts: with `DATABASE_URL` set (Render Postgres), `durable.py` saves a copy of the database and photos a few seconds after any change and restores it at start (`manage.py restore`). Logins are saved too.
- With `ANTHROPIC_API_KEY` set, Claude (claude-haiku-5-5) picks the complaint type from the charter list when a complaint is registered. It can only choose a listed type; days, owners and replies still come from the charter. Limit 300 calls a day (`COMPLAINTROUTER_CLAUDE_DAILY_LIMIT`).
- With a public `PUBLIC_URL`, the service visits itself every 10 minutes so the free plan does not sleep (`KEEP_AWAKE=0` turns this off).
- Offline fallback: `HOST=0.0.0.0 PORT=8000 python portal/server.py` on a laptop; phones on the same Wi-Fi open `http://<laptop address>:8000/share`.
