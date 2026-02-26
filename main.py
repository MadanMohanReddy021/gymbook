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

app = FastAPI()


# ---------------- HOME ----------------
@app.get("/", response_class=HTMLResponse)
@app.head("/")
def home(request: Request):
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

    try:
        # ---------- DATE ----------
        if date == "today":
            selected_date = datetime.now()
        else:
            selected_date = datetime.now() + timedelta(days=1)

        formatted_date = selected_date.strftime("%d-%b-%Y")

        # ---------- SELENIUM SETUP (DOCKER CHROMIUM) ----------
        chrome_options = webdriver.ChromeOptions()
        chrome_options.binary_location = "/usr/bin/chromium"
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        service = Service("/usr/bin/chromedriver")

        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 25)

        # ---------- LOGIN ----------
        driver.get("https://login.gitam.edu/Login.aspx")

        username = wait.until(
            EC.presence_of_element_located((By.NAME, "txtusername"))
        )
        password_field = driver.find_element(By.NAME, "password")

        username.send_keys(userid)
        password_field.send_keys(password)
        driver.find_element(By.NAME, "Submit").click()

        wait.until(EC.url_contains("gstudent"))

        # ---------- COPY COOKIES ----------
        session = httpx.Client()
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])

        driver.quit()

        # ---------- OPEN SPORTS ----------
        r4 = session.get("https://gstudent.gitam.edu/Home/Gsports")
        html = r4.text

        match = re.search(r"window\.location\.href\s*=\s*'([^']+)'", html)
        if not match:
            return {"error": "redirect url not found"}

        redirect_url = match.group(1)
        session.get(redirect_url)

        # ---------- FULL BOOKING PAYLOAD ----------
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
            "applicant_name": "SAREDDY MADAN MOHAN REDDY",
            "mobile": "9502175244",
            "email": "msareddy@student.gitam.edu",
            "user_type": "student"
        }

        r = session.post(
            "https://gsports.gitam.edu/schedule_st/schedule",
            data=payload
        )

        return {
            "booking_status_code": r.status_code,
            "selected_date": formatted_date,
            "selected_slot": timeslot
        }

    except Exception as e:
        return {"error": str(e)}