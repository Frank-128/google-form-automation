# 🧠 Google Form Auto-Filler (Selenium + Flask)

A Python automation tool with a simple Flask web interface that automatically fills out Google Forms using realistic fake data, captures a confirmation screenshot, and emails the result.

This project combines **Selenium**, **Faker**, and **Flask** to demonstrate browser automation, data generation, and email sending — all in one clean web interface.

---

## 🚀 Features

- 🧾 Automatically fills Google Form fields (text, email, phone, date, textarea, radio, dropdowns)
- 🧠 Generates realistic fake answers using [Faker](https://faker.readthedocs.io/)
- 📸 Captures a confirmation screenshot (`confirmation.png`)
- 📧 Sends an email with the screenshot attached
- 🖥️ Simple Flask-based web interface
- 🔐 Uses `.env` configuration for secure credentials

---

## 🧰 Requirements

- **Python 3.8+**
- **Google Chrome** installed
- Install required packages:

```bash
  pip install selenium webdriver-manager faker flask python-dotenv
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
GITHUB_LINK = <Github_link>
PORTFOLIO_LINK = <Portfolio_link> 
```


Run the app:
```bash
python app.py
```
The app will:

1. Open at port 5000.

2. Click on the send email link which will run an automation script which will: 


    i. Launch Chrome and fill the form.

    ii. Submit and save a screenshot as `confirmation.png`
    
    iii. Send an email with the screenshot attached

## Notes & Troubleshooting
- If running headless, uncomment the `--headless` option in ChromeOptions.
- If fields are not found, increase WebDriverWait timeouts.
- If the submit button text differs (localized), adjust the XPath used to locate it.
- Respect Google Forms' terms of service and avoid spamming forms.

## License
Use at your own risk. This repository contains example automation for learning and testing purposes only.