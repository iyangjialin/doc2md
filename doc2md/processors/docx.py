from pathlib import Path
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from doc2md.processors.base import BaseProcessor
from doc2md.models import ConversionResult
from doc2md.config import config

class DocxProcessor(BaseProcessor):
    SUPPORTED_EXTENSIONS = [".docx"]

    def process(self, file_path: str) -> ConversionResult:
        doc = Document(file_path)
        filename = Path(file_path).stem

        lines = []
        self.assets = []

        # Extract metadata
        metadata = self.extract_metadata(doc)
        if metadata:
            lines.append(self.build_front_matter(metadata))

        # Extract images first
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                image_data = rel.target_part.blob
                image_name = Path(rel.target_ref).name
                self.save_asset(filename, image_name, image_data)

        # Process paragraphs
        for element in doc.element.body:
            if isinstance(element, CT_P):
                para = Paragraph(element, doc)
                md = self._para_to_md(para, filename)
                if md:
                    lines.append(md)
            elif isinstance(element, CT_Tbl):
                table = Table(element, doc)
                lines.append(self._table_to_md(table))

        markdown = "\n\n".join(lines) + "\n"

        # Create output directory and save markdown
        output_dir = Path(config.PROJECTS_DIR) / self.project_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{filename}.md"
        output_path.write_text(markdown, encoding='utf-8')

        return ConversionResult(
            markdown=markdown,
            assets=self.assets,
            project_id=self.project_id,
            filename=f"{filename}.md"
        )

    def _para_to_md(self, para: Paragraph, doc_name: str) -> str:
        """Convert a paragraph to Markdown."""
        style_name = para.style.name.lower() if para.style else ""

        # Handle headings
        if style_name.startswith("heading"):
            level = style_name.replace("heading", "").strip() or "1"
            text = para.text.strip()
            if text:
                return f"{'#' * int(level)} {text}"

        # Handle blockquote
        if style_name in ["quote", "blockquote"]:
            lines = para.text.strip().split("\n")
            return "\n".join(f"> {line}" for line in lines)

        # Handle list items
        if para.style and ("list" in style_name or "bullet" in style_name or "number" in style_name):
            return self._list_item_to_md(para, style_name)

        # Handle task list
        for run in para.runs:
            if run.text and ("☐" in run.text or "☑" in run.text or "☒" in run.text):
                checked = "☑" in run.text or "☒" in run.text
                text = run.text.replace("☐", "").replace("☑", "").replace("☒", "").strip()
                return f"- [{'x' if checked else ' '}] {text}"

        # Regular paragraph
        text = para.text.strip()
        if not text:
            return ""

        # Process inline elements
        md = self._process_inline(para, doc_name)
        return md

    def _list_item_to_md(self, para: Paragraph, style_name: str) -> str:
        """Convert a list item to Markdown."""
        text = para.text.strip()
        if "number" in style_name or "ordered" in style_name:
            return f"1. {text}"
        return f"- {text}"

    def _process_inline(self, para: Paragraph, doc_name: str) -> str:
        """Process inline elements like links and images."""
        md = para.text

        # Process hyperlinks
        for run in para.runs:
            pass  # Basic implementation - hyperlinks need more complex handling

        return md

    def _table_to_md(self, table: Table) -> str:
        """Convert a table to Markdown."""
        rows = []
        for i, row in enumerate(table.rows):
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(f"| {' | '.join(cells) } |")
            if i == 0:
                rows.append("|" + "|".join(["---"] * len(cells)) + "|")
        return "\n".join(rows)

    def extract_metadata(self, doc: Document) -> dict:
        """Extract metadata from Word document."""
        core_props = doc.core_properties
        metadata = {}
        if core_props.title:
            metadata["title"] = core_props.title
        if core_props.author:
            metadata["author"] = core_props.author
        if core_props.created:
            metadata["date"] = core_props.created.strftime("%Y-%m-%d")
        return metadata