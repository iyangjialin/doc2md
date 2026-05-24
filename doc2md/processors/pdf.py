import pdfplumber
import fitz  # PyMuPDF
from pathlib import Path
from doc2md.processors.base import BaseProcessor
from doc2md.models import ConversionResult
from doc2md.config import config

class PdfProcessor(BaseProcessor):
    SUPPORTED_EXTENSIONS = [".pdf"]

    def process(self, file_path: str) -> ConversionResult:
        filename = Path(file_path).stem
        self.assets = []

        # Extract images
        self._extract_images(file_path, filename)

        # Extract text with pdfplumber
        text, confidence = self._extract_text(file_path)

        lines = text.split("\n")
        markdown = "\n\n".join(lines) + "\n"

        # Save markdown
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

    def _extract_text(self, file_path: str) -> tuple[str, float]:
        """Extract text from PDF using pdfplumber."""
        text_parts = []
        total_chars = 0
        valid_chars = 0

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
                total_chars += len(page_text)
                valid_chars += sum(1 for c in page_text if c.isprintable() or c in "\n ")

        full_text = "\n\n".join(text_parts)
        confidence = valid_chars / total_chars if total_chars > 0 else 0

        return full_text, confidence

    def _extract_images(self, file_path: str, doc_name: str):
        """Extract images from PDF using PyMuPDF."""
        doc = fitz.open(file_path)
        for page_num, page in enumerate(doc):
            images = page.get_images()
            for img_idx, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_name = f"page{page_num+1}_img{img_idx+1}.{base_image['ext']}"
                self.save_asset(doc_name, image_name, image_bytes)
        doc.close()