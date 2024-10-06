
# -*- coding: utf-8 -*-
"""
Created on Wed May 17 13:39:11 2023

@author: harsi
"""
import time
import json
import random
import configparser
from tqdm import tqdm
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

config = configparser.ConfigParser()
config.read('config.ini')

USERNAME = config['USVISA']['USERNAME']
PASSWORD = config['USVISA']['PASSWORD']
SCHEDULE_ID = config['USVISA']['SCHEDULE_ID']
MY_SCHEDULE_DATE = config['USVISA']['MY_SCHEDULE_DATE']
COUNTRY_CODE = config['USVISA']['COUNTRY_CODE'] 
FACILITY_ID = config['USVISA']['FACILITY_ID']

BOT_TOKEN = config['TELEGRAM']['BOT_TOKEN']
USER_ID1 = config['TELEGRAM']['USER_ID1']

SHOW_GUI = config['BROWSEROPTION']['SHOW_GUI']

REGEX_CONTINUE = "//a[contains(text(),'Continue')]"

def MY_CONDITION(month, day): return True # No custom condition wanted for the new scheduled date

STEP_TIME = 0.5  # time between steps (interactions with forms): Best 0.5 seconds
RETRY_TIME = 60*15  # wait time between retries/checks for available dates: Best 15 minutes
EXCEPTION_TIME =60*30  # wait time when an exception occurs: Best 30 minutes
COOLDOWN_TIME = 60*60*2  # wait time when temporarily banned (empty list): Best 120 minutes

DATE_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/days/{FACILITY_ID}.json?appointments[expedite]=false"
TIME_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/times/{FACILITY_ID}.json?date=%s&appointments[expedite]=false"
APPOINTMENT_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment"
EXIT = False

def send_notification(msg):
	# Create url
	url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'

	# Create json link with message
	data1 = {'chat_id': USER_ID1, 'text': msg}
	
	# POST the message
	requests.post(url, data1)

def get_driver():
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--verbose")
    if SHOW_GUI == 'False':
        options.add_argument('--no-sandbox')
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument("--window-size=1920, 1200")
        options.add_argument("enable-automation")
        options.add_argument("--disable-infobars")
        options.add_argument('--disable-dev-shm-usage')
        user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36'
        options.add_argument(f'user-agent={user_agent}')
    driver = webdriver.Chrome(service=service, options=options)
    return driver

driver = get_driver()

def login():
    # Bypass reCAPTCHA
    driver.get(f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv")
    time.sleep(STEP_TIME+random.random())
    a = driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
    a.click()
    time.sleep(STEP_TIME+random.random())

    print("Login start...")
    href = driver.find_element(By.XPATH, '//*[@id="header"]/nav/div[1]/div[1]/div[2]/div[1]/ul/li[3]/a')
   
    href.click()
    time.sleep(STEP_TIME+random.random())
    Wait(driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))

    print("\tclick bounce")
    a = driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
    a.click()
    time.sleep(STEP_TIME+random.random())

    do_login_action()


def do_login_action():
    print("\tinput email")
    user = driver.find_element(By.ID, 'user_email')
    user.send_keys(USERNAME)
    time.sleep(random.randint(1, 3))

    print("\tinput pwd")
    pw = driver.find_element(By.ID, 'user_password')
    pw.send_keys(PASSWORD)
    time.sleep(random.randint(1, 3))

    print("\tclick privacy")
    box = driver.find_element(By.CLASS_NAME, 'icheckbox')
    box .click()
    time.sleep(random.randint(1, 3))

    print("\tcommit")
    btn = driver.find_element(By.NAME, 'commit')
    btn.click()
    time.sleep(random.randint(1, 3))

    try:
        Wait(driver, 60).until(EC.presence_of_element_located((By.XPATH, REGEX_CONTINUE)))
    except TimeoutException:
        driver.refresh()
        time.sleep(random.randint(1, 3))

    print("\tlogin successful!")
    
def get_date():    
    session = driver.get_cookie("_yatri_session")["value"] 
    NEW_GET = driver.execute_script(
        "var req = new XMLHttpRequest();req.open('GET', '"
        + str(DATE_URL)
        + "', false);req.setRequestHeader('Accept', 'application/json, text/javascript, */*; q=0.01');req.setRequestHeader('X-Requested-With', 'XMLHttpRequest'); req.setRequestHeader('Cookie', '_yatri_session="
        + session
        + "'); req.send(null);return req.responseText;"
    )
    return json.loads(NEW_GET)

def get_time(date):
    time_url = TIME_URL % date
    try:
        session = driver.get_cookie("_yatri_session")["value"]
    except:
        print("get_time() failed to get cookie")
    try:
        content = driver.execute_script(
            "var req = new XMLHttpRequest();req.open('GET', '"
            + str(time_url)
            + "', false);req.setRequestHeader('Accept', 'application/json, text/javascript, */*; q=0.01');req.setRequestHeader('X-Requested-With', 'XMLHttpRequest'); req.setRequestHeader('Cookie', '_yatri_session="
            + session
            + "'); req.send(null);return req.responseText;"
        )
    except:
        print("get_time() failed to execute script")
    data = json.loads(content)
    time = data.get("available_times")[-1]
    print(f"Got time successfully! {date} {time}")
    return time

def is_logged_in():
    content = driver.page_source
    if(content.find("error") != -1):
        return False
    return True

def print_dates(dates):
    print("Available dates:")
    for d in dates:
        print("%s \t business_day: %s" % (d.get('date'), d.get('business_day')))
    print()

last_seen = None

def get_available_date(dates):
    global last_seen

    def is_earlier(date):
        my_date = datetime.strptime(MY_SCHEDULE_DATE, "%Y-%m-%d")
        new_date = datetime.strptime(date, "%Y-%m-%d")
        result = my_date > new_date
        print(f'Is {my_date} > {new_date}:\t{result}')
        return result

    print("Checking for an earlier date:")
    for d in dates:
        date = d.get('date')
        if is_earlier(date) and date != last_seen:
            _, month, day = date.split('-')
            if(MY_CONDITION(month, day)):
                last_seen = date
                return date

def reschedule(date):
    global EXIT
    print(f"Starting Reschedule ({date})")

    try:
        time = get_time(date)
    except:
        print("reschedule() failed to get time")
    
    try:
        driver.get(APPOINTMENT_URL)
    except:
        print("reschedule() failed to get URL")
        
    try:
        
        data = {
            "utf8": driver.find_element(by=By.NAME, value='utf8').get_attribute('value'),
            "authenticity_token": driver.find_element(by=By.NAME, value='authenticity_token').get_attribute('value'),
            "confirmed_limit_message": driver.find_element(by=By.NAME, value='confirmed_limit_message').get_attribute('value'),
            "use_consulate_appointment_capacity": driver.find_element(by=By.NAME, value='use_consulate_appointment_capacity').get_attribute('value'),
            "appointments[consulate_appointment][facility_id]": FACILITY_ID,
            "appointments[consulate_appointment][date]": date,
            "appointments[consulate_appointment][time]": time,
        }
    except:
        print("reschedule() failed to create data")
    
    try:
        headers = {
            "User-Agent": driver.execute_script("return navigator.userAgent;"),
            "Referer": APPOINTMENT_URL,
            "Cookie": "_yatri_session=" + driver.get_cookie("_yatri_session")["value"]
        }
    except:
        print("reschedule() failed to create headers")
    try:
        r = requests.post(APPOINTMENT_URL, headers=headers, data=data)
    except:
        print("reschedule() request is not working")
        msg = "Reschedule request is not working"
        send_notification(msg)
    if(r.text.find('Successfully Scheduled') != -1):
        msg = f"Rescheduled Successfully! {date} {time}"
        send_notification(msg)
        EXIT = True
    else:
        msg = f"Reschedule Failed. {date} {time}"
        send_notification(msg)  

if __name__ == "__main__":
    
    login()
    retry_count = 0
    while 1:
        
        try:
            print("------------------")
            print(datetime.today())
            print(f"Retry count: {retry_count}")
            print()

            try:
                try:
                    driver.get(APPOINTMENT_URL)
                except:
                    print("Failed to get appointment URL")
                time.sleep(4*STEP_TIME+random.random())
                dates = get_date()[:5]
            except:
                try:
                    driver.delete_all_cookies()
                    login()
                except:
                    print("Failed to get login")
                    raise
                time.sleep(4*STEP_TIME+random.random())
                dates = get_date()[:5]     
            
            if not dates:
                cool_time = COOLDOWN_TIME+random.randint(1,30)
                msg=f"No date available....retrying in {cool_time} sec"
                print(msg)
                send_notification(msg)
                print("Cooldown period progress:")
                for _ in tqdm(range(cool_time)):
                    time.sleep(1)
                retry_count+=1
                
            else:
                print_dates(dates)
                date = get_available_date(dates)
                if date:
                    print()
                    msg = f"Date available: {date}"
                    print(msg)
                    send_notification(msg)
                    reschedule(date)
                    break              
                if not date:
                    ret_time = RETRY_TIME+random.randint(1,30)
                    msg=f"No earlier date is available....retrying in {ret_time} sec"
                    print(msg)
		    
                    print("Retry wait period progress:")
                    for _ in tqdm(range(ret_time)):
                        time.sleep(1)
                    retry_count+=1
        except Exception as e:
            msg = f"Help! Script Crashed: {e}" 
            send_notification(msg)
            break
                



