import json
from db import get_db
from update_ner import insert_paper, insert_ner
import os
import sys

#listfile = './paper_info.list'
#hash_path = '/mnt/d/Data/z.R.scholar/jieguo_biobert/'

listfile = sys.argv[1]
hash_path = sys.argv[2]

with open(listfile, 'r') as lf:
    paper_info = json.loads(lf.read())

db = get_db()
for paper in paper_info:
    check_repeat = db.execute(
            'SELECT * FROM paper'
            ' WHERE title = ? AND paper_url = ?',
            (paper['title'], paper['paper_url'])
        ).fetchone()
    if not check_repeat:
        hash_file = hash_path + '/bern_demo_' + paper['ner_res'] + '.json'
        if os.path.exists(hash_file):
            with open(hash_file, 'r') as hf:
                paper['ner_res'] = hf.read()
        paper_id = insert_paper(paper)
        # 插入ner结果
        insert_ner(paper_id)


print(paper_id)



