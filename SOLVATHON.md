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
- Reminders are not sent by SMS. They are kept in the portal log. Real SMS needs a provider and approved message templates.
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
