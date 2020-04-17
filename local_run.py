from biobert_ner.run_ner import BioBERT, FLAGS
from convert import pubtator2dict_list, pubtator_biocxml2dict_list, \
    get_pub_annotation, get_pubtator
from utils import filter_entities

from datetime import datetime
import random
import numpy as np
import json
import time
import tensorflow as tf
import threading
import os

def ceshi_run(stm_dict):
    output_tmvar2 = 'tmVarJava/output/ceshi.txt.PubTator'
    dict_list = pubtator2dict_list(output_tmvar2, is_raw_text=True)
    is_raw_text, cur_thread_name = True, threading.current_thread().getName()
    res = biobert_recognize(stm_dict, dict_list, is_raw_text, cur_thread_name)
    return res


def biobert_recognize(stm_dict, dict_list, is_raw_text, cur_thread_name):
        res = stm_dict['biobert'].recognize(dict_list,
                                                 is_raw_text=is_raw_text,
                                                 thread_id=cur_thread_name)
        if res is None:
            return None, 0

        num_filtered_species_per_doc = filter_entities(res, is_raw_text)
        for n_f_spcs in num_filtered_species_per_doc:
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

        delete_files(os.path.join(params.gnormplus_home, 'input'))
        delete_files(os.path.join(params.tmvar2_home, 'input'))

        print(datetime.now().strftime(params.time_format),
              'Starting server at http://{}:{}'.format(params.ip, params.port))
        print(ceshi_run(stm_dict))

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
                           default=os.path.join(os.path.expanduser('~'),
                                                'bern', 'GNormPlusJava'))
    argparser.add_argument('--gnormplus_host',
                           help='GNormPlus host', default='localhost')
    argparser.add_argument('--gnormplus_port', type=int,
                           help='GNormPlus port', default=18895)
    argparser.add_argument('--tmvar2_home',
                           help='tmVar 2.0 home',
                           default=os.path.join(os.path.expanduser('~'),
                                                'bern', 'tmVarJava'))
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
