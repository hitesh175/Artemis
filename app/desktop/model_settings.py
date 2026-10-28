"""Persist the chat model; all requests still use the fixed local Ollama endpoint."""
import json
from contextlib import closing
from pathlib import Path
import re
import sqlite3
from urllib import request

DEFAULT_PATH=Path(__file__).resolve().parents[1]/'data'/'model-settings.sqlite3'


class ModelSettings:
    def __init__(self,path=None):
        self.path=Path(path) if path is not None else DEFAULT_PATH

    @staticmethod
    def valid(name):
        return isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}',name) is not None

    def get(self):
        if not self.path.exists():return 'artemis'
        with closing(sqlite3.connect(self.path,timeout=5)) as db:
            row=db.execute('SELECT name FROM selected_model WHERE id=1').fetchone()
        if not row or not self.valid(row[0]):raise ValueError('Invalid saved model setting')
        return row[0]

    @staticmethod
    def available():
        with request.urlopen('http://127.0.0.1:11434/api/tags',timeout=3) as response:
            data=json.load(response)
        if not isinstance(data,dict) or not isinstance(data.get('models'),list):
            raise ValueError('Invalid model list from Ollama')
        return sorted({model['name'] for model in data['models']
                       if isinstance(model,dict) and ModelSettings.valid(model.get('name'))})

    def select(self,name):
        if not self.valid(name):raise ValueError('Choose a valid installed model name.')
        names=self.available()
        if name not in names and name+':latest' not in names:
            raise ValueError('That model is not installed in Ollama. Refresh the list and choose again.')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS selected_model(id INTEGER PRIMARY KEY CHECK(id=1),name TEXT NOT NULL)')
            db.execute('INSERT INTO selected_model VALUES (1,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name',(name,))
        return name
