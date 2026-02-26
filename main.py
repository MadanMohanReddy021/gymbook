from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import httpx
import re

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html") as f:
        return f.read()


@app.post("/book")
def book(
    userid: str = Form(...),
    password: str = Form(...),
    date: str = Form(...),
    timeslot: str = Form(...)
):

    # ---------- date selection ----------
    if date == "today":
        selected_date = datetime.now()
    else:
        selected_date = datetime.now() + timedelta(days=1)

    formatted_date = selected_date.strftime("%d-%b-%Y")

    # ---------- selenium login ----------
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    driver.get("https://login.gitam.edu/Login.aspx")

    username = wait.until(
        EC.presence_of_element_located((By.NAME, "txtusername"))
    )
    password_field = driver.find_element(By.NAME, "password")

    username.send_keys(userid)
    password_field.send_keys(password)

    driver.find_element(By.NAME, "Submit").click()

    wait.until(EC.url_contains("gstudent"))

    # ---------- copy cookies ----------
    session = httpx.Client()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'])

    driver.quit()

    # ---------- open sports page ----------
    r4 = session.get("https://gstudent.gitam.edu/Home/Gsports")
    html = r4.text

    match = re.search(r"window\.location\.href\s*=\s*'([^']+)'", html)

    if not match:
        return {"status": "redirect failed"}

    redirect_url = match.group(1)
    session.get(redirect_url)

    # ---------- booking payload ----------
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
        "applicant_name": " SAREDDY MADAN MOHAN REDDY",
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
