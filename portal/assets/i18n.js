/* English / Kannada switch for the citizen pages.

   It swaps text for the Kannada below, using exact matches on the English the pages already show, so no page
   needs data attributes. Switching back restores the English. Text that comes from the server (a complaint
   description, a message already written in the complaint's language) is left as it is.

   The Kannada here is a first draft and has NOT been reviewed by a native speaker. Check it before real use. */
(function () {
  "use strict";

  const KEY = "portal_lang";

  const KN = {
    // Brand and footer
    "Kalaburagi Grievance Tracker": "ಕಲಬುರಗಿ ಕುಂದುಕೊರತೆ ಟ್ರ್ಯಾಕರ್",
    "Follow-up and reminders for citizen grievances": "ನಾಗರಿಕರ ದೂರುಗಳ ಅನುಸರಣೆ ಮತ್ತು ನೆನಪೋಲೆ",
    "Made by Abhinav Reddy and Tony Madhuri. Student prototype for Solvathon 2026. Not an official government system.":
      "ಅಭಿನವ್ ರೆಡ್ಡಿ ಮತ್ತು ಟೋನಿ ಮಧುರಿ ರಚಿಸಿದ್ದಾರೆ. ಸಾಲ್ವಥಾನ್ 2026ಕ್ಕಾಗಿ ವಿದ್ಯಾರ್ಥಿ ಮಾದರಿ. ಇದು ಅಧಿಕೃತ ಸರ್ಕಾರಿ ವ್ಯವಸ್ಥೆಯಲ್ಲ.",
    "Unofficial demo": "ಅನಧಿಕೃತ ಡೆಮೊ",
    "Language": "ಭಾಷೆ",

    // Menus
    "Main": "ಮುಖ್ಯ",
    "Home": "ಮುಖಪುಟ",
    "Register Complaint": "ದೂರು ನೋಂದಾಯಿಸಿ",
    "Track Complaint": "ದೂರು ಟ್ರ್ಯಾಕ್ ಮಾಡಿ",
    "Services": "ಸೇವೆಗಳು",
    "How It Works": "ಇದು ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ",
    "Your account": "ನಿಮ್ಮ ಖಾತೆ",
    "Your details": "ನಿಮ್ಮ ವಿವರಗಳು",
    "Log out": "ಲಾಗ್ ಔಟ್",
    "Name": "ಹೆಸರು",
    "Mobile": "ಮೊಬೈಲ್",
    "Address": "ವಿಳಾಸ",
    "Zone": "ವಲಯ (ತಾಲೂಕು)",
    "Ward": "ವಾರ್ಡ್",
    "Sign-up": "ನೋಂದಣಿ",
    "User sign-up": "ಬಳಕೆದಾರ ನೋಂದಣಿ",
    "Worker sign-up": "ಕಾರ್ಮಿಕ ನೋಂದಣಿ",
    "Officer sign-up": "ಅಧಿಕಾರಿ ನೋಂದಣಿ",
    "User Sign-up": "ಬಳಕೆದಾರ ನೋಂದಣಿ",
    "Worker Sign-up": "ಕಾರ್ಮಿಕ ನೋಂದಣಿ",
    "Officer Sign-up": "ಅಧಿಕಾರಿ ನೋಂದಣಿ",

    // First screen
    "Registered once": "ಒಮ್ಮೆ ನೋಂದಣಿ",
    "Auto reminders": "ಸ್ವಯಂ ನೆನಪೋಲೆ",
    "Escalated on time": "ಸಮಯಕ್ಕೆ ಮೇಲ್ಮಟ್ಟಕ್ಕೆ",
    "Your voice matters": "ನಿಮ್ಮ ಧ್ವನಿ ಮುಖ್ಯ",
    "Choose how to log in": "ಲಾಗಿನ್ ಮಾಡುವ ವಿಧಾನ ಆಯ್ಕೆಮಾಡಿ",
    "User Login": "ಬಳಕೆದಾರ ಲಾಗಿನ್",
    "Worker Login": "ಕಾರ್ಮಿಕ ಲಾಗಿನ್",
    "Officer Login": "ಅಧಿಕಾರಿ ಲಾಗಿನ್",
    "Mobile number": "ಮೊಬೈಲ್ ಸಂಖ್ಯೆ",
    "Enter your 10-digit mobile number": "ನಿಮ್ಮ 10 ಅಂಕಿಯ ಮೊಬೈಲ್ ಸಂಖ್ಯೆಯನ್ನು ನಮೂದಿಸಿ",
    "You get a 6-digit code by SMS or WhatsApp on this number. If it is not set up on the server, the code appears here instead.":
      "ಈ ಸಂಖ್ಯೆಗೆ SMS ಅಥವಾ WhatsApp ಮೂಲಕ 6 ಅಂಕಿಯ ಕೋಡ್ ಬರುತ್ತದೆ. ಸರ್ವರ್‌ನಲ್ಲಿ ಇದು ಸಿದ್ಧವಿಲ್ಲದಿದ್ದರೆ ಕೋಡ್ ಇಲ್ಲಿಯೇ ಕಾಣಿಸುತ್ತದೆ.",
    "Workers get a 6-digit code by SMS or WhatsApp on this number. If it is not set up on the server, the code appears here instead.":
      "ಕಾರ್ಮಿಕರಿಗೆ ಈ ಸಂಖ್ಯೆಗೆ SMS ಅಥವಾ WhatsApp ಮೂಲಕ 6 ಅಂಕಿಯ ಕೋಡ್ ಬರುತ್ತದೆ. ಸರ್ವರ್‌ನಲ್ಲಿ ಇದು ಸಿದ್ಧವಿಲ್ಲದಿದ್ದರೆ ಕೋಡ್ ಇಲ್ಲಿಯೇ ಕಾಣಿಸುತ್ತದೆ.",
    "Send me a code": "ನನಗೆ ಕೋಡ್ ಕಳುಹಿಸಿ",
    "Sign up as a citizen": "ನಾಗರಿಕರಾಗಿ ನೋಂದಾಯಿಸಿ",
    "Prefer WhatsApp?": "ವಾಟ್ಸಾಪ್ ಇಷ್ಟವೇ?",
    "Chat with us on WhatsApp": "ವಾಟ್ಸಾಪ್‌ನಲ್ಲಿ ನಮ್ಮೊಂದಿಗೆ ಚಾಟ್ ಮಾಡಿ",
    "Code": "ಕೋಡ್",
    "Enter the 6-digit code": "6 ಅಂಕಿಯ ಕೋಡ್ ನಮೂದಿಸಿ",
    "Log in": "ಲಾಗಿನ್",
    "Use a different mobile number": "ಬೇರೆ ಮೊಬೈಲ್ ಸಂಖ್ಯೆ ಬಳಸಿ",
    "Don't have an account?": "ಖಾತೆ ಇಲ್ಲವೇ?",
    "Click here to sign up": "ನೋಂದಾಯಿಸಲು ಇಲ್ಲಿ ಕ್ಲಿಕ್ ಮಾಡಿ",
    "Sign up as a worker": "ಕಾರ್ಮಿಕರಾಗಿ ನೋಂದಾಯಿಸಿ",
    "New worker?": "ಹೊಸ ಕಾರ್ಮಿಕರೇ?",
    "Username": "ಬಳಕೆದಾರ ಹೆಸರು",
    "Your officer username": "ನಿಮ್ಮ ಅಧಿಕಾರಿ ಬಳಕೆದಾರ ಹೆಸರು",
    "Password": "ಪಾಸ್‌ವರ್ಡ್",
    "Officer logins end at midnight every day (India time).": "ಅಧಿಕಾರಿ ಲಾಗಿನ್ ಪ್ರತಿದಿನ ಮಧ್ಯರಾತ್ರಿ (ಭಾರತೀಯ ಸಮಯ) ಮುಕ್ತಾಯವಾಗುತ್ತದೆ.",
    "New officer?": "ಹೊಸ ಅಧಿಕಾರಿಯೇ?",
    "How the portal works": "ಪೋರ್ಟಲ್ ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ",
    "Previous": "ಹಿಂದಿನದು",
    "Next": "ಮುಂದಿನದು",

    // Sign-up
    "Enter your details below to create your account.": "ಖಾತೆ ರಚಿಸಲು ನಿಮ್ಮ ವಿವರಗಳನ್ನು ಕೆಳಗೆ ನಮೂದಿಸಿ.",
    "Fields marked with": "ಗುರುತಿಸಿದ ಕ್ಷೇತ್ರಗಳು",
    "are mandatory": "ಕಡ್ಡಾಯ",
    "Enter your name": "ನಿಮ್ಮ ಹೆಸರನ್ನು ನಮೂದಿಸಿ",
    "House No. / Street / Area": "ಮನೆ ಸಂಖ್ಯೆ / ರಸ್ತೆ / ಪ್ರದೇಶ",
    "Used to find your zone. Include your area name.": "ನಿಮ್ಮ ತಾಲೂಕನ್ನು ಗುರುತಿಸಲು ಬಳಸಲಾಗುತ್ತದೆ. ನಿಮ್ಮ ಪ್ರದೇಶದ ಹೆಸರನ್ನು ಸೇರಿಸಿ.",
    "Loading zones ...": "ವಲಯಗಳು ಲೋಡ್ ಆಗುತ್ತಿವೆ ...",
    "Select a zone ...": "ವಲಯ ಆಯ್ಕೆಮಾಡಿ ...",
    "Ward / Area": "ವಾರ್ಡ್ / ಪ್ರದೇಶ",
    "Select a zone first": "ಮೊದಲು ವಲಯ ಆಯ್ಕೆಮಾಡಿ",
    "Select your ward ...": "ನಿಮ್ಮ ವಾರ್ಡ್ ಆಯ್ಕೆಮಾಡಿ ...",
    "Country": "ದೇಶ",
    "State": "ರಾಜ್ಯ",
    "District": "ಜಿಲ್ಲೆ",
    "You log in with a code to this number.": "ಈ ಸಂಖ್ಯೆಗೆ ಬರುವ ಕೋಡ್‌ನಿಂದ ನೀವು ಲಾಗಿನ್ ಮಾಡುತ್ತೀರಿ.",
    "Reset": "ಮರುಹೊಂದಿಸಿ",
    "Submit": "ಸಲ್ಲಿಸಿ",
    "Already signed up?": "ಈಗಾಗಲೇ ನೋಂದಾಯಿಸಿದ್ದೀರಾ?",
    "Log in with your mobile number": "ಮೊಬೈಲ್ ಸಂಖ್ಯೆಯಿಂದ ಲಾಗಿನ್ ಮಾಡಿ",

    // Home
    "Report water, road, health, sanitation and police problems. Follow every step and get reminders until it is resolved.":
      "ನೀರು, ರಸ್ತೆ, ಆರೋಗ್ಯ, ನೈರ್ಮಲ್ಯ ಮತ್ತು ಪೊಲೀಸ್ ಸಮಸ್ಯೆಗಳನ್ನು ದೂರು ನೀಡಿ. ಪ್ರತಿ ಹಂತವನ್ನು ಗಮನಿಸಿ, ಪರಿಹಾರವಾಗುವವರೆಗೆ ನೆನಪೋಲೆ ಪಡೆಯಿರಿ.",
    "Common Services": "ಸಾಮಾನ್ಯ ಸೇವೆಗಳು",
    "Report a problem to the right department of Kalaburagi district.": "ಕಲಬುರಗಿ ಜಿಲ್ಲೆಯ ಸರಿಯಾದ ಇಲಾಖೆಗೆ ಸಮಸ್ಯೆಯನ್ನು ತಿಳಿಸಿ.",
    "Register a complaint": "ದೂರು ನೋಂದಾಯಿಸಿ",
    "Drinking Water": "ಕುಡಿಯುವ ನೀರು",
    "No water, low pressure, a broken pipe or dirty water.": "ನೀರು ಬರುತ್ತಿಲ್ಲ, ಕಡಿಮೆ ಒತ್ತಡ, ಒಡೆದ ಪೈಪ್ ಅಥವಾ ಕೊಳಕು ನೀರು.",
    "Roads and Potholes": "ರಸ್ತೆ ಮತ್ತು ಗುಂಡಿಗಳು",
    "A damaged road, pothole or blocked footpath.": "ಹಾಳಾದ ರಸ್ತೆ, ಗುಂಡಿ ಅಥವಾ ಅಡ್ಡಿಯಾದ ಪಾದಚಾರಿ ಮಾರ್ಗ.",
    "Streetlights": "ಬೀದಿ ದೀಪಗಳು",
    "A streetlight that is off, flickering or damaged.": "ಆರಿರುವ, ಮಿನುಗುವ ಅಥವಾ ಹಾಳಾದ ಬೀದಿ ದೀಪ.",
    "Sanitation and Drains": "ನೈರ್ಮಲ್ಯ ಮತ್ತು ಚರಂಡಿಗಳು",
    "Garbage not collected, a blocked drain or a local tax issue.": "ಕಸ ಸಂಗ್ರಹವಾಗಿಲ್ಲ, ಚರಂಡಿ ಕಟ್ಟಿಕೊಂಡಿದೆ ಅಥವಾ ಸ್ಥಳೀಯ ತೆರಿಗೆ ಸಮಸ್ಯೆ.",
    "Health and Hospitals": "ಆರೋಗ್ಯ ಮತ್ತು ಆಸ್ಪತ್ರೆಗಳು",
    "A problem at a government hospital or health centre.": "ಸರ್ಕಾರಿ ಆಸ್ಪತ್ರೆ ಅಥವಾ ಆರೋಗ್ಯ ಕೇಂದ್ರದಲ್ಲಿನ ಸಮಸ್ಯೆ.",
    "Police Complaint": "ಪೊಲೀಸ್ ದೂರು",
    "Cybercrime, fraud, lost property or traffic. We only register and track it.":
      "ಸೈಬರ್ ಅಪರಾಧ, ವಂಚನೆ, ಕಳೆದುಹೋದ ವಸ್ತು ಅಥವಾ ಸಂಚಾರ. ನಾವು ನೋಂದಣಿ ಮತ್ತು ಟ್ರ್ಯಾಕಿಂಗ್ ಮಾತ್ರ ಮಾಡುತ್ತೇವೆ.",
    "Your complaints in numbers": "ನಿಮ್ಮ ದೂರುಗಳ ಸಂಖ್ಯೆ",
    "Your Complaints in Numbers": "ನಿಮ್ಮ ದೂರುಗಳ ಸಂಖ್ಯೆ",
    "From your account. Updates on its own.": "ನಿಮ್ಮ ಖಾತೆಯಿಂದ. ತಾನಾಗಿಯೇ ನವೀಕರಣವಾಗುತ್ತದೆ.",
    "Registered": "ನೋಂದಾಯಿತ",
    "In progress": "ಪ್ರಗತಿಯಲ್ಲಿದೆ",
    "Waiting for you": "ನಿಮ್ಮ ಪ್ರತಿಕ್ರಿಯೆಗಾಗಿ ಕಾಯುತ್ತಿದೆ",
    "Resolved": "ಪರಿಹಾರವಾಗಿದೆ",
    "From complaint to resolution, in four simple steps.": "ದೂರಿನಿಂದ ಪರಿಹಾರದವರೆಗೆ, ನಾಲ್ಕು ಸರಳ ಹಂತಗಳಲ್ಲಿ.",
    "1. Register": "1. ನೋಂದಾಯಿಸಿ",
    "Describe the problem in English or Kannada. Add a photo or document if you have one.":
      "ಸಮಸ್ಯೆಯನ್ನು ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ವಿವರಿಸಿ. ಫೋಟೋ ಅಥವಾ ದಾಖಲೆ ಇದ್ದರೆ ಸೇರಿಸಿ.",
    "2. Auto-route": "2. ಸ್ವಯಂ ರವಾನೆ",
    "It goes to the right department and officer for your area.": "ಅದು ನಿಮ್ಮ ಪ್ರದೇಶದ ಸರಿಯಾದ ಇಲಾಖೆ ಮತ್ತು ಅಧಿಕಾರಿಗೆ ಹೋಗುತ್ತದೆ.",
    "3. Track and get reminders": "3. ಟ್ರ್ಯಾಕ್ ಮಾಡಿ, ನೆನಪೋಲೆ ಪಡೆಯಿರಿ",
    "See the status and history. Reminders go out before the time limit ends.":
      "ಸ್ಥಿತಿ ಮತ್ತು ಇತಿಹಾಸ ನೋಡಿ. ಕಾಲಮಿತಿ ಮುಗಿಯುವ ಮೊದಲು ನೆನಪೋಲೆ ಹೋಗುತ್ತದೆ.",
    "4. Escalate or resolve": "4. ಮೇಲಕ್ಕೆ ಕಳುಹಿಸಿ ಅಥವಾ ಪರಿಹರಿಸಿ",
    "If the time limit passes, it moves up to the next officer. You confirm the fix.":
      "ಕಾಲಮಿತಿ ಮೀರಿದರೆ ಅದು ಮುಂದಿನ ಅಧಿಕಾರಿಗೆ ಹೋಗುತ್ತದೆ. ಪರಿಹಾರವನ್ನು ನೀವು ದೃಢೀಕರಿಸುತ್ತೀರಿ.",
    "Your Complaints": "ನಿಮ್ಮ ದೂರುಗಳು",
    "When an officer marks a complaint resolved, confirm here whether the problem is fixed.":
      "ಅಧಿಕಾರಿ ದೂರನ್ನು ಪರಿಹಾರವಾಗಿದೆ ಎಂದು ಗುರುತಿಸಿದಾಗ, ಸಮಸ್ಯೆ ಸರಿಯಾಗಿದೆಯೇ ಎಂದು ಇಲ್ಲಿ ದೃಢೀಕರಿಸಿ.",
    "Live": "ಲೈವ್",
    "You have not registered a complaint yet.": "ನೀವು ಇನ್ನೂ ದೂರು ನೋಂದಾಯಿಸಿಲ್ಲ.",
    "You have not registered a complaint yet. Your complaints will appear here.": "ನೀವು ಇನ್ನೂ ದೂರು ನೋಂದಾಯಿಸಿಲ್ಲ. ನಿಮ್ಮ ದೂರುಗಳು ಇಲ್ಲಿ ಕಾಣಿಸುತ್ತವೆ.",

    // Register
    "Tell us what is wrong. The complaint goes to the officer for your field and ward.":
      "ಏನು ತೊಂದರೆ ಎಂದು ತಿಳಿಸಿ. ದೂರು ನಿಮ್ಮ ಪ್ರದೇಶದ ಸಂಬಂಧಪಟ್ಟ ಅಧಿಕಾರಿಗೆ ಹೋಗುತ್ತದೆ.",
    "Today": "ಇಂದು",
    "Type of complaint": "ದೂರಿನ ಪ್ರಕಾರ",
    "Emergency": "ತುರ್ತು",
    "Fire, rescue, gas leak, a fallen live wire or anyone in danger right now.":
      "ಬೆಂಕಿ, ರಕ್ಷಣೆ, ಅನಿಲ ಸೋರಿಕೆ, ಬಿದ್ದ ವಿದ್ಯುತ್ ತಂತಿ ಅಥವಾ ಈಗ ಅಪಾಯದಲ್ಲಿರುವ ಯಾರಾದರೂ.",
    "Not emergency": "ತುರ್ತು ಅಲ್ಲ",
    "Water, drains, garbage, roads and other everyday civic problems.": "ನೀರು, ಚರಂಡಿ, ಕಸ, ರಸ್ತೆ ಮತ್ತು ಇತರ ದೈನಂದಿನ ನಾಗರಿಕ ಸಮಸ್ಯೆಗಳು.",
    "Police complaint": "ಪೊಲೀಸ್ ದೂರು",
    "Cybercrime, fraud, lost property, traffic and public safety. We only register and track it.":
      "ಸೈಬರ್ ಅಪರಾಧ, ವಂಚನೆ, ಕಳೆದುಹೋದ ವಸ್ತು, ಸಂಚಾರ ಮತ್ತು ಸಾರ್ವಜನಿಕ ಸುರಕ್ಷತೆ. ನಾವು ನೋಂದಣಿ ಮತ್ತು ಟ್ರ್ಯಾಕಿಂಗ್ ಮಾತ್ರ ಮಾಡುತ್ತೇವೆ.",
    "If a life is at risk, call 112 first. Then fill in this form so the right officer sees it.":
      "ಜೀವಕ್ಕೆ ಅಪಾಯವಿದ್ದರೆ ಮೊದಲು 112ಗೆ ಕರೆ ಮಾಡಿ. ನಂತರ ಸರಿಯಾದ ಅಧಿಕಾರಿಗೆ ಕಾಣುವಂತೆ ಈ ನಮೂನೆ ಭರ್ತಿ ಮಾಡಿ.",
    "Choose the problem": "ಸಮಸ್ಯೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ",
    "Photos of the problem": "ಸಮಸ್ಯೆಯ ಫೋಟೋಗಳು",
    "Photos and documents": "ಫೋಟೋಗಳು ಮತ್ತು ದಾಖಲೆಗಳು",
    "Upload 3 photos. JPEG, PNG or WebP. Large photos are made smaller on your phone before they are sent.":
      "3 ಫೋಟೋಗಳನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ. JPEG, PNG ಅಥವಾ WebP. ದೊಡ್ಡ ಫೋಟೋಗಳನ್ನು ಕಳುಹಿಸುವ ಮೊದಲು ನಿಮ್ಮ ಫೋನ್‌ನಲ್ಲಿ ಚಿಕ್ಕದಾಗಿಸಲಾಗುತ್ತದೆ.",
    "0 of 3 photos added": "3 ರಲ್ಲಿ 0 ಫೋಟೋ ಸೇರಿಸಲಾಗಿದೆ",
    "Address of the problem": "ಸಮಸ್ಯೆಯ ವಿಳಾಸ",
    "+ Add address": "+ ವಿಳಾಸ ಸೇರಿಸಿ",
    "Add a new address": "ಹೊಸ ವಿಳಾಸ ಸೇರಿಸಿ",
    "Full name": "ಪೂರ್ಣ ಹೆಸರು",
    "House, flat or building": "ಮನೆ, ಫ್ಲ್ಯಾಟ್ ಅಥವಾ ಕಟ್ಟಡ",
    "For example: No. 12, Ground floor": "ಉದಾಹರಣೆ: ಸಂಖ್ಯೆ 12, ನೆಲ ಮಹಡಿ",
    "Street or road": "ರಸ್ತೆ",
    "For example: 4th Main Road": "ಉದಾಹರಣೆ: 4ನೇ ಮುಖ್ಯ ರಸ್ತೆ",
    "Area": "ಪ್ರದೇಶ",
    "For example: Super Market area": "ಉದಾಹರಣೆ: ಸೂಪರ್ ಮಾರ್ಕೆಟ್ ಪ್ರದೇಶ",
    "City": "ನಗರ",
    "Landmark": "ಗುರುತು ಸ್ಥಳ",
    "For example: opposite the bus stop": "ಉದಾಹರಣೆ: ಬಸ್ ನಿಲ್ದಾಣದ ಎದುರು",
    "Cancel": "ರದ್ದುಮಾಡಿ",
    "Use this address": "ಈ ವಿಳಾಸ ಬಳಸಿ",
    "Describe the problem": "ಸಮಸ್ಯೆಯನ್ನು ವಿವರಿಸಿ",
    "For example: no water has come to our street for three days.": "ಉದಾಹರಣೆ: ನಮ್ಮ ರಸ್ತೆಗೆ ಮೂರು ದಿನಗಳಿಂದ ನೀರು ಬಂದಿಲ್ಲ.",
    "of 2000 characters. Say where the problem is and since when.": "/ 2000 ಅಕ್ಷರಗಳು. ಸಮಸ್ಯೆ ಎಲ್ಲಿದೆ ಮತ್ತು ಯಾವಾಗಿನಿಂದ ಎಂದು ತಿಳಿಸಿ.",
    "Use the local model to help sort the complaint, if it is running on this computer":
      "ಈ ಕಂಪ್ಯೂಟರ್‌ನಲ್ಲಿ ಚಾಲನೆಯಲ್ಲಿದ್ದರೆ, ದೂರನ್ನು ವರ್ಗೀಕರಿಸಲು ಸ್ಥಳೀಯ ಮಾದರಿಯನ್ನು ಬಳಸಿ",
    "Your complaint is registered. Complaint ID:": "ನಿಮ್ಮ ದೂರು ನೋಂದಾಯಿಸಲಾಗಿದೆ. ದೂರು ಐಡಿ:",
    "Keep this complaint ID. Use it on Track Complaint to follow your complaint.":
      "ಈ ದೂರು ಐಡಿಯನ್ನು ಇಟ್ಟುಕೊಳ್ಳಿ. ದೂರನ್ನು ಹಿಂಬಾಲಿಸಲು 'ದೂರು ಟ್ರ್ಯಾಕ್ ಮಾಡಿ' ಪುಟದಲ್ಲಿ ಬಳಸಿ.",
    "Message for you": "ನಿಮಗಾಗಿ ಸಂದೇಶ",
    "Track this complaint": "ಈ ದೂರನ್ನು ಟ್ರ್ಯಾಕ್ ಮಾಡಿ",
    "Register another": "ಇನ್ನೊಂದು ನೋಂದಾಯಿಸಿ",
    "Back to home": "ಮುಖಪುಟಕ್ಕೆ ಹಿಂತಿರುಗಿ",
    "From the agents": "ಏಜೆಂಟ್‌ಗಳಿಂದ",
    "Message from the complaint router about this complaint.": "ಈ ದೂರಿನ ಬಗ್ಗೆ ದೂರು ರೂಟರ್‌ನಿಂದ ಸಂದೇಶ.",
    "Time limits for your complaint": "ನಿಮ್ಮ ದೂರಿನ ಕಾಲಮಿತಿಗಳು",
    "What happens next": "ಮುಂದೇನಾಗುತ್ತದೆ",
    "A field worker accepts your complaint. You will see \"Allotted\" and \"Work in progress\".":
      "ಕ್ಷೇತ್ರ ಕಾರ್ಮಿಕರು ನಿಮ್ಮ ದೂರನ್ನು ಸ್ವೀಕರಿಸುತ್ತಾರೆ. ನೀವು \"ನಿಯೋಜಿತ\" ಮತ್ತು \"ಕೆಲಸ ನಡೆಯುತ್ತಿದೆ\" ಎಂದು ನೋಡುತ್ತೀರಿ.",
    "When the work is done, a code comes to your mobile. Give it to the worker only if the problem is fixed.":
      "ಕೆಲಸ ಮುಗಿದಾಗ ನಿಮ್ಮ ಮೊಬೈಲ್‌ಗೆ ಕೋಡ್ ಬರುತ್ತದೆ. ಸಮಸ್ಯೆ ಸರಿಯಾಗಿದ್ದರೆ ಮಾತ್ರ ಅದನ್ನು ಕಾರ್ಮಿಕರಿಗೆ ನೀಡಿ.",
    "If the time limit passes, the officers get a notice and the complaint moves up to the next officer.":
      "ಕಾಲಮಿತಿ ಮೀರಿದರೆ ಅಧಿಕಾರಿಗಳಿಗೆ ಸೂಚನೆ ಹೋಗುತ್ತದೆ ಮತ್ತು ದೂರು ಮುಂದಿನ ಅಧಿಕಾರಿಗೆ ಹೋಗುತ್ತದೆ.",
    "Your complaints": "ನಿಮ್ಮ ದೂರುಗಳು",
    "Loading ...": "ಲೋಡ್ ಆಗುತ್ತಿದೆ ...",
    "Completed": "ಪೂರ್ಣಗೊಂಡಿದೆ",
    "Not completed": "ಪೂರ್ಣಗೊಂಡಿಲ್ಲ",
    "None yet": "ಇನ್ನೂ ಇಲ್ಲ",

    // Heading used on every page: "Every Complaint Followed Up" + "for Every Taluk in" + "Kalaburagi".
    // Kannada puts the place first, so the last piece carries the whole second line.
    "Every Complaint Followed Up": "ಪ್ರತಿ ದೂರಿಗೂ ಅನುಸರಣೆ",
    "for Every Taluk in": "",
    "Kalaburagi": "ಕಲಬುರಗಿಯ ಪ್ರತಿ ತಾಲೂಕಿಗೂ",

    // Photos, documents and form messages
    "Documents or photos (optional)": "ದಾಖಲೆಗಳು ಅಥವಾ ಫೋಟೋಗಳು (ಐಚ್ಛಿಕ)",
    "You may add up to 3 files: JPEG, PNG, WebP or PDF, each under 4 MB. Do not add anything you do not want the police station to see.":
      "ನೀವು 3 ಫೈಲ್‌ಗಳವರೆಗೆ ಸೇರಿಸಬಹುದು: JPEG, PNG, WebP ಅಥವಾ PDF, ಪ್ರತಿಯೊಂದು 4 MB ಒಳಗೆ. ಪೊಲೀಸ್ ಠಾಣೆ ನೋಡಬಾರದು ಎಂದುಕೊಳ್ಳುವುದನ್ನು ಸೇರಿಸಬೇಡಿ.",
    "Add photo": "ಫೋಟೋ ಸೇರಿಸಿ",
    "Add file": "ಫೈಲ್ ಸೇರಿಸಿ",
    "Change": "ಬದಲಾಯಿಸಿ",
    "Your registered address": "ನೀವು ನೋಂದಾಯಿಸಿದ ವಿಳಾಸ",
    "Problem": "ಸಮಸ್ಯೆ",
    "Not given": "ನೀಡಿಲ್ಲ",
    "Write a note first.": "ಮೊದಲು ಟಿಪ್ಪಣಿ ಬರೆಯಿರಿ.",
    "Add 3 photos of the problem.": "ಸಮಸ್ಯೆಯ 3 ಫೋಟೋಗಳನ್ನು ಸೇರಿಸಿ.",

    // Track page
    "Open. Being handled.": "ತೆರೆದಿದೆ. ನಿರ್ವಹಣೆಯಲ್ಲಿದೆ.",
    "Allotted": "ನಿಯೋಜಿತ",
    "Waiting for a worker": "ಕಾರ್ಮಿಕರಿಗಾಗಿ ಕಾಯುತ್ತಿದೆ",
    "Work in progress": "ಕೆಲಸ ನಡೆಯುತ್ತಿದೆ",
    "The worker is on it": "ಕಾರ್ಮಿಕರು ಕೆಲಸ ಮಾಡುತ್ತಿದ್ದಾರೆ",
    "Not yet": "ಇನ್ನೂ ಇಲ್ಲ",
    "Problem fixed": "ಸಮಸ್ಯೆ ಪರಿಹಾರವಾಗಿದೆ",
    "Confirm the fix below": "ಕೆಳಗೆ ಪರಿಹಾರವನ್ನು ದೃಢೀಕರಿಸಿ",
    "Waiting for you": "ನಿಮ್ಮ ಪ್ರತಿಕ್ರಿಯೆಗಾಗಿ ಕಾಯುತ್ತಿದೆ",
    "Department": "ಇಲಾಖೆ",
    "Time limit": "ಕಾಲಮಿತಿ",
    "Zone and ward": "ವಲಯ ಮತ್ತು ವಾರ್ಡ್",
    "Taluk and ward": "ತಾಲೂಕು ಮತ್ತು ವಾರ್ಡ್",
    "Worker": "ಕಾರ್ಮಿಕ",
    "Not allotted yet": "ಇನ್ನೂ ನಿಯೋಜಿಸಿಲ್ಲ",
    "Office in charge": "ಜವಾಬ್ದಾರಿ ಕಚೇರಿ",
    "Officer": "ಅಧಿಕಾರಿ",
    "Registered on": "ನೋಂದಾಯಿಸಿದ ದಿನ",
    "Landmark": "ಗುರುತು ಸ್ಥಳ",
    "None": "ಇಲ್ಲ",
    "Not recorded": "ದಾಖಲಿಸಿಲ್ಲ",
    "Not running": "ನಡೆಯುತ್ತಿಲ್ಲ",
    "Track \u2192": "ಟ್ರ್ಯಾಕ್ \u2192",
    "Close the complaint": "ದೂರನ್ನು ಮುಚ್ಚಿ",
    "Yes, it is fixed": "ಹೌದು, ಪರಿಹಾರವಾಗಿದೆ",
    "No, still not fixed": "ಇಲ್ಲ, ಇನ್ನೂ ಪರಿಹಾರವಾಗಿಲ್ಲ",
    "An officer has marked this complaint resolved. Is the problem really fixed?": "ಅಧಿಕಾರಿ ಈ ದೂರನ್ನು ಪರಿಹಾರವಾಗಿದೆ ಎಂದು ಗುರುತಿಸಿದ್ದಾರೆ. ಸಮಸ್ಯೆ ನಿಜವಾಗಿಯೂ ಪರಿಹಾರವಾಗಿದೆಯೇ?",
    "Comment (optional)": "ಟಿಪ್ಪಣಿ (ಐಚ್ಛಿಕ)",
    "Comment": "ಟಿಪ್ಪಣಿ",
    "No messages yet.": "ಇನ್ನೂ ಸಂದೇಶಗಳಿಲ್ಲ.",
    "Code for the worker:": "ಕಾರ್ಮಿಕರಿಗೆ ಕೋಡ್:",

    // Complaint types
    "Emergency Rescue": "ತುರ್ತು ರಕ್ಷಣೆ",
    "Fire and smoke emergencies": "ಬೆಂಕಿ ಮತ್ತು ಹೊಗೆ ತುರ್ತು ಪರಿಸ್ಥಿತಿ",
    "Ambulance and medical emergencies": "ಆಂಬ್ಯುಲೆನ್ಸ್ ಮತ್ತು ವೈದ್ಯಕೀಯ ತುರ್ತು",
    "LPG gas leakage": "ಎಲ್‌ಪಿಜಿ ಅನಿಲ ಸೋರಿಕೆ",
    "Hazardous gas or chemical leakage": "ಅಪಾಯಕಾರಿ ಅನಿಲ ಅಥವಾ ರಾಸಾಯನಿಕ ಸೋರಿಕೆ",
    "Flood rescue and evacuation": "ಪ್ರವಾಹ ರಕ್ಷಣೆ ಮತ್ತು ಸ್ಥಳಾಂತರ",
    "Building collapse and trapped persons": "ಕಟ್ಟಡ ಕುಸಿತ ಮತ್ತು ಸಿಕ್ಕಿಬಿದ್ದವರು",
    "Electrical hazards and fallen live wires": "ವಿದ್ಯುತ್ ಅಪಾಯ ಮತ್ತು ಬಿದ್ದ ವಿದ್ಯುತ್ ತಂತಿಗಳು",
    "Road accidents requiring rescue": "ರಕ್ಷಣೆ ಬೇಕಾದ ರಸ್ತೆ ಅಪಘಾತ",
    "People trapped in lifts or confined spaces": "ಲಿಫ್ಟ್ ಅಥವಾ ಮುಚ್ಚಿದ ಜಾಗದಲ್ಲಿ ಸಿಕ್ಕಿಬಿದ್ದವರು",
    "Tree falls blocking access or threatening lives": "ದಾರಿ ತಡೆಯುವ ಅಥವಾ ಜೀವಕ್ಕೆ ಅಪಾಯವಾಗುವ ಮರ ಬೀಳುವಿಕೆ",
    "Drowning and water rescue": "ಮುಳುಗುವಿಕೆ ಮತ್ತು ನೀರಿನ ರಕ್ಷಣೆ",
    "Landslides and structural hazards": "ಭೂಕುಸಿತ ಮತ್ತು ರಚನಾತ್ಮಕ ಅಪಾಯ",
    "Water Supply": "ನೀರು ಪೂರೈಕೆ",
    "Drainage and Sewerage": "ಚರಂಡಿ ಮತ್ತು ಒಳಚರಂಡಿ",
    "Garbage and Sanitation": "ಕಸ ಮತ್ತು ನೈರ್ಮಲ್ಯ",
    "Roads and Footpaths": "ರಸ್ತೆ ಮತ್ತು ಪಾದಚಾರಿ ಮಾರ್ಗಗಳು",
    "Flooding and Waterlogging": "ಪ್ರವಾಹ ಮತ್ತು ನೀರು ನಿಲ್ಲುವಿಕೆ",
    "Public Health and Stray Animals": "ಸಾರ್ವಜನಿಕ ಆರೋಗ್ಯ ಮತ್ತು ಬೀದಿ ಪ್ರಾಣಿಗಳು",
    "Parks and Public Infrastructure": "ಉದ್ಯಾನ ಮತ್ತು ಸಾರ್ವಜನಿಕ ಮೂಲಸೌಕರ್ಯ",
    "Municipal Services and Taxes": "ನಗರ ಸೇವೆಗಳು ಮತ್ತು ತೆರಿಗೆಗಳು",
    "Other Complaints": "ಇತರ ದೂರುಗಳು",
    "Cybercrime and online fraud": "ಸೈಬರ್ ಅಪರಾಧ ಮತ್ತು ಆನ್‌ಲೈನ್ ವಂಚನೆ",
    "Financial fraud": "ಹಣಕಾಸು ವಂಚನೆ",
    "Lost property": "ಕಳೆದುಹೋದ ವಸ್ತು",
    "Public safety and traffic": "ಸಾರ್ವಜನಿಕ ಸುರಕ್ಷತೆ ಮತ್ತು ಸಂಚಾರ",
    "Complaint involving individuals": "ವ್ಯಕ್ತಿಗಳಿಗೆ ಸಂಬಂಧಿಸಿದ ದೂರು",
    "This system only registers and tracks your complaint. Whether an offence took place, and whether an FIR is registered, is decided only by authorised police officials.":
      "ಈ ವ್ಯವಸ್ಥೆ ನಿಮ್ಮ ದೂರನ್ನು ನೋಂದಾಯಿಸಿ ಟ್ರ್ಯಾಕ್ ಮಾತ್ರ ಮಾಡುತ್ತದೆ. ಅಪರಾಧ ನಡೆದಿದೆಯೇ ಮತ್ತು ಎಫ್‌ಐಆರ್ ದಾಖಲಿಸಬೇಕೇ ಎಂಬುದನ್ನು ಅಧಿಕೃತ ಪೊಲೀಸ್ ಅಧಿಕಾರಿಗಳು ಮಾತ್ರ ನಿರ್ಧರಿಸುತ್ತಾರೆ.",

    // Done screen and status
    "Type": "ಪ್ರಕಾರ",
    "Department": "ಇಲಾಖೆ",
    "Follow-up due": "ಅನುಸರಣೆ ಗಡುವು",
    "Language": "ಭಾಷೆ",
    "Allotted · Work in progress": "ನಿಯೋಜಿತ · ಕೆಲಸ ನಡೆಯುತ್ತಿದೆ",
    "Rejected · In progress": "ತಿರಸ್ಕೃತ · ಪ್ರಗತಿಯಲ್ಲಿದೆ",
    "Done": "ಮುಗಿದಿದೆ",
    "Now": "ಈಗ",
    "Not needed": "ಅಗತ್ಯವಿಲ್ಲ",

    // Track
    "Track Your": "ನಿಮ್ಮ ದೂರನ್ನು",
    "Complaint": "ಟ್ರ್ಯಾಕ್ ಮಾಡಿ",
    "Enter your complaint ID to see where it is, who is working on it, and its time limit.":
      "ದೂರು ಎಲ್ಲಿದೆ, ಯಾರು ಕೆಲಸ ಮಾಡುತ್ತಿದ್ದಾರೆ ಮತ್ತು ಕಾಲಮಿತಿ ಏನು ಎಂದು ನೋಡಲು ನಿಮ್ಮ ದೂರು ಐಡಿ ನಮೂದಿಸಿ.",
    "Enter your complaint ID, for example CMP-20261018-1234": "ನಿಮ್ಮ ದೂರು ಐಡಿ ನಮೂದಿಸಿ, ಉದಾಹರಣೆ CMP-20261018-1234",
    "Complaint ID": "ದೂರು ಐಡಿ",
    "Track": "ಟ್ರ್ಯಾಕ್",
    "Search above, or choose one of your complaints below.": "ಮೇಲೆ ಹುಡುಕಿ, ಅಥವಾ ಕೆಳಗಿನ ನಿಮ್ಮ ದೂರುಗಳಲ್ಲಿ ಒಂದನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
    "Your complaints:": "ನಿಮ್ಮ ದೂರುಗಳು:",
    "Progress": "ಪ್ರಗತಿ",
    "Details": "ವಿವರಗಳು",
    "Your complaint": "ನಿಮ್ಮ ದೂರು",
    "Time limits from the router": "ರೂಟರ್‌ನ ಕಾಲಮಿತಿಗಳು",
    "Message from the complaint router": "ದೂರು ರೂಟರ್‌ನಿಂದ ಸಂದೇಶ",
    "History": "ಇತಿಹಾಸ",
    "Messages to you": "ನಿಮಗೆ ಬಂದ ಸಂದೇಶಗಳು",
    "Documents": "ದಾಖಲೆಗಳು",
  };

  // Text with numbers or names in it: [pattern, function that builds the Kannada].
  const PATTERNS = [
    [/^(\d+) of (\d+) photos added$/, (m) => `${m[2]} ರಲ್ಲಿ ${m[1]} ಫೋಟೋ ಸೇರಿಸಲಾಗಿದೆ`],
    [/^(\d+) of (\d+) files added$/, (m) => `${m[2]} ರಲ್ಲಿ ${m[1]} ಫೈಲ್ ಸೇರಿಸಲಾಗಿದೆ`],
    [/^Time limit: (.+)$/, (m) => `ಕಾಲಮಿತಿ: ${m[1]}`],
    [/^Counting down to (.+)$/, (m) => `ಕೊನೆಯ ಸಮಯ: ${m[1]}`],
    [/^Hello, (.+)$/, (m) => `ನಮಸ್ಕಾರ, ${m[1]}`],
    [/^Welcome, (.+)$/, (m) => `ಸ್ವಾಗತ, ${m[1]}`],
    [/^Today: (.+)$/, (m) => `ಇಂದು: ${m[1]}`],
    [/^Photo (\d+)$/, (m) => `ಫೋಟೋ ${m[1]}`],
    [/^(\d+) of (\d+) files added \(optional\)$/, (m) => `${m[2]} ರಲ್ಲಿ ${m[1]} ಫೈಲ್ ಸೇರಿಸಲಾಗಿದೆ (ಐಚ್ಛಿಕ)`],
    [/^(.+) \((.+)\)$/, (m) => {
      const a = KN[m[1]], b = KN[m[2]];   // "Complaint type (Department)" in the lists of complaints
      return a && b ? `${a} (${b})` : null;
    }],
    [/^(.+) - Kalaburagi Grievance Tracker$/, (m) => `${translate(m[1])} - ಕಲಬುರಗಿ ಕುಂದುಕೊರತೆ ಟ್ರ್ಯಾಕರ್`],
  ];

  let lang = "en";
  const originals = new WeakMap();   // text node -> the English it had
  const written = new WeakMap();     // text node -> the Kannada this script wrote
  const attrOriginals = new WeakMap();   // element -> { attribute: English }
  const ATTRS = ["placeholder", "title", "aria-label"];
  const SKIP = new Set(["SCRIPT", "STYLE", "TEXTAREA", "OPTION_VALUE"]);

  function translate(text) {
    const key = text.trim();
    if (!key) return text;
    let out = KN[key];
    if (out === undefined) {
      for (const [pattern, build] of PATTERNS) {
        const m = key.match(pattern);
        if (m) { out = build(m); if (out) break; out = undefined; }
      }
    }
    if (out === undefined) return text;
    const lead = text.match(/^\s*/)[0];
    const trail = text.match(/\s*$/)[0];
    return lead + out + trail;
  }

  function skipped(node) {
    for (let p = node.parentNode; p; p = p.parentNode) {
      if (p.nodeType === 1 && (SKIP.has(p.tagName) || p.hasAttribute("data-no-i18n"))) return true;
    }
    return false;
  }

  function doText(node) {
    if (skipped(node)) return;
    if (lang === "kn") {
      if (written.get(node) === node.nodeValue) return;   // our own change
      const english = node.nodeValue;
      const kn = translate(english);
      if (kn !== english) {
        originals.set(node, english);
        written.set(node, kn);
        node.nodeValue = kn;
      }
    } else if (originals.has(node) && written.get(node) === node.nodeValue) {
      node.nodeValue = originals.get(node);
      originals.delete(node);
      written.delete(node);
    }
  }

  function doAttrs(element) {
    if (!element.getAttribute) return;
    for (const name of ATTRS) {
      const value = element.getAttribute(name);
      if (value === null) continue;
      let saved = attrOriginals.get(element);
      if (lang === "kn") {
        if (saved && saved[name] && saved[name].kn === value) continue;
        const kn = translate(value);
        if (kn !== value) {
          saved = saved || {};
          saved[name] = { en: value, kn: kn };
          attrOriginals.set(element, saved);
          element.setAttribute(name, kn);
        }
      } else if (saved && saved[name] && saved[name].kn === value) {
        element.setAttribute(name, saved[name].en);
        delete saved[name];
      }
    }
  }

  function walk(root) {
    if (root.nodeType === 3) { doText(root); return; }
    if (root.nodeType !== 1 || SKIP.has(root.tagName)) return;
    doAttrs(root);
    for (const child of root.childNodes) walk(child);
  }

  function doTitle() {
    const title = document.querySelector("title");
    if (!title || !title.firstChild) return;
    doText(title.firstChild);
  }

  const observer = new MutationObserver((records) => {
    for (const record of records) {
      if (record.type === "characterData") doText(record.target);
      else if (record.type === "attributes") doAttrs(record.target);
      else record.addedNodes.forEach(walk);
    }
  });

  function apply(next) {
    lang = next === "kn" ? "kn" : "en";
    document.documentElement.lang = lang;
    walk(document.body);
    doTitle();
    const select = document.getElementById("lang");
    if (select && select.value !== lang) select.value = lang;
    try { localStorage.setItem(KEY, lang); } catch (err) { /* not saved; English next time */ }
    window.dispatchEvent(new CustomEvent("portal-lang", { detail: lang }));
  }

  // Pages other than the first screen have no language box; add one next to the account menu.
  function ensureSelect() {
    if (document.getElementById("lang")) return;
    const holder = document.querySelector(".top-right") || document.querySelector(".topbar .container");
    if (!holder) return;
    const label = document.createElement("label");
    label.className = "lang";
    label.setAttribute("data-no-i18n", "");
    label.innerHTML = '<svg class="icon" aria-hidden="true"><use href="/assets/icons.svg#globe"/></svg>' +
      '<select id="lang" aria-label="Language"><option value="en">English</option><option value="kn">ಕನ್ನಡ</option></select>';
    holder.insertBefore(label, holder.firstChild);
  }

  // Office and complaint-type names come from the district's charter, with their Kannada.
  function loadNames() {
    if (!window.fetch) return;
    fetch("/api/config", { credentials: "same-origin" })
      .then((response) => (response.ok ? response.json() : null))
      .then((config) => {
        if (!config || !config.kannada_names) return;
        for (const key of Object.keys(config.kannada_names)) if (!(key in KN)) KN[key] = config.kannada_names[key];
        if (lang === "kn") walk(document.body);
      })
      .catch(() => { /* the pages still work in English */ });
  }

  function start() {
    ensureSelect();
    loadNames();
    const select = document.getElementById("lang");
    if (select) select.addEventListener("change", (event) => apply(event.target.value));
    let saved = "en";
    try { saved = localStorage.getItem(KEY) || "en"; } catch (err) { saved = "en"; }
    if (new URLSearchParams(window.location.search).get("lang") === "kn") saved = "kn";
    apply(saved);
    observer.observe(document.documentElement, {
      childList: true, subtree: true, characterData: true,
      attributes: true, attributeFilter: ATTRS,
    });
  }

  window.PortalI18n = {
    get lang() { return lang; },
    set: apply,
    t: (text) => (lang === "kn" ? translate(text) : text),
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
