from biobert_ner.run_ner import BioBERT, FLAGS
from convert import pubtator2dict_list, pubtator_biocxml2dict_list, \
    get_pub_annotation, get_pubtator
from utils import filter_entities
from normalize import Normalizer

from datetime import datetime
import random
import numpy as np
import json
import string
import time
import tensorflow as tf
import threading
import hashlib
import os
import glob
from pdfminer.high_level import extract_text as pdf2txt
from bioNER import txtFormat
from query import query_paper


def get_pdf_rawdata(pdf_file, maxpages=15):
    raw_text = pdf2txt(pdf_file, maxpages=maxpages)
    raw_text = txtFormat(raw_text.split("\n"))
    return raw_text

class NER(object):
    stm_dict = None
    normalizer = None

    def run_pipeline(self, db_path, pdf_data_path):
        cur_thread_name = threading.current_thread().getName()
        # 准备写批量的
        # 初步准备用数据库，输入数据库地址和要处理的id段默认全部，先批量把pdf转成文本putator格式存到第一个的输入目录里
        paper_info = query_paper(db_path, paper_ids=(4,6))
        # 没有判断去重复
        for paper in paper_info:
            if paper['downloaded'] == 'True':
                pdf_file = os.path.join(pdf_data_path, paper['pdf_path'].split('/data/')[1])
                if os.path.exists(pdf_file):
                    paper['pdf_path'] = pdf_file
                    # run pdf2txt text2pub 将paper转化成pub格式存在Gnorm的输入目录下，并返回hash村到paper list里
                    try:
                        raw_text = get_pdf_rawdata(pdf_file)
                    except:
                        print(pdf_file)
                        print("此pdf损坏")
                        paper['ner_res'] = "PDF damage"
                        continue
                    text = self.preprocess_input(raw_text, cur_thread_name)
                    text_hash = self.text2pub(text, cur_thread_name)
                    paper['ner_res'] = text_hash
                else:
                    print("严重错误 找不到pdf文件")
                    return
        #print(paper_info)
        # 开始跑tagger
        result_dict = self.tag_entities(
            cur_thread_name, is_raw_text=True, reuse=False)
        # 使用paper_info找到bern的结果后插入到数据库中
        return paper_info
    
    def preprocess_input(self, text, cur_thread_name):
        if '\n' in text:
            print(datetime.now().strftime(self.stm_dict['time_format']),
                  '[{}] Found a line break -> replace w/ a space'
                  .format(cur_thread_name))
            text = text.replace('\n', ' ')

        if '\t' in text:
            print(datetime.now().strftime(self.stm_dict['time_format']),
                  '[{}] Found a tab -> replace w/ a space'
                  .format(cur_thread_name))
            text = text.replace('\t', ' ')

        found_too_long_words = 0
        tokens = text.split(' ')
        for idx, tk in enumerate(tokens):
            if len(tk) > self.stm_dict['max_word_len']:
                tokens[idx] = tk[:self.stm_dict['max_word_len']]
                found_too_long_words += 1
        if found_too_long_words > 0:
            print(datetime.now().strftime(self.stm_dict['time_format']),
                  '[{}] Found a too long word -> cut the suffix of the word'
                  .format(cur_thread_name))
            text = ' '.join(tokens)

        return text
    
    def text2pub(self, text, cur_thread_name):
        n_ascii_letters = 0
        for l in text:
            if l not in string.ascii_letters:
                continue
            n_ascii_letters += 1

        if n_ascii_letters == 0:
            text = 'No ascii letters. Please enter your text in English.'

        text_hash = hashlib.sha224(text.encode('utf-8')).hexdigest()
        print(datetime.now().strftime(self.stm_dict['time_format']),
              '[{}] text_hash: {}'.format(cur_thread_name, text_hash))
        
        home_gnormplus = self.stm_dict['gnormplus_home']
        input_gnormplus = os.path.join(home_gnormplus, 'input',
                                       '{}.PubTator'.format(text_hash))

        # Write input str to a .PubTator format file
        with open(input_gnormplus, 'w', encoding='utf-8') as f:
            # only title
            f.write(text_hash + '|t|')
            f.write('\n')
            f.write(text_hash + '|a|' + text + '\n\n')

        return text_hash
    
    def tag_entities(self, cur_thread_name, is_raw_text, reuse=False):
        assert self.stm_dict is not None
        get_start_t = time.time()
        elapsed_time_dict = dict()

        home_gnormplus = self.stm_dict['gnormplus_home']
        input_gnormplus = os.path.join(home_gnormplus, 'input')
        output_gnormplus = os.path.join(home_gnormplus, 'output')

        home_tmvar2 = self.stm_dict['tmvar2_home']
        input_dir_tmvar2 = os.path.join(home_tmvar2, 'input')
        input_tmvar2 = os.path.join(input_dir_tmvar2)
        output_tmvar2 = os.path.join(home_tmvar2, 'output')
        
        # Run GNormPlus
        gnormplus_start_time = time.time()
        # 这里肯定要修改================================================
        shell_script = '''cd GNormPlusJava;java -Xmx12G -Xms12G -jar GNormPlus.jar input output setup.txt;cd -;'''# % (input_gnormplus, output_gnormplus)
        print(shell_script)
        os.system(shell_script)
        gnormplus_time = time.time() - gnormplus_start_time
        elapsed_time_dict['gnormplus'] = round(gnormplus_time, 3)
        print(datetime.now().strftime(self.stm_dict['time_format']),
              '[{}] GNormPlus {:.3f} sec'
              .format(cur_thread_name, gnormplus_time))
        
        # GNorm的输出作为tmVar的输入，其实上面和下面的命令里已经都写死了
        input_tmvar2 = output_gnormplus

        # Run tmVar 2.0
        tmvar2_start_time = time.time()
        # 这里肯定要修改================================================
        shell_script = '''cd tmVarJava; java -Xmx12G -Xms12G -jar tmVar.jar ../GNormPlusJava/input output; cd -;'''# % (input_tmvar2, output_tmvar2)
        os.system(shell_script)
        tmvar2_time = time.time() - tmvar2_start_time
        elapsed_time_dict['tmvar2'] = round(tmvar2_time, 3)
        print(datetime.now().strftime(self.stm_dict['time_format']),
              '[{}] tmVar 2.0 {:.3f} sec'
              .format(cur_thread_name, tmvar2_time))
        
        # Convert tmVar 2.0 outputs (?.PubTator.PubTator) to python dict
        file_list = glob.glob(output_tmvar2+"/*.PubTator.PubTator")
        dict_list = [pubtator2dict_list(i, is_raw_text=True) for i in file_list]

        # 至此所有的结果已经到dict_list了

        # Run BioBERT of Lee et al., 2019
        ner_start_time = time.time()
        # 这里设为False会报错
        is_raw_text = True
        tagged_docs_list = []
        for dict_l in dict_list:
            tagged_docs, num_entities = \
                biobert_recognize(self.stm_dict,dict_l, is_raw_text, cur_thread_name)
            tagged_docs_list.append((tagged_docs, num_entities))
        if tagged_docs_list is None:
            return None

        ner_time = time.time() - ner_start_time
        elapsed_time_dict['ner'] = round(ner_time, 3)
        print(datetime.now().strftime(self.stm_dict['time_format']),
              '[%s] NER %.3f sec, #entities: %d' %
              (cur_thread_name, ner_time, num_entities))
        #print(tagged_docs_list)
        #with open("ceshi_normllllll.list",'w') as ceshide:
        #    ceshide.write(json.dumps(tagged_docs_list))
        #return
        
        #for tagged_docs in tagged_docs_list:
        #    if tagged_docs is None:
        #        return None
        #    assert len(tagged_docs) == 1

        # Normalization models
        # 这里需要把load_dict.sh里的三个python脚本和两个jar全部run起来才跑的通
        os.system('sh load_dicts.sh')
        normalization_time = 0.
        new_tagged_docs_list = []
        for tagged_docs, num_entities in tagged_docs_list:
            if tagged_docs is None:
                continue
            text_hash = tagged_docs[0]['pmid']
            if num_entities > 0:
                normalization_start_time = time.time()
                tagged_docs = self.normalizer.normalize(text_hash, tagged_docs,
                                                        cur_thread_name,
                                                        is_raw_text=is_raw_text)
                normalization_time = time.time() - normalization_start_time
            elapsed_time_dict['normalization'] = round(normalization_time, 3)
            # Convert to PubAnnotation JSON
            elapsed_time_dict['total'] = round(time.time() - get_start_t, 3)
            tagged_docs[0] = get_pub_annotation(tagged_docs[0],
                                                is_raw_text=is_raw_text,
                                                elapsed_time_dict=elapsed_time_dict)
            new_tagged_docs_list.append(tagged_docs[0])
            # Save a BERN result
            bern_output_path = './output/bern_demo_{}.json'.format(text_hash)
            if reuse and os.path.exists(bern_output_path):
                print(datetime.now().strftime(self.stm_dict['time_format']),
                    '[{}] Found prev. output'.format(cur_thread_name))
                with open(bern_output_path, 'r', encoding='utf-8') as f_out:
                    return json.load(f_out)
            with open(bern_output_path, 'w', encoding='utf-8') as f_out:
                json.dump(tagged_docs[0], f_out, sort_keys=True)

        return tagged_docs[0]

def ceshi_run(stm_dict):
    #output_tmvar2 = 'tmVarJava/output/ceshi.txt.PubTator'
    output_tmvar2 = 'tmVarJava/output/29848cb18c2db29141bae9c5f7cc97b1d5175f4960eed341cca78cd9.PubTator.PubTator'
    dict_list = pubtator2dict_list(output_tmvar2, is_raw_text=True)
    is_raw_text, cur_thread_name = True, threading.current_thread().getName()
    ner_start_time = time.time()
    tagged_docs, num_entities = biobert_recognize(stm_dict, dict_list, is_raw_text, cur_thread_name)
    ner_time = time.time() - ner_start_time
    print(datetime.now().strftime(stm_dict['time_format']),
              '[%s] NER %.3f sec, #entities: %d' %
              (cur_thread_name, ner_time, num_entities))
    return (tagged_docs, num_entities)


def biobert_recognize(stm_dict, dict_list, is_raw_text, cur_thread_name):
        res = stm_dict['biobert'].recognize(dict_list,
                                                 is_raw_text=is_raw_text,
                                                 thread_id=cur_thread_name)
        if res is None:
            print("dao zhe lai le##################")
            return None, 0

        num_filtered_species_per_doc = filter_entities(res, is_raw_text)
        for n_f_spcs in num_filtered_species_per_doc:
            if len(n_f_spcs) < 2:
                # list溢出不是这里的问题
                print("物种统计出了问题")
                continue
            if n_f_spcs[1] > 0:
                print(datetime.now().strftime(stm_dict['time_format']),
                      '[{}] Filtered {} species{}'
                      .format(cur_thread_name, n_f_spcs[1],
                              '' if is_raw_text
                              else ' in PMID:%s' % n_f_spcs[0]))
        num_entities = count_entities(res)
        return res, num_entities



def count_entities(data):
    num_entities = 0
    for d in data:
        if 'entities' not in d:
            continue
        doc_ett = d['entities']
        num_entities += len(doc_ett['gene'])
        num_entities += len(doc_ett['disease'])
        num_entities += len(doc_ett['drug'])
        num_entities += len(doc_ett['species'])
        if 'mutation' in doc_ett:
            num_entities += len(doc_ett['mutation'])
    return num_entities

def delete_files(dirname):
    if not os.path.exists(dirname):
        return

    for f in os.listdir(dirname):
        f_path = os.path.join(dirname, f)
        if not os.path.isfile(f_path):
            continue
        print('Delete', f_path)
        os.remove(f_path)

class Main:
    def __init__(self, params):
        print(datetime.now().strftime(params.time_format), 'Starting..')
        # os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # verbose off(info, warning)
        random.seed(params.seed)
        np.random.seed(params.seed)
        tf.set_random_seed(params.seed)

        print("A GPU is{} available".format(
            "" if tf.test.is_gpu_available() else " NOT"))

        stm_dict = dict()
        stm_dict['params'] = params

        FLAGS.model_dir = './biobert_ner/pretrainedBERT/'
        FLAGS.bert_config_file = './biobert_ner/conf/bert_config.json'
        FLAGS.vocab_file = './biobert_ner/conf/vocab.txt'
        FLAGS.init_checkpoint = \
            './biobert_ner/pretrainedBERT/pubmed_pmc_470k/biobert_model.ckpt'

        FLAGS.ip = params.ip
        FLAGS.port = params.port

        FLAGS.gnormplus_home = params.gnormplus_home
        FLAGS.gnormplus_host = params.gnormplus_host
        FLAGS.gnormplus_port = params.gnormplus_port

        FLAGS.tmvar2_home = params.tmvar2_home
        FLAGS.tmvar2_host = params.tmvar2_host
        FLAGS.tmvar2_port = params.tmvar2_port

        # import pprint
        # pprint.PrettyPrinter().pprint(FLAGS.__flags)

        stm_dict['biobert'] = BioBERT(FLAGS)

        stm_dict['gnormplus_home'] = params.gnormplus_home
        stm_dict['gnormplus_host'] = params.gnormplus_host
        stm_dict['gnormplus_port'] = params.gnormplus_port

        stm_dict['tmvar2_home'] = params.tmvar2_home
        stm_dict['tmvar2_host'] = params.tmvar2_host
        stm_dict['tmvar2_port'] = params.tmvar2_port

        stm_dict['max_word_len'] = params.max_word_len
        stm_dict['ner_model'] = params.ner_model
        stm_dict['n_pmid_limit'] = params.n_pmid_limit
        stm_dict['time_format'] = params.time_format
        stm_dict['available_formats'] = params.available_formats

        if not os.path.exists('./output'):
            os.mkdir('output')
        else:
            # delete prev. version outputs
            delete_files('./output')

        #delete_files(os.path.join(params.gnormplus_home, 'input'))
        #delete_files(os.path.join(params.tmvar2_home, 'input'))
        #ceshi_pdf = '/home/yg/work/BioNLP/NER_RE_DB/pdf_data/z.R.scholar/data/rs993419_DNMT3B/A_new_and_a_reclassified_ICF_patient_without_mutations_in_DNMT3B_and_its_interacting_proteins_SUMO‐1_and_UBC9.pdf'
        ner = NER()
        ner.stm_dict = stm_dict
        ner.normalizer = Normalizer()
        input_db_path = '/home/yg/work/BioNLP/NER_RE_DB/pdf_data/z.R.scholar/instance/paper.sqlite'
        pdf_data_path = '/home/yg/work/BioNLP/NER_RE_DB/pdf_data/z.R.scholar/data'
        res = ner.run_pipeline(input_db_path, pdf_data_path)
        stm_dict['biobert'].close()
        return

        print("任务开始")
        res = ceshi_run(stm_dict)
        print('以下是本次测试的结果:')
        print(res)
        stm_dict['biobert'].close()

        

if __name__ == '__main__':
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument('--ip', default='0.0.0.0')
    argparser.add_argument('--port', type=int, default=8888)
    argparser.add_argument('--ner_model', default='BioBERT')
    argparser.add_argument('--max_word_len', type=int, help='word max chars',
                           default=50)
    argparser.add_argument('--seed', type=int, help='seed value', default=2019)

    argparser.add_argument('--gnormplus_home',
                           help='GNormPlus home',
                           default=os.path.join('GNormPlusJava'))
    argparser.add_argument('--gnormplus_host',
                           help='GNormPlus host', default='localhost')
    argparser.add_argument('--gnormplus_port', type=int,
                           help='GNormPlus port', default=18895)
    argparser.add_argument('--tmvar2_home',
                           help='tmVar 2.0 home',
                           default=os.path.join('tmVarJava'))
    argparser.add_argument('--tmvar2_host',
                           help='tmVar 2.0 host', default='localhost')
    argparser.add_argument('--tmvar2_port', type=int,
                           help='tmVar 2.0 port', default=18896)

    argparser.add_argument('--n_pmid_limit', type=int,
                           help='max # of pmids', default=10)
    argparser.add_argument('--available_formats', type=list,
                           help='output formats', default=['json', 'pubtator'])
    argparser.add_argument('--time_format',
                           help='time format', default='[%d/%b/%Y %H:%M:%S.%f]')

    args = argparser.parse_args()

    Main(args)
