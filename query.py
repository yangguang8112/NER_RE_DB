from db import get_db
import json

#class Query_db(object):
#    def 

def query_paper(db_path, paper_ids=None):
    # 默认id为None即选中整个数据库，选中特定id需传入一个元组(20,30)即20到30之间的id
    db = get_db(db_path)
    if paper_ids:
        res = db.execute(
            'SELECT * FROM paper'
            ' WHERE id >= ? AND id <= ?',
            paper_ids
        ).fetchall()
    else:
        res = db.execute(
            'SELECT * FROM paper'
        ).fetchall()
    return [dict(i) for i in res]


def query_re(keyword):
    db = get_db()
    res = db.execute(
        'SELECT RE.*, paper.title FROM RE'
        ' LEFT JOIN paper on RE.paper_id = paper.id'
        ' WHERE ner1_name = ?'
        ' OR ner2_name = ?',
        (keyword, keyword)
    ).fetchall()
    if res:
        print('title|sentence')
        for resone in res:
            print(resone['title']+'|'+resone['re_content'])

def query_ner(keyword):
    db = get_db()
    res = db.execute(
        'SELECT NER.*, paper.title FROM NER'
        ' LEFT JOIN paper on NER.paper_id = paper.id'
        ' WHERE ner_name = ?',
        (keyword,)
    ).fetchall()
    if res:
        for resone in res:
            print(resone['id'])

if __name__ == '__main__':
    query_re('PDA')
    query_ner('c.506G>A')
