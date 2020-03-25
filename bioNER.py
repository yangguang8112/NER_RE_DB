import requests
import json
import os
#import pdfminer.high_level.extract_text as pdf2txt

def txtFormat(rawtxt):
    # rawtxt为readlines的list
    length = len(rawtxt)
    #print(rawtxt)
    cleantxt = []
    section = ''
    flag = 1
    for i in range(length-1):
        # 先保守把十个字符以下的行去掉
        if len(rawtxt[i]) < 10:
            continue
        if rawtxt[i] == '' or rawtxt[i] == '\n':
            continue
        if rawtxt[i+1] == '' or rawtxt[i+1] == '\n':
            section += rawtxt[i]
            cleantxt.append(section)
            section = ''
            flag = 0
            continue
        section += rawtxt[i].strip('\n') + ' '
        flag = 1
    if flag == 1:
        section += rawtxt[-1]
        cleantxt.append(section)
    return "".join(cleantxt)

# 确保本地服务已开启
def query_raw(text, url="http://localhost:8888"):
    print("laile")
    body_data = {"param": json.dumps({"text": text})}
    try:
        return requests.post(url, data=body_data).json()
    except:
        return

def bioNER_run(pdf_file):
    #rawtxt = os.popen('pdf2txt.py -d %s' % pdf_file).read()
    try:
        #print("pdf2txt.py '%s'" % pdf_file)
        #rawtxt = pdf2txt(pdf_file)
        rawtxt = os.popen("pdf2txt.py '%s'" % pdf_file).read()
    except:
        return "PDF damage"
    cleantxt = txtFormat(rawtxt.split('\n'))
    return query_raw(cleantxt)



if __name__ == '__main__':
    import sys
    pdf_file = sys.argv[1]
    rawtxt = os.popen('pdf2txt.py -d %s' % pdf_file).read()
    cleantxt = txtFormat(rawtxt.split('\n'))
    print(bioNER_run(pdf_file))
