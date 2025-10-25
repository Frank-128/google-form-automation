import os
import json
import time
import re
import smtplib
import random
from datetime import datetime, timedelta
from email.message import EmailMessage
from faker import Faker
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

load_dotenv()

# ---------------------
# CONFIGURATION
# ---------------------
FORM_URL = "https://forms.gle/WT68aV5UnPajeoSc8"
SCREENSHOT = "confirmation.png"
RESPONSES_FILE = "responses.json"


SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
RECEIVERS = os.getenv("RECEIVERS", "").split(",")
CC = os.getenv("CC", "").split(",")
YOUR_NAME = os.getenv("YOUR_NAME", "Unknown User")


# ---------------------
# FAKER INITIALIZATION
# ---------------------
fake = Faker()

# ---------------------
# UTILS FOR SPECIFIC FIELDS
# ---------------------
def gen_pin_code():
    """Return a numeric postal code (5 or 6 digits)."""
    length = random.choice([5, 6])
    return "".join(str(random.randint(0, 9)) for _ in range(length))

def gen_dob(min_age=20, max_age=45, out_format="DDMMYYYY"):
    """Generate a DOB string. default returns DD/MM/YYYY; for input type=date return YYYY-MM-DD."""
    today = datetime.today()
    age = random.randint(min_age, max_age)
    birth = today - timedelta(days=age * 365 + random.randint(0, 365))
    return birth

COMMON_GENDERS = ["male", "female", "other", "prefer not to say", "non-binary", "transgender"]

def find_code_in_question(q):
    """Search all text nodes under the question for an uppercase alphanumeric token of length 4-8 (captcha-like)."""
    try:
        elems = q.find_elements(By.XPATH, './/*')
        for e in elems:
            text = (e.text or "").strip()
            # look for tokens like GNFPYC (4-8 uppercase alnum) or numeric codes
            for token in re.findall(r'\b[A-Z0-9]{4,8}\b', text):
                # ensure token has at least one letter or is numeric token of length >=4
                if re.match(r'^[A-Z0-9]{4,8}$', token):
                    return token
    except Exception:
        pass
    return None

# ---------------------
# SMART ANSWER GENERATOR
# ---------------------
def fake_answer(label):
    """Return a realistic fake answer based on field hint."""
    label_lower = label.lower()
    if "name" in label_lower:
        return fake.name()
    if "email" in label_lower:
        return fake.email()
    if "phone" in label_lower or "mobile" in label_lower or "contact" in label_lower or "number" in label_lower:
        return fake.phone_number()
    if "city" in label_lower or "location" in label_lower:
        return fake.city()
    if "address" in label_lower or "full address" in label_lower:
        return fake.address().replace("\n", " ")
    if "company" in label_lower or "organization" in label_lower:
        return fake.company()
    if "age" in label_lower or "years" in label_lower:
        return str(random.randint(20, 45))
    if "country" in label_lower:
        return fake.country()
    if "pin" in label_lower or "postal" in label_lower or "zip" in label_lower or "pincode" in label_lower:
        return gen_pin_code()
    if "date of birth" in label_lower or "dob" in label_lower or "date of birth" in label_lower:
        # Return an object / marker; actual formatting handled during input depending on input type.
        return gen_dob()
    if "gender" in label_lower:
        # Return a sensible string, but we will prefer selecting a radio/option matching this.
        return random.choice(["Male", "Female", "Other"])
    if "type this code" in label_lower or "type the code" in label_lower or "enter code" in label_lower or "captcha" in label_lower:
        # We'll attempt to extract the shown code from the form when filling.
        return None  # special handling; don't type a made-up word
    if "why" in label_lower or "describe" in label_lower or "tell" in label_lower:
        return fake.sentence(nb_words=12)
    # fallback to a reasonably long word/phrase
    return fake.sentence(nb_words=3)

# ---------------------
# HELPER FUNCTIONS
# ---------------------
def load_responses():
    try:
        with open(RESPONSES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# ---------------------
# FORM FILL FUNCTION
# ---------------------
def fill_form_and_capture():
    print("🚀 Launching Chrome browser...")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(FORM_URL)

    # Wait until the form loads (list items = questions)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//div[@role="listitem"]'))
    )

    responses = load_responses()
    questions = driver.find_elements(By.XPATH, '//div[@role="listitem"]')
    print(f"🧩 Found {len(questions)} questions in the form...")

    for q in questions:
        try:
            # Some questions have heading role, others can be structured differently.
            try:
                label_elem = q.find_element(By.XPATH, './/div[@role="heading"]')
                label = label_elem.text.strip()
            except Exception:
                # fallback to first visible text inside question
                label = (q.text.splitlines()[0] if q.text else "").strip()

            if not label:
                continue

            # allow overriding from responses.json if exact match exists
            preset = responses.get(label)
            answer = preset if preset is not None else fake_answer(label)
            print(f"✍️ Filling '{label}' → '{answer}'")

            # Special handling: CAPTCHA / Type this code
            if (label.lower().startswith("type this code") or
                "type this code" in label.lower() or
                "enter code" in label.lower() or
                "type the code" in label.lower() or
                "captcha" in label.lower()):
                code = find_code_in_question(q)
                if code:
                    # try find a text input inside the same question
                    inputs = q.find_elements(By.XPATH, './/input[@type="text" or @type="email"]')
                    if inputs:
                        inputs[0].clear()
                        inputs[0].send_keys(code)
                        print(f"   ↳ Captcha-like code found and entered: {code}")
                        continue
                # no code extraction -> fallback to available options / random text
                if answer is None:
                    answer = fake.word()

            # If question has an input element(s)
            inputs = q.find_elements(By.XPATH, './/input')
            if inputs:
                # Prefer typing into text/email inputs
                text_inputs = [i for i in inputs if (i.get_attribute('type') in ('text', 'email', 'tel', 'search') or i.get_attribute('type')==None)]
                date_inputs = [i for i in inputs if i.get_attribute('type') == 'date']
                if date_inputs:
                    # format DOB to YYYY-MM-DD for date input
                    if isinstance(answer, datetime):
                        date_str = answer.strftime("%Y-%m-%d")
                    else:
                        # try to parse if string; fallback to today - 25 years
                        try:
                            parsed = datetime.strptime(str(answer), "%d/%m/%Y")
                            date_str = parsed.strftime("%Y-%m-%d")
                        except Exception:
                            date_str = gen_dob().strftime("%Y-%m-%d")
                    date_inputs[0].send_keys(date_str)
                    print(f"   ↳ Sent date value: {date_str}")
                    continue
                if text_inputs:
                    # choose the first text-like input
                    target = text_inputs[0]
                    # If answer is a datetime object -> format to dd/mm/YYYY by default
                    if isinstance(answer, datetime):
                        formatted = answer.strftime("%d/%m/%Y")
                        # also try iso format if needed; send dd/mm/yyyy first
                        target.clear()
                        target.send_keys(formatted)
                        print(f"   ↳ Sent formatted datetime: {formatted}")
                    else:
                        # ensure pin only digits if label suggests pin
                        if "pin" in label.lower() or "postal" in label.lower() or "zip" in label.lower():
                            answer_str = re.sub(r'\D', '', str(answer))
                        else:
                            answer_str = str(answer)
                        target.clear()
                        target.send_keys(answer_str)
                    continue

            # Textarea handling
            textareas = q.find_elements(By.XPATH, './/textarea')
            if textareas:
                val = ""
                if isinstance(answer, datetime):
                    val = answer.strftime("%d/%m/%Y")
                else:
                    val = str(answer)
                textareas[0].clear()
                textareas[0].send_keys(val)
                continue

            # Radio buttons - try to select option matching answer text
            radios = q.find_elements(By.XPATH, './/div[@role="radio"]')
            if radios:
                chosen = None
                # Try to match option text with answer
                if answer:
                    ans_low = str(answer).strip().lower()
                    for r in radios:
                        try:
                            # option text may be sibling; search within ancestor
                            txt = r.text.strip().lower()
                            if txt and ans_low in txt:
                                chosen = r
                                break
                        except Exception:
                            continue
                if not chosen:
                    # pick the first radio that looks like gender option if label contains gender
                    if "gender" in label.lower():
                        for r in radios:
                            t = (r.text or "").strip().lower()
                            if any(g in t for g in ["male", "female", "other", "non-binary", "prefer not"]):
                                chosen = r
                                break
                if not chosen:
                    chosen = random.choice(radios)
                try:
                    chosen.click()
                    continue
                except Exception:
                    pass

            # Dropdowns / listbox
            dropdowns = q.find_elements(By.XPATH, './/div[@role="listbox"]')
            if dropdowns:
                dropdowns[0].click()
                time.sleep(0.4)
                options = driver.find_elements(By.XPATH, '//div[@role="option"]')
                matched = None
                if answer:
                    ans_low = str(answer).strip().lower()
                    for opt in options:
                        try:
                            if ans_low in (opt.text or "").strip().lower():
                                matched = opt
                                break
                        except Exception:
                            continue
                if not matched and "gender" in label.lower():
                    for opt in options:
                        t = (opt.text or "").strip().lower()
                        if any(g in t for g in ["male", "female", "other", "non-binary", "prefer not"]):
                            matched = opt
                            break
                if not matched:
                    matched = random.choice(options) if options else None
                if matched:
                    try:
                        matched.click()
                        continue
                    except Exception:
                        pass

            # fallback: if nothing matched, try clicking first clickable option inside q
            clickable = q.find_elements(By.XPATH, './/div[@role="button" or @role="option"]')
            if clickable:
                try:
                    clickable[0].click()
                    continue
                except Exception:
                    pass

        except Exception as e:
            print(f"⚠️ Error filling question '{label}': {e}")
            try:
                driver.save_screenshot(f"error_{int(time.time())}.png")
            except Exception:
                pass
            continue

    # Submit the form
    try:
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//span[text()="Submit" or text()="Send"]/ancestor::div[@role="button"]'))
        )
        submit_button.click()
        print("📤 Submitting form...")
    except Exception as e:
        print(f"⚠️ Submit button not found or clickable: {e}")

    # Wait for confirmation and screenshot
    time.sleep(4)
    driver.save_screenshot(SCREENSHOT)
    print(f"📸 Screenshot saved as {SCREENSHOT}")

    driver.quit()

# ---------------------
# EMAIL FUNCTION
# ---------------------
def send_email():
    msg = EmailMessage()
    msg['Subject'] = f"Python (Selenium) Assignment - {YOUR_NAME}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = ", ".join(RECEIVERS)
    msg['Cc'] = ", ".join(CC)

    msg.set_content(f"""\
Dear Team,

Please find attached my Python (Selenium) assignment submission.

Included:
1. Screenshot of Google Form submission
2. Source code (GitHub link) : https://github.com/Frank-128/google-form-automation
3. Documentation
4. Resume
5. Work samples : https://rico-portfolio.vercel.app/
6. Availability: Full-time (2100 hrs to 0300 hrs Indian time(i.e +UTC 5:30) for 6 months)

Best regards,
{YOUR_NAME}
""")

    # Attach screenshot
    try:
        with open(SCREENSHOT, "rb") as f:
            msg.add_attachment(f.read(), maintype='image', subtype='png', filename=SCREENSHOT)
    except FileNotFoundError:
        print(f"⚠️ {SCREENSHOT} not found; skipping screenshot attachment.")

    # Attach resume (optional)
    try:
        with open("resume.pdf", "rb") as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename="resume.pdf")
    except FileNotFoundError:
        print("⚠️ Warning: 'resume.pdf' not found, skipping attachment.")

    # Send email securely
    try:
        print("📧 Sending email...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
        print("✅ Assignment email sent successfully!")
    except Exception as e:
        print(f"⚠️ Failed to send email: {e}")

# ---------------------
# MAIN EXECUTION
# ---------------------
if __name__ == "__main__":
    print("🚀 Starting automation...")
    fill_form_and_capture()
    send_email()
