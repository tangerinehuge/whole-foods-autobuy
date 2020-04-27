import sys
import time
import os
from pathlib import Path
import platform
import requests
import json
import socket
import PySimpleGUI as sg
import datetime

from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from twilio.rest import Client

if platform.system == 'Linux':
    CONFIG_FILE = Path(Path.home() / "config.json")
else:
    CONFIG_FILE = Path(Path.home() / "Documents/config.json")

DEFAULT_CONFIG = {"interval": 30, "purchasing_enabled": True, 
    "today_enabled": True, "tomorrow_enabled": True, "ifttt_enabled": False,
    "ifttt_webhook": "", "slack_enabled": False, "slack_webhook": "",
    "twilio_enabled": False, "twilio_account_sid": "", "twilio_auth_token": "",
    "twilio_phone_number": "", "twilio_cell_number": ""}

def load_config(config_file, default_config):
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception:
        config = default_config
        save_config(config_file, config)
    return config

def save_config(config_file, values):
    with open(config_file, 'w') as f:
        json.dump(values, f)

def display_config_window():
    # set theme for config window
    sg.theme('Dark')

    # config = json.load(cf)
    config = load_config(CONFIG_FILE, DEFAULT_CONFIG)

    # set columns for each setting
    ifttt = [
        [sg.Text('IFTTT Webhook URL:'),
        sg.Input(default_text=config['ifttt_webhook'],
        key='ifttt_webhook')]
        ]
    slack = [
        [sg.Text('Slack Webhook URL:'),
        sg.Input(default_text=config['slack_webhook'],
        key='slack_webhook')]
        ]
    twilio = [
        [sg.Text('Twilio Account SID:'),
        sg.Input(default_text=config['twilio_account_sid'],
        key='twilio_account_sid')],
        [sg.Text('Twilio Auth Token:'),
        sg.Input(default_text=config['twilio_auth_token'],
        key='twilio_auth_token')],
        [sg.Text('Twilio Phone #:'),
        sg.Input(default_text=config['twilio_phone_number'],
        key='twilio_phone_number')],
        [sg.Text('Your Phone #:'),
        sg.Input(default_text=config['twilio_cell_number'],
        key='twilio_cell_number')]
        ]

    instructions = """INSTRUCTIONS:
1. Select from the following options and click "Start" to begin.
2. Amazon will open in a new Chrome window.
3. Login to Amazon and add items to your cart if you haven't already.
4. When you get to the delivery window selection page the script will start\
refreshing at the selected interval and place the order for the first\
available slot.
"""

    layout = [
        [
            sg.Text(instructions, size=(70,7))
        ],
        [
            sg.Text('Refresh interval in seconds:'), sg.Slider(range=(5,600), 
            default_value=config['interval'], orientation='horizontal',
            size=(60,15), key='interval')
        ],
        [
            sg.Checkbox('Enable Purchasing (uncheck to stop at purchase screen)', 
            default=config['purchasing_enabled'], key='purchasing_enabled')
        ],
        [
            sg.Text('Accept delivery windows:'), 
            sg.Checkbox('Today', key="today_enabled",
            default=config['today_enabled'], change_submits=True),
            sg.Checkbox('Tomorrow', key="tomorrow_enabled",
            default=config['tomorrow_enabled'], change_submits=True)
        ],
        [
            sg.Checkbox('Enable IFTTT Notification', change_submits=True,
            default=config['ifttt_enabled'], key="ifttt_enabled"),
            sg.Column(ifttt, key='ifttt_opts', visible=config['ifttt_enabled'])
        ],
        [
            sg.Checkbox('Enable Slack Notification', change_submits=True,
            default=config['slack_enabled'], key="slack_enabled"),
            sg.Column(slack, key='slack_opts', visible=config['slack_enabled'])
            ],
        [
            sg.Checkbox('Enable Twilio SMS Notification', change_submits=True,
            default=config['twilio_enabled'], key="twilio_enabled"),
            sg.Column(twilio, key='twilio_opts', 
            visible=config['twilio_enabled'])
        ],
        [
            sg.Submit('Start', key="start_button"),
            sg.Text("You must select at least one delivery day", 
            text_color='red', key="warn_message", visible=False)
        ]
    ]

    # draw window
    window = sg.Window('Amazon Whole Foods Autobuy', layout, 
        font=("Arial", 14), keep_on_top=True)

    # process input into config window
    while True:  # Event Loop
        event, values = window.read()
        # # print(event, values)
        if event is None:
            sys.exit(0)
        if event == 'start_button':
            values['interval'] = int(values['interval'])
            save_config(CONFIG_FILE,values)
            break
        if values['ifttt_enabled'] == True:
            window.FindElement('ifttt_opts').Update(visible=True)
        if values['ifttt_enabled'] == False:
            window.FindElement('ifttt_opts').Update(visible=False)
        if values['slack_enabled'] == True:
            window.FindElement('slack_opts').Update(visible=True)
        if values['slack_enabled'] == False:
            window.FindElement('slack_opts').Update(visible=False)
        if values['twilio_enabled'] == True:
            window.FindElement('twilio_opts').Update(visible=True)
        if values['twilio_enabled'] == False:
            window.FindElement('twilio_opts').Update(visible=False)
        if (values['today_enabled'] == False and
                values['tomorrow_enabled'] == False):
            window.FindElement('start_button').Update(disabled=True)
            window.FindElement('warn_message').Update(visible=True)
        else:
            window.FindElement('start_button').Update(disabled=False)
            window.FindElement('warn_message').Update(visible=False)


    window.close()

    return(values)


def send_ifttt(webhook):
    report = {'value1': "Whole Foods order has been placed!"}
    requests.post(webhook, data=report)


def send_sms(account_sid, auth_token, twilio_number, cell_number):
    client = Client(account_sid, auth_token)

    # message = client.messages \
    client.messages.create(
                        body="Whole Foods order has been placed!",
                        from_=twilio_number,
                        to=cell_number
                    )

    # print(message.sid)


def send_slack_notification(webhook):
    data = {
        'text': 'Whole Foods order has been placed!',
        'username': 'Whole Foods Checkout Script',
        'icon_emoji': ':robot_face:'
    }

    response = requests.post(webhook, data=json.dumps(
        data), headers={'Content-Type': 'application/json'})
    return response


def show_message_box():
    sg.theme('Dark')  # please make your windows colorful
    
    alert_layout = [
            [sg.Text('Whole Foods purchase completed successfully!')],
            [sg.CloseButton("Close")]
            ]

    alert_window = sg.Window('Whole Foods Purchase Successful', alert_layout)

    alert_window.read()
    alert_window.close()


def init_webdriver():
    # check for chromedriver and install if not present
    # webdriver.Chrome(ChromeDriverManager().install())

    # create webdriver object
    chrome_options = Options()
    
    # create socket object
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # check to see if chrome is running in remote debugging mode
    location = ("127.0.0.1", 9222)
    result_of_check = a_socket.connect_ex(location)

    # close socket object
    a_socket.close()

    if result_of_check == 0:
        chrome_options.add_experimental_option(
            "debuggerAddress",
            "127.0.0.1:9222")
    
    chromedriver_path = ChromeDriverManager().install()
    
    # config webdriver and fetch product URL
    driver = webdriver.Chrome(executable_path=chromedriver_path, options=chrome_options)
    
    return driver

def getWFSlot(driver, productUrl, config):
    driver.get(productUrl)
    # driver.implicitly_wait(3)

    no_open_slots = True

    alternate_url = "https://www.amazon.com/gp/buy/itemselect/handlers/display\
        .html?ie=UTF8&useCase=singleAddress&hasWorkingJavascript=1"

    # loop while no open slots found
    while no_open_slots:

        # loop while URL is not on the delivery window page
        while driver.current_url not in [productUrl, alternate_url]:
            time.sleep(5)

        try:
            # time.sleep(1) # wait 1 second for page to fully load  
            today = datetime.datetime.now()
            tomorrow = today + datetime.timedelta(days=1)  
            todaystr = today.strftime("%Y%m%d")
            tomorrowstr = tomorrow.strftime("%Y%m%d")

            today_button = driver.find_element_by_name(todaystr)
            tomorrow_button = driver.find_element_by_name(tomorrowstr)
            day_enabled = True
            # todaystr = "20200424" # remove in prod
            # tomorrowstr = "20200425"
            if (today_button.get_attribute("disabled") is not None and
                    config['today_enabled'] and 
                    not config['tomorrow_enabled']):
                day_enabled = False
            elif not config['today_enabled'] and config['tomorrow_enabled']:
                if (tomorrow_button.get_attribute("disabled") is not None):
                    day_enabled = False
                elif today_button.get_attribute("disabled") is None:
                    driver.execute_script("arguments[0].scrollIntoView(true);",
                        tomorrow_button)
                    tomorrow_button.click()

            # search for delivery slot buttons, select first one, then click continue
            slot_xpath = "//button[@class='a-button-text ufss-slot-toggle-native-button']"
            if driver.find_elements_by_xpath(slot_xpath) and day_enabled:
                try:
                    slot_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, slot_xpath))
                        )
                    # if slot_button.find_element_by_class_name("ufss-aok-offscreen").get_attribute("innerText") == "By 2:00 PM":
                    #     print("Found button")
                    driver.execute_script("arguments[0].scrollIntoView(true);", slot_button)
                    slot_button.click()
                    # else:
                    #     continue
                except Exception as ex:
                    print("slot button not clickable")
                    print(repr(ex))
                    continue
                
                try:
                    continue_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                        (By.XPATH, "//input[@class='a-button-input' and @type='submit']")
                        ))
                    driver.execute_script("arguments[0].scrollIntoView(true);", continue_button)
                    continue_button.click()
                except:
                    # print("continue button not clickable")
                    continue

            else:
                # if no slots found, wait specified interval before refreshing page and restarting loop
                # print(f"No slots found, waiting {config['interval']} seconds...", end = "")
                time.sleep(config['interval'])
                driver.refresh()
                # print("refreshing.")
                continue

            # click continue if payment selection page shows up
            place_order_title = "Place Your Order - Amazon.com Checkout"
            select_payment_title = "Select a Payment Method - Amazon.com Checkout"

            WebDriverWait(driver, 10).until(lambda x: driver.title in [select_payment_title, place_order_title])

            if driver.title == select_payment_title:
                # print("Payment selection page loaded, selecting default and continuing")
                try:
                    top_continue_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                        (By.XPATH, "//input[@class='a-button-text ' and @type='submit']")
                        ))
                    driver.execute_script("arguments[0].scrollIntoView(true);", top_continue_button)
                    top_continue_button.click()
                except Exception:
                    # print(repr(ex))
                    pass
            else:
                # print("Payment selection page not loaded, proceeding with purchase")
                pass

            WebDriverWait(driver, 10).until(lambda x: driver.title == place_order_title)

            # place order
            if driver.title == place_order_title:
                try:
                    place_order_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                        (By.XPATH, "//input[@class='a-button-text place-your-order-button']")
                        ))
                    if config['purchasing_enabled']:
                        driver.execute_script("arguments[0].scrollIntoView(true);", place_order_button)
                        place_order_button.click()
                        # print("Order placed!")

                        # send notifications
                        if config.notifications['slack']:
                            # print('sending slack notification')
                            send_slack_notification(config['slack_webhook'])
                        if config.notifications['twilio_sms']:
                            # print('sending sms notification')
                            send_sms(config['twilio_account_sid'], config['twilio_auth_token'], config['twilio_phone_number'], config['twilio_cell_number'])
                        if config.notifications['ifttt']:
                            # print('sending ifttt notification')
                            send_ifttt(config['ifttt_webhook'])
                        if config.notifications['message_box']:
                            # print('displaying visual notification')
                            show_message_box()
                    else:
                        # print("Purchasing disabled. Please complete purchase manually.")
                        pass

                    # sleep for an hour after success then quit
                    time.sleep(3600)
                    driver.quit()
                    sys.exit(0)
                except TimeoutError:
                    continue # retry loop if button doesn't appear for some reason
                except:
                    # if error, sleep for an hour in case the session can be manually recovered
                    time.sleep(3600)     
            
        except:
            # print("The following exception occured in the main loop. Restarting.")
            # print(sys.exc_info()[0])
            # print(sys.exc_info()[1])
            # print(sys.exc_info()[2].tb_lineno)
            pass     

if __name__ == "__main__":
    try:
        config_values = display_config_window()
        driver = init_webdriver()
        getWFSlot(driver, 'https://www.amazon.com/gp/buy/shipoptionselect/handlers/display.html?hasWorkingJavascript=1', config_values)
        # getWFSlot(driver, 'file:///Users/galen/Downloads/two%20days%20Reserve%20a%20Time%20Slot%20-%20Amazon.com%20Checkout.html', config_values)
    except WebDriverException:
        driver.quit()
