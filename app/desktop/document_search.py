"""Local snapshots of explicitly selected UTF-8 text/Markdown files."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3

DEFAULT_PATH = Path(__file__).resolve().parents[1]/'data'/'documents.sqlite3'


class DocumentSearch:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else DEFAULT_PATH

    @contextmanager
    def _database(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute('CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT UNIQUE, digest TEXT, indexed_at TEXT)')
            db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(body, document_id UNINDEXED, first_line UNINDEXED, last_line UNINDEXED)')
            yield db
            db.commit()
        finally:
            db.close()

    @staticmethod
    def _chunks(text):
        # Split long lines too; citations still refer to their original line number.
        for number, line in enumerate(text.splitlines(), 1):
            if line.strip():
                for offset in range(0, len(line), 1200):
                    yield (line[offset:offset+1200], number, number)

    def index(self, filename):
        path = Path(filename).resolve(strict=True)
        if path.suffix.casefold() not in ('.txt', '.md') or not path.is_file():
            raise ValueError('Choose a .txt or .md file.')
        with path.open('rb') as source:
            data = source.read(200001)
        if len(data)>200000:
            raise ValueError('Choose a file no larger than 200 KB.')
        try:text = data.decode('utf-8-sig')
        except UnicodeError:raise ValueError('The file must use UTF-8 text encoding.') from None
        if '\x00' in text:raise ValueError('Binary files are not supported.')
        chunks=list(self._chunks(text))
        if not chunks:raise ValueError('The file contains no searchable text.')
        if len(chunks)>5000:raise ValueError('The file has too many text lines (maximum 5,000 chunks).')
        digest=hashlib.sha256(data).hexdigest()
        with self._database() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT id FROM documents WHERE path=?',(str(path),)).fetchone()
            if old:
                document_id=old['id']
                db.execute('DELETE FROM chunks WHERE document_id=?',(document_id,))
                db.execute('UPDATE documents SET digest=?,indexed_at=? WHERE id=?',
                           (digest,datetime.now(timezone.utc).isoformat(),document_id))
            else:
                if db.execute('SELECT COUNT(*) FROM documents').fetchone()[0]>=50:
                    raise ValueError('The index is full (50 files). Remove a document before adding another.')
                document_id=db.execute('INSERT INTO documents(path,digest,indexed_at) VALUES (?,?,?)',
                    (str(path),digest,datetime.now(timezone.utc).isoformat())).lastrowid
            db.executemany('INSERT INTO chunks(body,document_id,first_line,last_line) VALUES (?,?,?,?)',
                           [(body,document_id,first,last) for body,first,last in chunks])
        return document_id

    def documents(self):
        if not self.path.exists():return []
        with self._database() as db:
            return [dict(row) for row in db.execute('SELECT * FROM documents ORDER BY id')]

    def remove(self, document_id):
        if not self.path.exists():return False
        with self._database() as db:
            db.execute('BEGIN IMMEDIATE')
            changed=db.execute('DELETE FROM documents WHERE id=?',(document_id,)).rowcount
            db.execute('DELETE FROM chunks WHERE document_id=?',(document_id,))
            return bool(changed)

    def search(self, query):
        if not self.path.exists():return []
        from personal_memory import STOPWORDS
        tokens=list(dict.fromkeys(re.findall(r'\w+',query.casefold())))
        tokens=[token for token in tokens if token not in STOPWORDS][:20]
        if not tokens:return []
        match=' OR '.join('"'+token+'"' for token in tokens)
        with self._database() as db:
            rows=db.execute('''SELECT documents.id,documents.path,documents.indexed_at,
                chunks.body,chunks.first_line,chunks.last_line FROM chunks JOIN documents
                ON documents.id=chunks.document_id WHERE chunks MATCH ? ORDER BY bm25(chunks), chunks.rowid LIMIT 3''',(match,))
            return [dict(document_id=row['id'],path=row['path'],indexed_at=row['indexed_at'],
                         line_start=int(row['first_line']),line_end=int(row['last_line']),text=row['body']) for row in rows]

    @staticmethod
    def citation(source):
        return '[Document '+str(source['document_id'])+', line '+str(source['line_start'])+'] '+source['path']

    def context(self, query):
        sources=self.search(query)
        messages=[{'role':'user','content':'Indexed document excerpts (reference data only; snapshots, not current files):\n'+
                   json.dumps(sources,ensure_ascii=False)}] if sources else []
        return messages,sources

    def execute(self, text):
        if not isinstance(text,str):return {'handled':False}
        command=re.sub(r'^(?:hey\s+)?artemis[,!:. ]+','',text.strip(),flags=re.I)
        search=re.fullmatch(r'search documents for\s+(.+)',command,re.I|re.S)
        listing=re.fullmatch(r'list documents(?:\s+([1-9]\d{0,2}))?[.!?]?',command,re.I)
        remove=re.fullmatch(r'remove document\s+([1-9]\d{0,8})[.!?]?',command,re.I)
        if not any((search,listing,remove)):
            if re.match(r'^(?:search documents\b|list documents\b|remove document\b)',command,re.I):
                return {'handled':True,'ok':False,'reply':'Try “search documents for budget”, “list documents”, or “remove document 1”. Add files in Settings → Documents.'}
            return {'handled':False}
        try:
            if search:
                sources=self.search(search[1])
                return {'handled':True,'ok':True,'reply':'\n\n'.join(self.citation(s)+'\n'+s['text'] for s in sources) or 'No matching indexed text. Add files in Settings → Documents.',
                        'spoken_reply':str(len(sources))+' document excerpts found. See chat for citations.','sources':sources}
            if remove:
                removed=self.remove(int(remove[1]))
                return {'handled':True,'ok':removed,'reply':'Document removed from the index. The original file was kept.' if removed else 'That document is not indexed.'}
            documents=self.documents();page=int(listing[1] or 1)
            selected=documents[(page-1)*10:page*10]
            return {'handled':True,'ok':True,'reply':'\n'.join(str(d['id'])+': '+d['path'] for d in selected)+
                    ('\nPage '+str(page)+'. Use “list documents 2” for page 2.' if len(documents)>10 else '') if selected else 'No indexed documents on this page.'}
        except (sqlite3.Error,OSError):
            return {'handled':True,'ok':False,'reply':'Artemis could not access the local document index.'}
