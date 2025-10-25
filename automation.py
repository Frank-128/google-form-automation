import json, time, smtplib, random, os, re
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

# Load .env
load_dotenv()

# ---------------------
# CONFIGURATION
# ---------------------
FORM_URL = os.getenv("FORM_URL")
SCREENSHOT = "confirmation.png"
RESPONSES_FILE = "responses.json"

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
RECEIVERS = os.getenv("RECEIVERS", "").split(",")
CC = os.getenv("CC", "").split(",")
YOUR_NAME = os.getenv("YOUR_NAME", "Unknown User")
GITHUB_LINK = os.getenv("GITHUB_LINK", "https://github.com/yourusername/your-repo")
PORTFOLIO_LINK = os.getenv("PORTFOLIO_LINK", "https://yourportfolio.com")

fake = Faker()

# ---------------------
# HELPER FUNCTIONS
# ---------------------
def gen_dob(min_age=20, max_age=45):
    """Generate a date of birth."""
    today = datetime.today()
    age = random.randint(min_age, max_age)
    birth = today - timedelta(days=age * 365 + random.randint(0, 365))
    return birth

def find_code_in_question(q):
    """Search for captcha-like code in question text."""
    try:
        text = q.text or ""
        # Look for uppercase alphanumeric tokens (4-8 chars)
        for token in re.findall(r'\b[A-Z0-9]{4,8}\b', text):
            if re.match(r'^[A-Z0-9]{4,8}$', token):
                return token
    except Exception:
        pass
    return None

# ---------------------
# FAKER LOGIC
# ---------------------
def fake_answer(label):
    """Generate realistic fake answers based on field label."""
    label_lower = label.lower()

    if "name" in label_lower and "file" not in label_lower:
        return fake.name()
    elif "email" in label_lower:
        return fake.email()
    elif "phone" in label_lower or "mobile" in label_lower or "contact" in label_lower or "number" in label_lower:
        return fake.numerify("##########")
    elif "address" in label_lower and "email" not in label_lower:
        return fake.address().replace("\n", ", ")
    elif "city" in label_lower or "location" in label_lower:
        return fake.city()
    elif "company" in label_lower or "organization" in label_lower:
        return fake.company()
    elif "country" in label_lower:
        return fake.country()
    elif "pin" in label_lower or "postal" in label_lower or "zip" in label_lower or "pincode" in label_lower:
        return fake.postcode()
    elif "date of birth" in label_lower or "dob" in label_lower or "birth date" in label_lower:
        return gen_dob()
    elif "age" in label_lower or "years old" in label_lower:
        return str(random.randint(20, 45))
    elif "gender" in label_lower:
        return random.choice(["Male", "Female", "Other"])
    elif ("code" in label_lower and "type" in label_lower) or "captcha" in label_lower:
        return None  # Special handling
    elif "why" in label_lower or "describe" in label_lower or "tell" in label_lower or "explain" in label_lower:
        return fake.sentence(nb_words=12)
    else:
        return fake.word()

def load_responses():
    """Load pre-defined responses from JSON file."""
    try:
        with open(RESPONSES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# ---------------------
# FORM FILL FUNCTION
# ---------------------
def fill_form_and_capture():
    """Fill Google Form using Selenium and capture screenshot."""
    print("🚀 Launching Chrome browser...")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        driver.get(FORM_URL)
        print(f"📄 Navigating to form: {FORM_URL}")
        
        # Wait for form to load with multiple fallback strategies
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
        
        # Try to find questions using multiple selectors
        questions = []
        selectors = [
            '//div[contains(@class,"Qr7Oae")]',  # Original selector
            '//div[@role="listitem"]',
            '//div[contains(@class,"freebirdFormviewerViewItemsItemItem")]'
        ]
        
        for selector in selectors:
            try:
                questions = driver.find_elements(By.XPATH, selector)
                if questions:
                    print(f"✅ Found {len(questions)} questions using selector")
                    break
            except Exception:
                continue
        
        if not questions:
            print("❌ No questions found!")
            driver.save_screenshot("error_no_questions.png")
            return
        
        responses = load_responses()
        
        for idx, q in enumerate(questions, 1):
            try:
                # Extract label with multiple strategies
                label = ""
                label_selectors = [
                    './/div[contains(@class,"Y2Zypf")]',
                    './/div[@role="heading"]',
                    './/span[contains(@class, "M7eMe")]',
                    './/label'
                ]
                
                for ls in label_selectors:
                    try:
                        label_elem = q.find_element(By.XPATH, ls)
                        label = label_elem.text.strip()
                        if label:
                            break
                    except Exception:
                        continue
                
                # Fallback: get first line of question text
                if not label and q.text:
                    lines = [line.strip() for line in q.text.splitlines() if line.strip()]
                    label = lines[0] if lines else ""
                
                if not label:
                    print(f"⚠️ Q{idx}: No label found, skipping...")
                    continue
                
                # Get answer (preset or generated)
                preset = responses.get(label)
                answer = preset if preset is not None else fake_answer(label)
                
                # Special handling for captcha
                if answer is None and ("code" in label.lower() or "captcha" in label.lower()):
                    code = find_code_in_question(q)
                    if code:
                        answer = code
                        print(f"✍️ Q{idx}: '{label[:40]}...' → [CAPTCHA: {code}]")
                    else:
                        answer = fake.word()
                        print(f"✍️ Q{idx}: '{label[:40]}...' → [CAPTCHA NOT FOUND]")
                else:
                    print(f"✍️ Q{idx}: '{label[:40]}...' → '{str(answer)[:40]}...'")
                
                # === TEXT INPUTS ===
                inputs = q.find_elements(By.XPATH, './/input')
                if inputs:
                    text_inputs = [i for i in inputs if i.get_attribute('type') in ('text', 'email', 'tel', 'search', None)]
                    date_inputs = [i for i in inputs if i.get_attribute('type') == 'date']
                    
                    if date_inputs:
                        date_str = answer.strftime("%Y-%m-%d") if isinstance(answer, datetime) else gen_dob().strftime("%Y-%m-%d")
                        date_inputs[0].clear()
                        date_inputs[0].send_keys(date_str)
                        print(f"   ↳ Date entered: {date_str}")
                        continue
                    
                    if text_inputs:
                        target = text_inputs[0]
                        if isinstance(answer, datetime):
                            formatted = answer.strftime("%d/%m/%Y")
                        else:
                            formatted = str(answer)
                        
                        # Ensure PIN/postal codes are numeric only
                        if "pin" in label.lower() or "postal" in label.lower() or "zip" in label.lower():
                            formatted = re.sub(r'\D', '', formatted)
                        
                        target.clear()
                        time.sleep(0.2)
                        target.send_keys(formatted)
                        continue
                
                # === TEXTAREA ===
                textareas = q.find_elements(By.XPATH, './/textarea')
                if textareas:
                    val = answer.strftime("%d/%m/%Y") if isinstance(answer, datetime) else str(answer)
                    textareas[0].clear()
                    time.sleep(0.2)
                    textareas[0].send_keys(val)
                    continue
                
                # === RADIO BUTTONS ===
                radios = q.find_elements(By.XPATH, './/div[@role="radio"]')
                if radios:
                    chosen = None
                    if answer:
                        ans_low = str(answer).strip().lower()
                        for r in radios:
                            try:
                                txt = r.text.strip().lower()
                                if ans_low in txt or txt in ans_low:
                                    chosen = r
                                    break
                            except Exception:
                                continue
                    
                    if not chosen:
                        chosen = random.choice(radios)
                    
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", chosen)
                    time.sleep(0.2)
                    chosen.click()
                    continue
                
                # === DROPDOWNS ===
                dropdowns = q.find_elements(By.XPATH, './/div[@role="listbox"]')
                if dropdowns:
                    dropdowns[0].click()
                    time.sleep(0.6)
                    
                    options = driver.find_elements(By.XPATH, '//div[@role="option"]')
                    matched = None
                    
                    if answer and options:
                        ans_low = str(answer).strip().lower()
                        for opt in options:
                            try:
                                if ans_low in opt.text.strip().lower():
                                    matched = opt
                                    break
                            except Exception:
                                continue
                    
                    if not matched and options:
                        matched = random.choice(options)
                    
                    if matched:
                        matched.click()
                        time.sleep(0.3)
                        continue
                
            except Exception as e:
                print(f"⚠️ Error filling Q{idx}: {str(e)[:80]}")
                continue
        
        # === SUBMIT FORM ===
        print("\n📤 Looking for submit button...")
        try:
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//span[text()="Submit" or text()="Send"]/ancestor::div[@role="button"]'))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
            time.sleep(0.5)
            submit_button.click()
            print("✅ Form submitted!")
        except Exception as e:
            print(f"⚠️ Submit button error: {e}")
            driver.save_screenshot("error_submit.png")
        
        # Wait for confirmation page
        time.sleep(4)
        driver.save_screenshot(SCREENSHOT)
        print(f"📸 Screenshot saved as {SCREENSHOT}")
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        driver.save_screenshot("error_critical.png")
        raise
    finally:
        driver.quit()

# ---------------------
# EMAIL FUNCTION
# ---------------------
def send_email():
    """Send assignment submission email with attachments."""
    print("\n📧 Preparing email...")
    
    msg = EmailMessage()
    msg['Subject'] = f"Python (Selenium) Assignment - {YOUR_NAME}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = ", ".join(RECEIVERS)
    if CC and CC[0]:  # Only add CC if not empty
        msg['Cc'] = ", ".join(CC)
    
    email_body = f"""Dear Team,

Please find attached my Python (Selenium) assignment submission.

Included:
1. Screenshot of Google Form submission
2. Source code (GitHub): {GITHUB_LINK}
3. Portfolio: {PORTFOLIO_LINK}
4. Resume (attached)
5. Availability: Full-time (2100 hrs to 0300 hrs Indian time, UTC+5:30 for 6 months)

Technical Details:
- Python 3.x with Selenium WebDriver
- Automated form filling with intelligent field detection
- Error handling and screenshot capture
- Email automation with SMTP

Thank you for your consideration.

Best regards,
{YOUR_NAME}
"""
    
    msg.set_content(email_body)
    
    # Attach screenshot
    try:
        with open(SCREENSHOT, "rb") as f:
            msg.add_attachment(f.read(), maintype='image', subtype='png', filename=SCREENSHOT)
        print("✅ Screenshot attached")
    except FileNotFoundError:
        print(f"⚠️ Warning: '{SCREENSHOT}' not found, skipping screenshot attachment")
    
    # Attach resume
    try:
        with open("resume.pdf", "rb") as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename="resume.pdf")
        print("✅ Resume attached")
    except FileNotFoundError:
        print("⚠️ Warning: 'resume.pdf' not found, skipping resume attachment")
    
    # Send email
    try:
        print("📤 Sending email via Gmail SMTP...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
        print("✅ Assignment email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        raise

# ---------------------
# MAIN EXECUTION (for testing)
# ---------------------
if __name__ == "__main__":
    print("🚀 Starting automation test...")
    try:
        fill_form_and_capture()
        send_email()
        print("\n✅ All tasks completed successfully!")
    except Exception as e:
        print(f"\n❌ Automation failed: {e}")