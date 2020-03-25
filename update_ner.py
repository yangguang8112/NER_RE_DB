from db import get_db
import json
from get_re_data import run_re
from bioNER import bioNER_run
import pandas as pd
import glob
from re import sub

from langdetect import detect
from langdetect import DetectorFactory
DetectorFactory.seed = 0

# 不加括号，适用之前的版本
ILLEGAL_CHAR = r'[\\/:*?"<>|\r\n\.]+'

def loads_xlsx(xlsx_file):
    df = pd.read_excel(xlsx_file)
    size = len(df)
    pdf_dir_path = xlsx_file.strip('.xlsx')
    for index in range(size):
        line = df.loc[index]
        title = line['title']
        author = line['author']
        qoute= line['qoute']
        pubtime = line['pubtime']
        downloaded = line['downloaded']
        url = line['url']
        keyword = line['keyword']
        if detect(title) != 'en':
            # 把原因记录下来
            continue
        if downloaded:
            pdf_name = sub(ILLEGAL_CHAR, '', title) + '.pdf'
            if pdf_name == 'Early respiratory and ocular involvement in X-linked hypohidrotic ectodermal dysplasia.pdf':
                continue
            tmp = glob.glob(pdf_dir_path+'/'+pdf_name)
            if tmp:
                pdf_path = tmp[0]
                ner_res = bioNER_run(pdf_path)
                return ner_res
            else:
                print(pdf_dir_path+'/'+pdf_name)
        else:
            ner_res = None
    print(ner_res)



def insert_paper(pdf_path):
    db = get_db()
    # 暂时用来做测试数据，真实情况是从pdf读取然后做ner
    raw = db.execute(
        'SELECT * FROM ner_result'
        ' WHERE id = 384'
    ).fetchall()[0]
    # 上面的raw应该从真实的excel中获取
    ner_res = bioNER_run(pdf_path)
    # 插入数据
    db.execute(
        'INSERT INTO paper (title, downloaded, paper_url, key_words, pdf_path, author, quate, pubtime, ner_res)'
        ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (raw['title'], raw['downloaded'], raw['paper_url'], raw['key_words'], raw['pdf_path'], raw['author'], raw['quate'], raw['pubtime'], json.dumps(ner_res))
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
    # 等下再写
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
    text = json.loads(ner_res)['text']
    #print(type(ner_res))
    re_res = run_re(ner_res, './instance/re_dir')
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

if __name__ == '__main__':
    #paperid = insert_paper('../BioExtract/instance/pdf/data/antimicrobial_peptide_gene_expression/Cutting_edge_1,_25-dihydroxyvitamin_D3_is_a_direct_inducer_of_antimicrobial_peptide_gene_expression.pdf')
    #print(paperid)
    #insert_ner(paperid)
    #insert_re(1)
    a = loads_xlsx('pdf_data/sample_pdf/ACAN-1/data/ACAN c821GA.xlsx')
    print(a)