from update_ner import loads_xlsx, from_sql
import sys

#xlsx_file = sys.argv[1]
sql_file = sys.argv[1]
pdf_data_path = sys.argv[2]
log_path = sys.argv[3]

#loads_xlsx(xlsx_file, log_path)
from_sql(sql_file, pdf_data_path, log_path)