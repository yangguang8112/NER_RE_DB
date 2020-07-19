from db import get_db
import json
#from nltk import sent_tokenize
import os
import sys
import scispacy
import spacy
import pandas as pd


def sentence_split(str_centence):
    nlp = spacy.load("en_core_sci_sm")
    doc = nlp(str_centence)
    sentence_list = [str(i) for i in list(doc.sents)]
    return sentence_list

def build_re_file(res_ner, test_path, re_type='gene-disease'):
    db = get_db()
    if res_ner == 'Nothing':
        print("no data")
        return
    res_ner = json.loads(res_ner)
    #tokens = sent_tokenize(res_ner['text'])
    # 这里有问题，用nltk会出现句号前有没有空格两种但是无法分辨导致后面index混乱，现在只用暴力分句会把很多句子分成两半
    full_text = res_ner['text']
    #print(full_text.find('Reference'))
    tokens = sentence_split(full_text)
    #print(res_ner['text'])
    denotations = res_ner['denotations']
    start, end = 0, 0
    text_dict = []
    for token in tokens:
        #print(end)
        #print(token)
        # 分句的过程中会除掉一些中间的空格，所以需要判断下一句的最开始是不是被去掉了
        while True:
            if token[0] == full_text[end]:
                start = end
                break
            end += 1
        end += len(token)
        #print(full_text[start:end])
        text_dict.append({'start':start,'end':end,'token':token,'flag':0})
    check_index = 0
    type_list = re_type.split('-')
    for ner in denotations:
        ner_obj = ner['obj']
        #if ner_obj not in ['disease', 'gene']:
        if ner_obj not in type_list:
            continue
        begin = ner['span']['begin']
        end = ner['span']['end']
        # check有溢出风险
        for text in text_dict[check_index:]:
            if begin in range(text['start'], text['end']):
                if end not in range(text['start'], text['end']):
                    # 暂时先不考虑这种情况
                    break
                # 没考虑有多个gene的情况
                text[ner_obj] = (begin, end)
                break
            else:
                check_index += 1
    test_file = open(test_path+'/test.tsv','w')
    rewrite_file = open(test_path+'/rewrite.txt','w')
    test_file.write("index\tsentence\n")
    index = 0
    for text in text_dict:
        #if 'gene' in text.keys() and 'disease' in text.keys():
        if type_list[0] in text.keys() and type_list[1] in text.keys():
            text['flag'] = 1
            token = text['token']
            start, end = text['start'], text['end']
            #gene_start, gene_end = text['gene']
            #d_start, d_end = text['disease']
            gene_start, gene_end = text[type_list[0]]
            d_start, d_end = text[type_list[1]]
            new_token = ''
            #if text['gene'] < text['disease']:
            if text[type_list[0]] < text[type_list[1]]:
                new_token = token[:gene_start-start] + '@GENE$' + token[gene_end-start:d_start-start] + '@DISEASE$' + token[d_end-start:]
            else:
                new_token = token[:d_start-start] + '@DISEASE$' + token[d_end-start:gene_start-start] + '@GENE$' + token[gene_end-start:]
            test_file.write("%d\t%s\n" % (index, new_token))
            # 添加ner的位置信息 ner name 和 ner location
            gene_name = token[gene_start-start:gene_end-start]
            diseas_name = token[d_start-start:d_end-start]
            rewrite_file.write("%d\t%d\t%d\t%s\t%d\t%d\t%s\t%d\t%d\n" % (index, start, end, gene_name, gene_start, gene_end, diseas_name, d_start, d_end))
            #print("%d\t%s" % (index, new_token))
            index += 1
    test_file.close()
    rewrite_file.close()
    return index

def run_re(res_ner, test_path, re_type='gene-disease'):
    check = build_re_file(res_ner, test_path, re_type=re_type)
    if not check:
        print("sssss")
        return
    re_script = './relation_extract/run_local.sh'
    os.system('sh %s %s' % (re_script, test_path))
    rewrite = open(test_path + '/rewrite.txt', 'r')
    test_res = open(test_path+'/test_results.tsv', 'r')
    rewrite_list = rewrite.readlines()
    test_list = test_res.readlines()
    re_res = []
    for i in range(len(test_list)):
        score = float(test_list[i].split('\t')[1])
        if score > 0.5:
            index = rewrite_list[i].strip('\n').split('\t')
            re_res.append({'start':int(index[1]), 'end':int(index[2]), 'score':score, 'obj':'RE',
                            'ner1':index[3], 'ner1_begin':int(index[4]), 'ner1_end':int(index[5]),
                            'ner2':index[6], 'ner2_begin':int(index[7]), 'ner2_end':int(index[8])})
    return re_res
    #print(re_res)
    '''
    db = get_db()
    ner_json = db.execute(
                'SELECT *'
                ' FROM ner_result'
                ' WHERE id = ?',
                (ner_id,)
                ).fetchone()
    res_ner = ner_json['json_res']
    res_ner = json.loads(res_ner)
    denotations = res_ner['denotations']
    check_index = 0
    for re_one in re_res:
        for deno in denotations[check_index:]:
            if re_one['start'] < deno['span']['begin']:
                ner1 = deno
                ner2 = denotations[check_index+1]
                re_one['ner'] = {ner1['obj']:(ner1['span']['begin'],ner1['span']['end']), ner2['obj']:(ner2['span']['begin'],ner2['span']['end'])}
                denotations.insert(check_index,re_one)
                check_index += 1
                break
            else:
                check_index += 1
               
    db.execute(
            'UPDATE ner_result SET json_res = ?'
            ' WHERE id = ?',
            (json.dumps(res_ner), ner_id)
            )
    db.commit()
    '''

def testGetdata(paper_id):
    db = get_db()
    paper_json = db.execute(
                'SELECT *'
                ' FROM paper'
                ' WHERE id = ?',
                (paper_id,)
                ).fetchone()
    res_ner = paper_json['ner_res']
    return res_ner
    


if __name__ == '__main__':
    ner_id = int(sys.argv[1])
    test_path = sys.argv[2]
    os.system('mkdir -p %s' % test_path)
    ner_res = testGetdata(ner_id)
    
    #print(ner_res)
    check = build_re_file(ner_res, test_path)
    if check:
        run_re(ner_res, test_path)