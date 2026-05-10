from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import os
doc = Document()
style = doc.styles["Normal"]
style.font.size = Pt(11)
style.paragraph_format.line_spacing = 1.5
