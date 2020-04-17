from biobert_ner.run_ner import BioBERT, FLAGS
from convert import pubtator2dict_list, pubtator_biocxml2dict_list, \
    get_pub_annotation, get_pubtator


class RunNER(object):

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

    def tag_entities(self, text, cur_thread_name, is_raw_text, reuse=False):
        assert self.stm_dict is not None
        get_start_t = time.time()
        elapsed_time_dict = dict()
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

        bern_output_path = './output/bern_demo_{}.json'.format(text_hash)

        if reuse and os.path.exists(bern_output_path):
            print(datetime.now().strftime(self.stm_dict['time_format']),
                  '[{}] Found prev. output'.format(cur_thread_name))
            with open(bern_output_path, 'r', encoding='utf-8') as f_out:
                return json.load(f_out)

        home_gnormplus = self.stm_dict['gnormplus_home']
        input_gnormplus = os.path.join(home_gnormplus, 'input',
                                       '{}.PubTator'.format(text_hash))
        output_gnormplus = os.path.join(home_gnormplus, 'output',
                                        '{}.PubTator'.format(text_hash))

        home_tmvar2 = self.stm_dict['tmvar2_home']
        input_dir_tmvar2 = os.path.join(home_tmvar2, 'input')
        input_tmvar2 = os.path.join(input_dir_tmvar2,
                                    '{}.PubTator'.format(text_hash))
        output_tmvar2 = os.path.join(home_tmvar2, 'output',
                                     '{}.PubTator.PubTator'.format(text_hash))

        # Write input str to a .PubTator format file
        with open(input_gnormplus, 'w', encoding='utf-8') as f:
            # only title
            f.write(text_hash + '|t|')
            f.write('\n')
            f.write(text_hash + '|a|' + text + '\n\n')

        # Run GNormPlus
        gnormplus_start_time = time.time()
        tell_inputfile(self.stm_dict['gnormplus_host'],
                       self.stm_dict['gnormplus_port'],
                       '{}.PubTator'.format(text_hash))
        gnormplus_time = time.time() - gnormplus_start_time
        elapsed_time_dict['gnormplus'] = round(gnormplus_time, 3)
        print(datetime.now().strftime(self.stm_dict['time_format']),
              '[{}] GNormPlus {:.3f} sec'
              .format(cur_thread_name, gnormplus_time))

        # Move a GNormPlus output file to the tmVar2 input directory
        shutil.move(output_gnormplus, input_tmvar2)

        # Run tmVar 2.0
        tmvar2_start_time = time.time()
        tell_inputfile(self.stm_dict['tmvar2_host'],
                       self.stm_dict['tmvar2_port'],
                       '{}.PubTator'.format(text_hash))
        tmvar2_time = time.time() - tmvar2_start_time
        elapsed_time_dict['tmvar2'] = round(tmvar2_time, 3)
        print(datetime.now().strftime(self.stm_dict['time_format']),
              '[{}] tmVar 2.0 {:.3f} sec'
              .format(cur_thread_name, tmvar2_time))

        # Convert tmVar 2.0 outputs (?.PubTator.PubTator) to python dict
        dict_list = pubtator2dict_list(output_tmvar2, is_raw_text=True)

        # Delete temp files
        os.remove(input_gnormplus)
        os.remove(input_tmvar2)
        os.remove(output_tmvar2)

        # error
        if type(dict_list) is str:
            print(dict_list)
            return None

        # Run BioBERT of Lee et al., 2019
        ner_start_time = time.time()
        tagged_docs, num_entities = \
            self.biobert_recognize(dict_list, is_raw_text, cur_thread_name)
        if tagged_docs is None:
            return None

        assert len(tagged_docs) == 1
        ner_time = time.time() - ner_start_time
        elapsed_time_dict['ner'] = round(ner_time, 3)
        print(datetime.now().strftime(self.stm_dict['time_format']),
              '[%s] NER %.3f sec, #entities: %d' %
              (cur_thread_name, ner_time, num_entities))

        # Normalization models
        normalization_time = 0.
        if num_entities > 0:
            normalization_start_time = time.time()
            # print(datetime.now().strftime(time_format),
            #       '[{}] Normalization models..'.format(cur_thread_name))
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

        # Save a BERN result
        with open(bern_output_path, 'w', encoding='utf-8') as f_out:
            json.dump(tagged_docs[0], f_out, sort_keys=True)

        return tagged_docs[0]

    def biobert_recognize(self, dict_list, is_raw_text, cur_thread_name):
        res = self.stm_dict['biobert'].recognize(dict_list,
                                                 is_raw_text=is_raw_text,
                                                 thread_id=cur_thread_name)
        if res is None:
            return None, 0

        num_filtered_species_per_doc = filter_entities(res, is_raw_text)
        for n_f_spcs in num_filtered_species_per_doc:
            if n_f_spcs[1] > 0:
                print(datetime.now().strftime(self.stm_dict['time_format']),
                      '[{}] Filtered {} species{}'
                      .format(cur_thread_name, n_f_spcs[1],
                              '' if is_raw_text
                              else ' in PMID:%s' % n_f_spcs[0]))
        num_entities = count_entities(res)
        return res, num_entities


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