from db import get_db
import json
#from nltk import sent_tokenize
import os
import sys

def sentence_split(str_centence):
    list_ret = list()
    for s_str in str_centence.split('.'):
        if '?' in s_str:
            list_ret.extend(s_str.split('?'))
        elif '!' in s_str:
            list_ret.extend(s_str.split('!'))
        else:
            list_ret.append(s_str)
    return list_ret

def build_re_file(res_ner, test_path):
    db = get_db()
    if res_ner == 'Nothing':
        return
    res_ner = json.loads(res_ner)
    #tokens = sent_tokenize(res_ner['text'])
    # 这里有问题，用nltk会出现句号前有没有空格两种但是无法分辨导致后面index混乱，现在只用暴力分句会把很多句子分成两半
    tokens = sentence_split(res_ner['text'])
    denotations = res_ner['denotations']
    start, end = 0, 0
    text_dict = []
    for token in tokens:
        start = end
        # 这里因为前面的nltk分句把每个句子前的空格给去掉了,所以加回来
        end += len(token) + 1
        text_dict.append({'start':start,'end':end,'token':token,'flag':0})
    check_index = 0
    for ner in denotations:
        ner_obj = ner['obj']
        if ner_obj not in ['disease', 'gene']:
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
        if 'gene' in text.keys() and 'disease' in text.keys():
            text['flag'] = 1
            token = text['token']
            start, end = text['start'], text['end']
            gene_start, gene_end = text['gene']
            d_start, d_end = text['disease']
            new_token = ''
            if text['gene'] < text['disease']:
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

def run_re(res_ner, test_path):
    check = build_re_file(res_ner, test_path)
    if not check:
        return
    re_script = './relation_extract/run.sh'
    os.system('sh %s %s' % (re_script, test_path))
    rewrite = open(test_path + '/rewrite.txt', 'r')
    test_res = open(test_path+'/test_results.tsv', 'r')
    rewrite_list = rewrite.readlines()
    test_list = test_res.readlines()
    re_res = []
    for i in range(len(test_list)):
        score = float(test_list[i].split('\t')[0])
        if score > 0.9:
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
    


if __name__ == '__main__':
    ner_id = int(sys.argv[1])
    test_path = sys.argv[2]
    os.system('mkdir -p %s' % test_path)
    check = build_re_file(ner_id, test_path)
    if check:
        run_re(ner_id, test_path)