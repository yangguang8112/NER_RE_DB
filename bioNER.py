import requests
import json
import os

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


def query_raw(text, url="http://localhost:8888"):
    try:
        return requests.post(url, data={'sample_text': text}, timeout=180).json()
    except:
        return

def bioNER_run(pdf_file):
    rawtxt = os.popen('pdf2txt.py -d %s' % pdf_file).read()
    cleantxt = txtFormat(rawtxt.split('\n'))
    #print(cleantxt)
    return query_raw(cleantxt)



if __name__ == '__main__':
    import sys
    pdf_file = sys.argv[1]
    rawtxt = os.popen('pdf2txt.py -d %s' % pdf_file).read()
    cleantxt = txtFormat(rawtxt.split('\n'))
    print(bioNER_run(pdf_file))
