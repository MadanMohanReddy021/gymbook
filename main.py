from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import httpx
import re
import os
import traceback
import time
import json
import logging

# ---------------- LOGGING SETUP ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI()

# -------- LOAD USERS --------
logger.info("Loading users.json...")
with open("users.json", "r") as f:
    USERS = json.load(f)
logger.info(f"{len(USERS)} users loaded successfully")


# ---------------- HOME ----------------
@app.get("/", response_class=HTMLResponse)
@app.head("/")
def home(request: Request):
    logger.info("Home page accessed")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "index.html")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------- BOOK ----------------
@app.post("/book")
def book(
    userid: str = Form(...),
    password: str = Form(...),
    date: str = Form(...),
    timeslot: str = Form(...)
):

    logger.info("=================================================")
    logger.info("NEW BOOKING REQUEST RECEIVED")
    logger.info(f"UserID: {userid}")
    logger.info(f"Date param: {date}")
    logger.info(f"Timeslot: {timeslot}")

    try:

        # -------- CHECK USER EXISTS --------
        if userid not in USERS:
            logger.warning("User not registered in system")
            return {"error": "User not registered in system"}

        user_data = USERS[userid]
        logger.info(f"User found: {user_data['name']}")

        # ---------- DATE ----------
        if date == "today":
            selected_date = datetime.now()
        else:
            selected_date = datetime.now() + timedelta(days=1)

        formatted_date = selected_date.strftime("%d-%b-%Y")
        logger.info(f"Formatted booking date: {formatted_date}")

        # ---------- SELENIUM SETUP ----------
        logger.info("Starting Selenium WebDriver...")

        chrome_options = webdriver.ChromeOptions()
        chrome_options.binary_location = "/usr/bin/chromium"

        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 30)

        logger.info("WebDriver started successfully")

        # ---------- LOGIN ----------
        logger.info("Opening login page...")
        driver.get("https://login.gitam.edu/Login.aspx")

        username = wait.until(
            EC.presence_of_element_located((By.NAME, "txtusername"))
        )
        password_field = driver.find_element(By.NAME, "password")

        username.send_keys(userid)
        password_field.send_keys(password)

        logger.info("Username and password entered")

        # ---------- CAPTCHA ----------
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "preview")))
        captcha_spans = driver.find_elements(By.CSS_SELECTOR, ".preview span")
        captcha_text = "".join([span.text for span in captcha_spans])

        logger.info(f"Captcha extracted: {captcha_text}")

        captcha_input = driver.find_element(By.ID, "captcha_form")
        captcha_input.send_keys(captcha_text)

        driver.find_element(By.NAME, "Submit").click()
        logger.info("Login submitted")

        time.sleep(6)

        current_url = driver.current_url
        logger.info(f"Current URL after login: {current_url}")

        if "Login" in current_url:
            logger.error("LOGIN FAILED - Still on login page")
            driver.save_screenshot(f"{userid}_login_failed.png")
            driver.quit()
            return {
                "error": "login failed",
                "captcha_used": captcha_text
            }

        logger.info("LOGIN SUCCESSFUL")

        # ---------- COPY COOKIES ----------
        logger.info("Copying session cookies...")
        session = httpx.Client()

        for cookie in driver.get_cookies():
            session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain"),
                path=cookie.get("path")
            )

        driver.quit()
        logger.info("Browser closed successfully")

        # ---------- OPEN SPORTS ----------
        logger.info("Opening sports page...")
        r4 = session.get("https://gstudent.gitam.edu/Home/Gsports")
        html = r4.text

        match = re.search(r"window\.location\.href\s*=\s*'([^']+)'", html)

        if not match:
            logger.error("Sports redirect not found in HTML")
            return {"error": "sports redirect not found"}

        redirect_url = match.group(1)
        logger.info(f"Sports redirect URL: {redirect_url}")

        session.get(redirect_url)
        logger.info("Redirected to sports system successfully")

        # ---------- BOOKING ----------
        logger.info("Preparing booking payload...")

        payload = {
            "form-facility": "UniSex Fitness Centre",
            "facility": "31",
            "form-court": "court 1",
            "court": "61",
            "from_date": formatted_date,
            "timeslot": timeslot,
            "no-of-players": "1",
            "terms": "yes",
            "shift_id": "62",
            "type_of_user": "Gitam",
            "registration__st_fee_hidden": "",
            "app_dept": "CSE",
            "campus": "BLR",
            "college": "GST",
            "resource_id": "",
            "resource": "UniSex Fitness Centre",
            "std": "4",
            "empid": userid,
            "applicant_name": user_data["name"],
            "mobile": user_data["mobile"],
            "email": user_data["email"],
            "user_type": "student"
        }

        logger.info("Sending booking POST request...")

        r = session.post(
            "https://gsports.gitam.edu/schedule_st/schedule",
            data=payload
        )

        logger.info(f"Booking response status: {r.status_code}")
        logger.info(f"Booking response body (first 500 chars): {r.text[:500]}")

        if r.status_code == 200:
            logger.info("BOOKING REQUEST SENT SUCCESSFULLY")
        else:
            logger.warning("Booking returned non-200 status")

        logger.info("BOOKING PROCESS COMPLETED")
        logger.info("=================================================")

        return {
            "booking_status_code": r.status_code,
            "selected_user": user_data["name"],
            "selected_date": formatted_date,
            "selected_slot": timeslot
        }

    except Exception as e:
        logger.exception("CRITICAL ERROR OCCURRED")
        return {
            "error": str(e),
            "trace": traceback.format_exc()
        }
