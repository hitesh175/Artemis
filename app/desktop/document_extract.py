"""Extract searchable text with honest source locations; never execute content."""
import io
import zipfile
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def extract(data, suffix):
    """Return (text, locator) sections. PDF pages; Word body blocks; text lines."""
    if suffix in ('.txt', '.md'):
        try:text=data.decode('utf-8-sig')
        except UnicodeError:raise ValueError('The file must use UTF-8 text encoding.') from None
        if '\x00' in text:raise ValueError('Binary files are not supported.')
        return [(text, '')]
    if suffix=='.pdf':
        try:from pypdf import PdfReader
        except ImportError:raise ValueError('PDF support requires pypdf. Install the project requirements first.') from None
        try:
            reader=PdfReader(io.BytesIO(data))
            if reader.is_encrypted:raise ValueError('Encrypted PDFs are not supported. Choose an unencrypted copy.')
            if len(reader.pages)>100:raise ValueError('Choose a PDF of at most 100 pages.')
            sections=[]
            for number,page in enumerate(reader.pages,1):
                contents=page.get_contents()
                if contents and len(contents.get_data())>4000000:
                    raise ValueError('A PDF page is too complex to extract.')
                text=page.extract_text() or ''
                sections.append((text,'page '+str(number)))
            return sections
        except ValueError:raise
        except Exception:raise ValueError('The PDF could not be read. It may be damaged or unsupported.') from None
    if suffix=='.docx':
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries=archive.infolist()
                if len(entries)>2000 or sum(entry.file_size for entry in entries)>20000000:
                    raise ValueError('The Word document expands beyond the extraction limit.')
                info=archive.getinfo('word/document.xml')
                if info.file_size>4000000:raise ValueError('The Word document body is too large.')
                xml=archive.read(info)
            if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
                raise ValueError('Custom XML entities are not supported.')
            body=ET.fromstring(xml).find(W+'body')
            if body is None:raise ValueError('The Word document has no body.')
            sections=[];paragraph=0;table=0
            def text(element):
                return ''.join(node.text or '' for node in element.iter(W+'t'))
            for block in body:
                if block.tag==W+'p':
                    paragraph+=1
                    sections.append((text(block),'paragraph '+str(paragraph)))
                elif block.tag==W+'tbl':
                    table+=1
                    for row_number,row in enumerate(block.findall(W+'tr'),1):
                        cells=[' '.join(text(p) for p in cell.findall(W+'p')) for cell in row.findall(W+'tc')]
                        sections.append((' | '.join(cells),'table '+str(table)+', row '+str(row_number)))
            return sections
        except ValueError:raise
        except Exception:raise ValueError('The Word document could not be read. Choose a valid .docx file.') from None
    raise ValueError('Choose a .txt, .md, .pdf or .docx file.')
