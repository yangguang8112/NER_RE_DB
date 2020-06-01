from db import get_db
import json
from get_re_data import run_re
from bioNER import bioNER_run
import pandas as pd
import numpy as np
import glob
from re import sub
import os

from langdetect import detect
from langdetect import DetectorFactory
DetectorFactory.seed = 0

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NpEncoder, self).default(obj)

# 不加括号，适用之前的版本
ILLEGAL_CHAR = r'[\\/:*?"<>|\r\n\.]+'

def from_sql(sql_file, pdf_data_path, log_path):
    error_info = []
    paper_ids = []
    input_db = get_db(sql_file)
    paper_list = input_db.execute(
            'SELECT * FROM paper'
        ).fetchall()
    #print(paper_list[0]['title'])
    db = get_db()
    for paper in paper_list:
        e_info = dict(paper)
        paper = dict(paper)
        check_repeat = db.execute(
            'SELECT * FROM paper'
            ' WHERE title = ? AND paper_url = ?',
            (paper['title'], paper['paper_url'])
        ).fetchone()
        if detect(paper['title']) != 'en':
            # 将paper信息加入error列表
            e_info['info'] = 'The paper is not english.'
            error_info.append(e_info)
            continue
        if check_repeat:
            e_info['info'] = 'This paper already exists in db.'
            error_info.append(e_info)
            continue
        if paper['downloaded'] == 'True':
            pdf_file = os.path.join(pdf_data_path, paper['pdf_path'].split('/data/')[1])
            if os.path.exists(pdf_file):
                print("running ner for :" + pdf_file)
                paper['pdf_path'] = pdf_file
                ner_res = bioNER_run(pdf_file)
                if ner_res == "PDF damage":
                    e_info['info'] = 'PDF damage'
                    error_info.append(e_info)
                    continue
                elif ner_res:
                    paper['ner_res'] = json.dumps(ner_res)
                    # 插入数据库
                    paper_id = insert_paper(paper)
                    paper_ids.append(paper_id)
                else:
                    print("NER error please check paper or program")
                    e_info['info'] = 'NER error'
                    error_info.append(e_info)
            else:
                print("Warning:NOT FOUND "+pdf_file)
                e_info['info'] = 'Not found the pdf file'
                error_info.append(e_info)
    error_info = json.dumps(error_info, cls=NpEncoder)
    with open(log_path+'/log.json', 'w') as lj:
        lj.write(error_info)
    with open(log_path + '/paper.ids','w') as pi:
        pi.write(json.dumps(paper_ids))
    return paper_ids
    

def loads_xlsx(xlsx_file, log_path):
    error_info = []
    paper_ids = []
    df = pd.read_excel(xlsx_file)
    size = len(df)
    pdf_dir_path = xlsx_file.strip('.xlsx')
    logname = xlsx_file.strip('.xlsx').split('/')[-1]
    db = get_db()
    for index in range(size):
        line = df.loc[index]
        line_dict = dict(line)
        if line_dict['downloaded']:
            line_dict['downloaded'] = 1
        else:
            line_dict['downloaded'] = 0
        title = line['title']
        author = line['author']
        qoute= line['qoute']
        pubtime = line['pubtime']
        downloaded = line['downloaded']
        url = line['url']
        keyword = line['keyword']
        e_info = dict(line)
        if e_info['downloaded']:
            e_info['downloaded'] = 1
        else:
            e_info['downloaded'] = 0
        if detect(title) != 'en':
            # 将paper信息加入error列表
            e_info['info'] = 'The paper is not english.'
            error_info.append(e_info)
            continue
        check_repeat = db.execute(
            'SELECT * FROM paper'
            ' WHERE title = ? AND paper_url = ?',
            (title, url)
        ).fetchone()
        if check_repeat:
            e_info['info'] = 'This paper already exists in db.'
            error_info.append(e_info)
            continue
        if downloaded:
            # NER
            pdf_name = sub(ILLEGAL_CHAR, '', title) + '.pdf'
            if pdf_name == 'Early respiratory and ocular involvement in X-linked hypohidrotic ectodermal dysplasia.pdf':
                continue
            tmp = glob.glob(pdf_dir_path+'/'+pdf_name)
            if tmp:
                pdf_path = tmp[0]
                ner_res = bioNER_run(pdf_path)
                if ner_res == "PDF damage":
                    e_info['info'] = 'PDF damage'
                    error_info.append(e_info)
                    continue
                elif ner_res:
                    line_dict['pdf_path'] = pdf_path
                    line_dict['ner_res'] = json.dumps(ner_res)
                    # 插入数据库
                    paper_id = insert_paper(line_dict)
                    paper_ids.append(paper_id)
                else:
                    print("NER error please check paper or program")
                    e_info['info'] = 'NER error'
                    error_info.append(e_info)
            else:
                print("Warning:NOT FOUND "+pdf_dir_path+'/'+pdf_name)
                e_info['info'] = 'Not found the pdf file'
                error_info.append(e_info)
    error_info = json.dumps(error_info, cls=NpEncoder)
    with open(log_path+'/'+logname+'_log.json', 'w') as lj:
        lj.write(error_info)
    with open(log_path + '/'+logname+'_paper.ids','w') as pi:
        pi.write(json.dumps(paper_ids))
    return paper_ids



def insert_paper(p_info):
    db = get_db()
    # 插入数据
    db.execute(
        'INSERT INTO paper (title, downloaded, paper_url, key_words, pdf_path, author, quote, pubtime, ner_res)'
        ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        # excel 中quote写错
        #(p_info['title'], p_info['downloaded'], p_info['url'], p_info['keyword'], p_info['pdf_path'], p_info['author'], p_info['qoute'], p_info['pubtime'], p_info['ner_res'])
        (p_info['title'], p_info['downloaded'], p_info['paper_url'], p_info['key_words'], p_info['pdf_path'], p_info['author'], p_info['quote'], p_info['pubtime'], p_info['ner_res'])
    )
    db.commit()
    # 此方法返回id查询效率低，是通过比较所有数据得到的结果，另外无法做并发，是全局的max
    paper_id = db.execute(
        'select max(id) FROM paper'
    ).fetchone()
    return paper_id[0]

def insert_ner(paper_id):
    db = get_db()
    ner_res = db.execute(
        'SELECT ner_res FROM paper'
        ' WHERE id = ?',
        (paper_id,)
    ).fetchone()[0]
    if len(ner_res) < 100:
        print(paper_id, ner_res)
        return
    if ner_res == '[{"error": "empty text"}]':
        return
    ner_res = json.loads(ner_res)
    text = ner_res['text']
    denotations = ner_res['denotations']
    for ner_item in denotations:
        ner_type = ner_item['obj']
        ner_begin = ner_item['span']['begin']
        ner_end = ner_item['span']['end']
        ner_name = text[ner_begin:ner_end]
        db.execute(
            'INSERT INTO NER (ner_name, ner_type, ner_begin, ner_end, paper_id)'
            ' VALUES (?, ?, ?, ?, ?)',
            (ner_name, ner_type, ner_begin, ner_end, paper_id)
            )
        db.commit()
    return


def insert_re(paper_id):
    db = get_db()
    ner_res = db.execute(
        'SELECT ner_res FROM paper'
        ' WHERE id = ?',
        (paper_id,)
    ).fetchone()[0]
    if ner_res == '[{"error": "empty text"}]':
        return
    text = json.loads(ner_res)['text']
    #print(type(ner_res))
    re_res = run_re(ner_res, './instance/re_dir')
    if not re_res:
        print("paper %d no gene-disease" % paper_id)
        return
    re_type = 'gene-disease'
    
    for re_item in re_res:
        re_begin = re_item['start']
        re_end = re_item['end']
        re_content = text[re_begin:re_end]
        ner1_name = re_item['ner1']
        ner2_name = re_item['ner2']
        ner1_id = db.execute(
            'SELECT id FROM NER'
            ' WHERE paper_id = ? AND ner_begin = ? AND ner_name = ?',
            (paper_id, re_item['ner1_begin'], ner1_name)
        ).fetchone()[0]
        ner2_id = db.execute(
            'SELECT id FROM NER'
            ' WHERE paper_id = ? AND ner_begin = ? AND ner_name = ?',
            (paper_id, re_item['ner2_begin'], ner2_name)
        ).fetchone()[0]

        db.execute(
            'INSERT INTO RE (re_type, re_content, ner1_id, ner1_name, ner2_name, ner2_id, re_begin, re_end, paper_id)'
            ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (re_type, re_content, ner1_id, ner1_name, ner2_name, ner2_id, re_begin, re_end, paper_id)
            )
        db.commit()
    
    return re_res



def run_ner_re(paper_ids_file):
    with open(paper_ids_file, 'r') as pif:
        paper_ids = json.loads(pif.read())
    for paper_id in paper_ids:
        insert_ner(paper_id)
        insert_re(paper_id)

def run_re_db(paper_ids_file):
    with open(paper_ids_file, 'r') as pif:
        paper_ids = json.loads(pif.read())
    #paper_ids = [331,332,334]
    for paper_id in paper_ids:
        insert_re(paper_id)
    

if __name__ == '__main__':
    #paperid = insert_paper('../BioExtract/instance/pdf/data/antimicrobial_peptide_gene_expression/Cutting_edge_1,_25-dihydroxyvitamin_D3_is_a_direct_inducer_of_antimicrobial_peptide_gene_expression.pdf')
    #print(paperid)
    #insert_ner(paperid)
    #insert_re(1)
    #a = loads_xlsx('pdf_data/sample_pdf/ACAN-1/data/ACAN c821GA.xlsx')
    #print(a)
    import sys
    xlsx_file = sys.argv[1]
    log_path = sys.argv[2]
    paperids = loads_xlsx(xlsx_file, log_path)
