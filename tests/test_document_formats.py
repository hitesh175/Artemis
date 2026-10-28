"""Synthetic extraction fixtures: no user documents and no visual-layout claims."""
import io
from pathlib import Path
import sys
import tempfile
import zipfile
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/desktop'))
from document_search import DocumentSearch
from document_extract import extract
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

def pdf_bytes(encrypted=False, blank=False):
    writer=PdfWriter()
    for phrase in ('Overview of project','Approved budget 900 euros'):
        page=writer.add_blank_page(width=600,height=800)
        if not blank:
            font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
            page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
            stream=DecodedStreamObject();stream.set_data(('BT /F1 12 Tf 30 700 Td ('+phrase+') Tj ET').encode())
            page[NameObject('/Contents')]=writer._add_object(stream)
    if encrypted:writer.encrypt('password')
    output=io.BytesIO();writer.write(output);return output.getvalue()

with tempfile.TemporaryDirectory() as folder:
    root=Path(folder);store=DocumentSearch(root/'index.sqlite3')
    pdf=root/'budget.pdf';pdf.write_bytes(pdf_bytes())
    document_id=store.index(pdf)
    source=store.search('900')[0]
    assert source['document_id']==document_id and source['locator']=='page 2'
    assert source['line_start'] is None and 'page 2' in store.citation(source)
    xml=b'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
      <w:p><w:r><w:t>Project overview</w:t></w:r></w:p><w:p/>
      <w:p><w:r><w:t>Launch date November</w:t></w:r></w:p>
      <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Venue</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Berlin</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
    </w:body></w:document>'''
    word=root/'plan.docx'
    with zipfile.ZipFile(word,'w') as archive:archive.writestr('word/document.xml',xml)
    word_id=store.index(word)
    assert store.search('November')[0]['locator']=='paragraph 3'
    assert store.search('Berlin')[0]['locator']=='table 1, row 1'
    assert 'Venue | Berlin' in store.search('Berlin')[0]['text']
    assert store.index(word)==word_id
    for content in (pdf_bytes(encrypted=True),pdf_bytes(blank=True),b'broken'):
        pdf.write_bytes(content)
        try:store.index(pdf);raise AssertionError('Invalid PDF accepted')
        except ValueError:pass
        assert store.search('900'), 'Failed refresh must retain previous snapshot'
    with patch.dict(sys.modules,{'pypdf':None}):
        try:extract(b'pdf','.pdf');raise AssertionError('Missing dependency accepted')
        except ValueError as error:assert 'requires pypdf' in str(error)
    with zipfile.ZipFile(word,'w') as archive:archive.writestr('word/document.xml',b'<!DOCTYPE document><document/>')
    try:store.index(word);raise AssertionError('Custom XML declaration accepted')
    except ValueError:pass
    assert store.search('Berlin'), 'Failed Word refresh must retain previous snapshot'
    assert store.remove(word_id) and not store.search('Berlin')
    # Simulate an old text-only database lacking locator metadata.
    text=root/'legacy.txt';text.write_text('Legacy text survives migration',encoding='utf-8')
    store.index(text)
    with store._database() as db:db.execute('DROP TABLE chunk_locations')
    assert DocumentSearch(store.path).search('Legacy')[0]['locator']=='line 1'
print('PASS: PDF page citations, Word paragraph/table locations, old-index compatibility, rejection and rollback')
