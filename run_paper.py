from update_ner import loads_xlsx
import sys

xlsx_file = sys.argv[1]
log_path = sys.argv[2]

loads_xlsx(xlsx_file, log_path)