from db import get_db
import json

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



if __name__ == '__main__':
    query_re('PDA')
