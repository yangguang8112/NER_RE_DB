# NER_RE_DB

### 下载数据库
git clone 这个仓库

然后下载http://60.205.203.207:8081/instance/ner_re.sqlite 数据库文件到仓库内的instance目录下，没有就新建一个

```sql
table|paper|paper|1110|CREATE TABLE paper (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  downloaded TEXT NOT NULL,
  paper_url TEXT,
  key_words TEXT,
  pdf_path TEXT,
  author TEXT,
  quote INTEGER,
  pubtime TEXT,
  ner_res TEXT NOT NULL
)
table|NER|NER|1217|CREATE TABLE NER (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ner_name TEXT NOT NULL,
  ner_type TEXT NOT NULL,
  ner_begin INTEGER,
  ner_end INTEGER,
  paper_id INTEGER
)
table|RE|RE|1226|CREATE TABLE RE (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  re_type TEXT NOT NULL,
  re_content TEXT NOT NULL,
  ner1_id INTEGER,
  ner1_name TEXT NOT NULL,
  ner2_name TEXT NOT NULL,
  ner2_id INTEGER,
  re_begin INTEGER,
  re_end INTEGER,
  paper_id INTEGER
)
```
以上是ner_re.sqlite中三张表（paper, NER, RE）的结构

paper存储文献的基本信息和全文，一篇文献一行；NER存储文献中的命名实体，一个命名实体一行；RE存储文献中有关系的命名实体，一个关系一行。

linux系统中查看数据库
```sql
# 打开数据库
sqlite3 ner_re.sqlite
# 数据库内操作 sql语句
sqlite> .tables
sqlite> SELECT * FROM paper LIMIT 10;
```
Windows下建议下载 http://www.sqliteexpert.com/download.html 个人版，可以对数据库进行可视化操作

### 查询
下面两段代码都是从RE表中找到符合关键词的句子然后在paper表中找到包含这句话的文献。

```sql
#sql
sqlite> SELECT RE.*, paper.title FROM RE 
        LEFT JOIN paper on RE.paper_id = paper.id 
        WHERE ner1_name = "PDA" OR ner2_name = "PDA";
```
查询脚本 query.py
```python
def query_re(keyword):
    db = get_db()
    res = db.execute(
        'SELECT RE.*, paper.title FROM RE'
        ' LEFT JOIN paper on RE.paper_id = paper.id'
        ' WHERE ner1_name = ?'
        ' OR ner2_name = ?',
        (keyword, keyword)
    ).fetchall()
    if res:
        print('title|sentence')
        for resone in res:
            print(resone['title']+'|'+resone['re_content'])
```
```sql
sqlite> SELECT NER.*, paper.title FROM NER 
        LEFT JOIN paper on NER.paper_id = paper.id
        WHERE ner_name = "c.506G>A";
```

查询脚本更新中，这也是本仓库后续重点更新部分。

可以根据数据库的表结构做一些满足自己需求的查询。


### 数据库构建
run_paper.py和run_ner_re.py分别是往数据库中插入paper信息，对paper内容做ner标注以及对ner标注做关系抽提。
做re之前需要将模型的两个文件夹model和config放到relation_extract下。
初始化数据库使用python db.py（一般用不到）。

#### 新增spacy进行断句
```shell
pip install scispacy
pip install <Model URL>
```

