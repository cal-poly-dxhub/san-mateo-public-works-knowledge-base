import io
import PyPDF2
import docx
import openpyxl


def extract_text(file_bytes, filename):
    """Extract text from various document formats"""
    ext = filename.lower().split('.')[-1]
    
    if ext == 'pdf':
        return extract_pdf(file_bytes)
    elif ext in ['doc', 'docx']:
        return extract_docx(file_bytes)
    elif ext in ['xls', 'xlsx']:
        return extract_xlsx(file_bytes)
    else:
        return file_bytes.decode('utf-8')


def extract_pdf(file_bytes):
    """Extract text from PDF"""
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    return '\n'.join(page.extract_text() for page in reader.pages)


def extract_docx(file_bytes):
    """Extract text from DOCX"""
    doc = docx.Document(io.BytesIO(file_bytes))
    return '\n'.join(para.text for para in doc.paragraphs)


def extract_xlsx(file_bytes):
    """Extract text from XLSX"""
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    text = []
    for sheet in wb.worksheets:
        text.append(f"Sheet: {sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            row_text = '\t'.join(str(c) if c else '' for c in row)
            if row_text.strip():
                text.append(row_text)
    return '\n'.join(text)
