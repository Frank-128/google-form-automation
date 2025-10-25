# Google Form Auto-Filler (Selenium) — README

Short script to auto-fill a Google Form, capture a confirmation screenshot, and email the result. Uses Faker for realistic values and webdriver-manager to manage ChromeDriver.

## Features
- Auto-detects form questions and fills sensible fake answers
- Handles text, email, phone, date, textarea, radio, dropdowns
- Attempts to extract short captcha-like codes shown in the form
- Saves a confirmation screenshot (confirmation.png)
- Sends an email with the screenshot and optional attachments

## Requirements
- Python 3.8+
- Google Chrome installed
- pip packages:
    - selenium
    - webdriver-manager
    - faker

Install dependencies:
```bash
pip install selenium webdriver-manager faker
```

## Configuration
Edit the top of the script to set:
- FORM_URL — URL of the Google Form
- SCREENSHOT, RESPONSES_FILE — output filenames
- SENDER_EMAIL, APP_PASSWORD — sender Gmail and app-specific password (do not use your main password; create a Gmail App Password)
- RECEIVERS, CC, YOUR_NAME — email recipients and sender name

Tip: for security, prefer reading the password from an environment variable instead of hardcoding.

You can create a `responses.json` in the same folder with exact question labels mapped to values to override auto-generated answers:
```json
{
    "Full name": "Frank Ndagula",
    "Email address": "frank@example.com"
}
```

## Usage

create a .env file with the entries
```js
FORM_URL = "https://forms.gle/WT68aV5UnPajeoSc8"
SENDER_EMAIL = <sender_email>
APP_PASSWORD = <google_app_password>
RECEIVERS = <receiver1>,<receiver2> // comma separated
CC = <cc_email1>,<cc_email2> // cc emails comma separated
YOUR_NAME = <your_name> 
```


Run the script:
```bash
python your_script.py
```
The script will:
1. Launch Chrome and fill the form
2. Submit and save a screenshot as `confirmation.png`
3. Send an email with the screenshot attached

## Notes & Troubleshooting
- If running headless, uncomment the `--headless` option in ChromeOptions.
- If fields are not found, increase WebDriverWait timeouts.
- If the submit button text differs (localized), adjust the XPath used to locate it.
- Respect Google Forms' terms of service and avoid spamming forms.

## License
Use at your own risk. This repository contains example automation for learning and testing purposes only.