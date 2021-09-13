from selenium import webdriver
import urllib.request
from selenium.webdriver.support.ui import Select
import time
from selenium.webdriver.chrome.options import Options
import os
from datetime import date
import glob

from utilties.send_email import send_email
from utilties.anticaptcha import solve_captcha


def initialize_selenium_driver(download_directory):
    chrome_options = Options()
    chrome_options.add_experimental_option('prefs',  {
        "download.default_directory": download_directory,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
        }
    )
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def download_wait(path_to_downloads):
    seconds = 0
    dl_wait = True
    while dl_wait and seconds < 20:
        time.sleep(1)
        dl_wait = False
        for fname in os.listdir(path_to_downloads):
            if fname.endswith('.crdownload'):
                dl_wait = True
        seconds += 1
    return seconds


def main():
    today = date.today()
    dateFormat = today.strftime("%m/%d/%Y")  # Use this for selenium date
    dirDateFormat = today.strftime("%m_%d_%Y")
    directory = "report_files/reports_" + dirDateFormat
    stateFileName = "report_files_downloaded_" + dirDateFormat + ".txt"
    if not os.path.exists(directory):
        os.makedirs(directory)
    driver = initialize_selenium_driver(directory)

    url = "https://ohtrafficdata.dps.ohio.gov/crashretrieval"
    driver.get(url)
    inputElement = driver.find_element_by_id("txtCrashStartDate")
    inputElement.send_keys(dateFormat)
    inputElement = driver.find_element_by_id("txtCrashEndDate")
    inputElement.send_keys(dateFormat)
    select = Select(driver.find_element_by_id('ddlCounties'))
    select.select_by_visible_text('Hamilton County')

    img = driver.find_element_by_xpath('//img[@class="captchaImage"]')
    src = img.get_attribute('src')

    # download the image
    captcha_directory = "captcha-images"
    if not os.path.exists(captcha_directory):
        os.makedirs(captcha_directory)
    urllib.request.urlretrieve(src, "captcha-images/captcha-image.png")

    captcha_text = solve_captcha("((token))",
                                 "captcha-images/captcha-image.png")

    inputElement = driver.find_element_by_id("txtCaptcha")
    inputElement.send_keys(captcha_text)
    driver.find_element_by_id('btnSearch').click()

    print("done retrieving captcha...")
    time.sleep(2)

    print("click through pages...")
    hasNext = True
    while hasNext:
        table = driver.find_element_by_xpath(
                           "//table[@id='mySearchTable']")
        for row in table.find_elements_by_xpath(".//tr"):
            row_information = []
            for td in row.find_elements_by_xpath(".//td"):
                row_information.append(td.text)
            with open(stateFileName, "a+") as file:
                file.seek(0)  # set position to start of file
                lines = file.read().splitlines()
                if row_information[1] in lines:
                    print("PDF alredy downloaded. Skipping...")
                else:
                    td.click()
                    file.write(row_information[1] + "\n")
                    if (download_wait(directory) >= 20):
                        print("Timed out downloading pdf.")
                    else:
                        report_filename = directory + "/GetReport_"
                        + td.text + ".pdf"
                        all_files_in_dir = directory + "/*"
                        list_of_files = glob.glob(all_files_in_dir)
                        latest_file = max(list_of_files, key=os.path.getctime)
                        os.rename(latest_file, report_filename)
        try:
            driver.find_element_by_xpath("//li[@aria-label='Next page']/a").click()
            time.sleep(1)
        except Exception as inst:
            print(type(inst))
            print("No next page exists")
            hasNext = False

    print("Done with selenium script")
    driver.close()

    report_files = os.listdir(directory)
    # Send Email
    send_email(directory, report_files)


if __name__ == "__main__":
    main()
