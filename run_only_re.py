from update_ner import run_re_db
import sys

paper_ids_file = sys.argv[1]

run_re_db(paper_ids_file)