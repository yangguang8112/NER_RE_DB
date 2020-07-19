from update_ner import run_re_db
import sys

paper_ids_file = sys.argv[1]

paper_id_min = int(sys.argv[1])
paper_id_max = int(sys.argv[2])

re_type = 'gene-disease'
if sys.argv[3]:
    re_type = sys.argv[3]

run_re_db(paper_id_min, paper_id_max, re_type=re_type)