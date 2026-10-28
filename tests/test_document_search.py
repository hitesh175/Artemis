"""Isolated document snapshots; no user files or live model required."""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/desktop'))
from document_search import DocumentSearch

with tempfile.TemporaryDirectory() as folder:
    root=Path(folder);store=DocumentSearch(root/'index.sqlite3')
    assert store.search('budget')==[] and not store.path.exists()
    file=root/'notes.md';file.write_text('Project notes\nBudget approved: 250 euros\n',encoding='utf-8')
    document_id=store.index(file)
    assert document_id==1
    result=store.search('What budget was approved?')[0]
    assert result['document_id']==1 and result['line_start']==2
    assert result['text']=='Budget approved: 250 euros'
    assert str(file) in store.citation(result)
    assert store.search('" OR * DROP TABLE chunks;')==[]
    assert not store.execute('explain documents')['handled']
    assert store.execute('search documents for budget')['sources'][0]['line_start']==2
    assert 'notes.md' in store.execute('list documents')['reply']
    assert not store.execute('remove document all')['ok']
    file.write_text('Replacement budget is 500 euros',encoding='utf-8')
    assert '250' in store.search('budget')[0]['text'], 'Only explicit refresh may re-read files'
    assert store.index(file)==1
    assert '500' in store.search('budget')[0]['text']
    assert store.search('approved')==[]
    assert DocumentSearch(store.path).search('replacement')
    messages,sources=store.context('budget')
    assert messages[0]['role']=='user' and sources[0]['path']==str(file)
    bad=root/'bad.txt';bad.write_bytes(b'\xff\xfe')
    binary=root/'binary.txt';binary.write_bytes(b'abc\x00def')
    large=root/'large.txt';large.write_bytes(b'x'*200001)
    unsupported=root/'report.pdf';unsupported.write_bytes(b'%PDF')
    empty=root/'empty.txt';empty.write_text('   ')
    for path in (bad,binary,large,unsupported,empty):
        try:store.index(path);raise AssertionError('Invalid file accepted: '+str(path))
        except ValueError:pass
    assert len(store.documents())==1, 'Failed indexing must preserve the index'
    assert store.execute('remove document 1')['ok']
    assert file.exists() and store.context('budget')==([],[])
    assert not store.execute('remove document 1')['ok']
    assert store.index(file)>1, 'Removed citation IDs must not be reused'
print('PASS: selected-file snapshots, line citations, refresh, persistence, removal, format/size limits and query escaping')
