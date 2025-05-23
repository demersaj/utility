from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode

pipeline_options = PdfPipelineOptions(do_table_structure=True)
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE  # use more accurate TableFormer model

doc_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

source = "/Users/huxley-47/Downloads/Deere manuals/1023E/1.pdf"  # PDF path or URL
result = doc_converter.convert(source)
#print(result.document.export_to_markdown())

with open("test.md", "a") as f:
  print(result.document.export_to_markdown(), file=f)
f.close()	
