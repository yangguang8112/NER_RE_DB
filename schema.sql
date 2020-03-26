
DROP TABLE IF EXISTS paper;
DROP TABLE IF EXISTS NER;
DROP TABLE IF EXISTS RE;

CREATE TABLE paper (
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
);

CREATE TABLE NER (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ner_name TEXT NOT NULL,
  ner_type TEXT NOT NULL,
  ner_begin INTEGER,
  ner_end INTEGER,
  paper_id INTEGER
);

CREATE TABLE RE (
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
