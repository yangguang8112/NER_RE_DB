import requests
import json
import os
#from pdfminer.high_level import extract_text as pdf2txt

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
            section += rawtxt[i].strip()
            cleantxt.append(section)
            section = ''
            flag = 0
            continue
        section += rawtxt[i].strip('\n').strip() + ' '
        flag = 1
    if flag == 1:
        section += rawtxt[-1]
        cleantxt.append(section)
    return "".join(cleantxt)

# 确保本地服务已开启
def query_raw(text, url="http://localhost:8888"):
    print("Runing NER")
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
        rawtxt = os.popen("pdf2txt.py -m 15 '%s'" % pdf_file).read()
    except:
        return "PDF damage"
    #print("get raw")
    cleantxt = txtFormat(rawtxt.split('\n'))
    #print("get_clean")
    return query_raw(cleantxt)



if __name__ == '__main__':
    import sys
    pdf_file = sys.argv[1]
    rawtxt = os.popen('pdf2txt.py -d %s' % pdf_file).read()
    cleantxt = txtFormat(rawtxt.split('\n'))
    #print(cleantxt)
    nlp = spacy.load("en_core_sci_sm")
    senten = nlp(cleantxt)
    #a = list(senten.sents)
    a = [str(i) for i in senten.sents]
    he = "".join(a)
    b = list(nlp(he).sents)
    b = [str(i) for i in b]
    print((len(a),len(b)))
    c = cleantxt.split(". ")
    print(len(c))
    '''
    for i in range(len(a)):
        if a[i] != b[i]:
            print(a[i])
            print("++++++++++++++++++++")
            print(b[i])
    
    if a == b:
        print("shi dui de")
    else:
        print(type(a[0]))
        print(type(b[0]))
        print("xing bu tong")
        print(a[:5])
        print("++++++++++++++++++++")
        print(b[:5])
'''
