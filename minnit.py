from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import time
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from selenium.webdriver.firefox.options import Options
import argparse

parser = argparse.ArgumentParser(description='Save chats from a minnit.chat chatroom')
parser.add_argument("chatname", type=str,
                    help='Name of the Chatroom as used in the chat URL')
parser.add_argument('-s', '--scroll', type=int, default=100,
                    help='number of times to scroll up in the chat (experiment with this to get the correct number)')
parser.add_argument('-o', '--outdir', type=str, help='.csv output directory (include trailing /)', default=None)
parser.add_argument('-d', '--date', type=str, help='restrict message output to date (YYYY-MM-DD)',
                    default=datetime.today().date().strftime('%Y-%m-%d'))
parser.add_argument('--csv', action='store_true', default=False, help='CSV output (default JSON)')

args = parser.parse_args()

date = datetime.strptime(args.date, "%Y-%m-%d").date()

out_filename = date.strftime('%Y%m%d')

firefox_options = Options()
firefox_options.headless = True

driver = webdriver.Firefox(options=firefox_options)
driver.set_window_size(1080, 4000)

action = webdriver.ActionChains(driver)

driver.implicitly_wait(10)
wait = WebDriverWait(driver, 10)

driver.get("https://minnit.chat/" + args.chatname + "?embed&popout")

time.sleep(5)

driver.switch_to.frame(0)

# click join button
try:

    join_button = driver.find_element(By.XPATH, "//button[@onclick='agreeToChatRules()']")
    join_button.click()
except:
    # no join button found, so simply proceed
    pass

driver.switch_to.parent_frame()

chat_iframe = driver.find_element(By.ID, 'chat-iframe')

driver.switch_to.frame(chat_iframe)

iframe_html = driver.find_element(By.TAG_NAME, 'html')

# scroll up

i = 1
while True:
    driver.execute_script("document.getElementById('prfscrMsgWindow').scrollTop=-4500")
    time.sleep(1)

    i = i + 1

    if i >= args.scroll:
        break
    if divmod(i, 5)[1] == 0:
        driver.execute_script("document.getElementById('prfscrMsgWindow').scrollTop=100")

# store html code
html = driver.find_element(By.TAG_NAME, 'html')
html = html.get_attribute("outerHTML")

driver.quit()


# function to parse messages
def parse_messages(source):
    bs = BeautifulSoup(source, 'html.parser')

    msg_window = bs.find(id='msgWindow')

    messages = [m for m in msg_window]

    def message(bs_m):
        return bs_m.find('span', {'class': ["msgTextOnly"]}).get_text(strip=True)

    def user(bs_m):
        return bs_m.find('span', {'class': ["msgNick"]}).get_text(strip=True)

    message_dicts = [{'time': int(m['data-timestamp']), 'user': user(m), 'message': message(m)} for m in messages if
                     'id' in m.attrs and m['id'] != 'imgblock']

    message_dicts.sort(key=lambda x: x['time'])

    return message_dicts


messages = parse_messages(html)

# put into dataframe
df_messages = pd.DataFrame.from_records(messages)

if args.date is not None:
    # filter for date
    df_messages['day'] = df_messages.time.apply(lambda d: datetime.utcfromtimestamp(int(d)).date())
    df_messages = df_messages[df_messages['day'] == date].__deepcopy__()
    df_messages.drop('day', axis=1, inplace=True)

if args.csv:
    output = df_messages.to_json()
else:
    output = df_messages.to_csv(sep="\t")

if args.outdir is not None:
    # write to chats
    open(args.outdir + out_filename + '.txt', 'w').write(output)
else:
    print(output)
