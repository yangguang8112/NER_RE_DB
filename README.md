# NER_RE_DB

git clone 这个仓库

然后下载http://60.205.203.207:8081/instance/ner_re.sqlite 数据库文件到仓库内的instance目录下，没有就新建一个

run_paper.py和run_ner_re.py分别是往数据库中插入paper信息，对paper内容做ner标注以及对ner标注做关系抽提


做re之前需要将模型的两个文件夹model和config放到relation_extract下

初始化数据库使用python db.py（一般用不到）
