import os
import sys
import subprocess
import re
import requests
import json
from bs4 import BeautifulSoup
from tqdm import tqdm
import urllib3
import time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url_pattern = r"https://www\.[\w\-\.]+\.[a-zA-Z]{2,6}(\S*)?"
result_url = []
file_List = []
package_List = []
appkey_List = []
LOGIN_SESSION = ''
gsess = ''
def login():
    print("ImmuniWeb Login")
    USERID = input("아이디: ")
    PASS = input("패스워드: ")
    global LOGIN_SESSION
    global gsess
    LOGIN_SESSION = requests.Session()

    LOGIN_DATA = {
        "portal_type":"customer_portal",
        "login":USERID,
        "pass":PASS,
        "actbutton":"login",
        "actbutton1":"Login"
    }
    LOGIN_URL = "https://portal.immuniweb.com/client/login/"
    response = LOGIN_SESSION.post(LOGIN_URL, data=LOGIN_DATA, verify=False)
    if "OTP" in response.text:
        OTP_URL = "https://portal.immuniweb.com/client/"
        OTP = input("OTP CODE: ")
        OTP_DATA = {
            "OTP_T1_TEST" : OTP,
            "actbutton" : "Submit"
        }
        response = LOGIN_SESSION.post(OTP_URL,data=OTP_DATA, verify=False)
        gsess = LOGIN_SESSION.cookies.get('gsess')

    else:
        print("아이디 또는 비밀번호가 틀립니다.")
        sys.exit()
    
def getFileList():
    global file_List
    directory = "./apps"
    file_List = os.listdir(directory)

def resultStringReplace(result):
    result = result.replace(",", '')
    result = result.replace("'", '')
    return result

def scan():
    file_path = "../testid.txt"
    
    print("Scan Start")
    getFileList()
    global file_List
    global result_url

    if len(file_List) == 0:
        print("apps 폴더에 스캔 대상 파일이 없습니다.")
        sys.exit()
    for file in tqdm(file_List):
        fileLocation = f'./apps/{file}'

        command = f"curl -F \"malware_check=0\" -F \"hide_in_statistics=0\" -F \"file=@{fileLocation}\" \"https://www.immuniweb.com/mobile/api/upload\" --ssl-no-revoke" 
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        #print(result.stdout)
        command = f'python iwtools.py mobile --format colorized_text {fileLocation}'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        print(result.stdout)
        if 'Wrong' in result.stdout:
            print("오늘 스캔 가능한 횟수가 초과하였습니다.")
            sys.exit()
        #print(result.stdout)
        if result.returncode == 0:
            #print("result:" + str(result))
            url_list = re.findall(url_pattern, str(result.stdout))
            list_as_string = [element.strip() for element in url_list]
            list_as_string = ', '.join(url_list)
            list_as_string = resultStringReplace(list_as_string)
            result_url.append(list_as_string)
            #print(result_url)
        else:
            print("Command error")
        
def scan_result():
    for index in range(0,len(file_List)):
        print(f"{file_List[index]} Report URL : https://www.immuniweb.com{result_url[index]}")
        print("")



def downloadPDF():
    print("PDF Report Download Start")
    time.sleep(10)
    for index in tqdm(range(0, len(file_List))):
        DOWNPDF_URL = f"https://www.immuniweb.com{result_url[index]}"
        req = requests.get(DOWNPDF_URL, verify=False)
        html_content = req.text
    
        soup = BeautifulSoup(html_content, 'html.parser')
        title_tags = soup.find_all('title')
        package = ''
        for title_tag in title_tags:
            package = title_tag.text.split()[0]
            package_List.append(package)
    
        url = DOWNPDF_URL
        match = re.search(r"/([^/]+)/$", url)
        appKey = match.group(1)
        appkey_List.append(appKey)

        
        pdfDownUrl = f"https://www.immuniweb.com/mobile/api/v2/tests/{appKey}/pdf/{package}"
        downResponse = LOGIN_SESSION.get(pdfDownUrl, verify=False)
        if downResponse.status_code == 200:
            folder_path = './Reports'
            file_name = f"ImmuniWeb Mobile App Security Test Report - {file_List[index]}.pdf"
            file_path = os.path.join(folder_path, file_name)
            try:
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
            except OSError:
                print("Error: Creating directory. Reports" )
            with open(file_path, "wb") as file:
                file.write(downResponse.content)
            print("\n")
            print(f"File {file_name} downloaded successfully.")
        else:
            print("Error downloading the file.")

def deleteReport():
    global gsess
    global package_List
    global file_List
    print("DELETE REPORT Start")
  
    testids = []
    index = 0
    for appkey in tqdm(appkey_List):
        time.sleep(200)
        DELETE_URL = f"https://www.immuniweb.com/mobile/api/delete/id/{appkey}/{gsess}/"
        
        print(f"DELETE URL:{DELETE_URL}")
        response = LOGIN_SESSION.get(DELETE_URL, verify=False)

        if 'deleted' in response.text:
            print(f"{file_List[index]} Delete Successfully.")        
        
        else:
            print(f"{file_List[index]} Delete Fail")

        index = index + 1
        

if __name__=="__main__":
    login()
    scan()
    scan_result()
    downloadPDF()
    deleteReport()
