import fitz  # PyMuPDF for reading PDFs
import os
import json
import hashlib
import re
from PIL import Image
from io import BytesIO
from typing import List, Dict, Union
import subprocess

# Set file paths and constants
PDF_PATH = "IMO class 1 Maths Olympiad Sample Paper 1 for the year 2024-25.pdf"
VEDANTU_LOGO_PATH = "vedantulogo.jpeg"
OUTPUT_DIR = "output"
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
JSON_OUTPUT = os.path.join(OUTPUT_DIR, "extracted_content.json")
VALID_IMAGE_EXTS = ['png', 'jpg', 'jpeg', 'jpe']

# Create image output directory if it doesn't exist
os.makedirs(IMAGE_DIR, exist_ok=True)

class PDFExtractor:
    def __init__(self):
        self.vedantu_logo_hash = None
        self._load_vedantu_logo()  # Precompute Vedantu logo hash for skipping

    def _load_vedantu_logo(self):
        if os.path.exists(VEDANTU_LOGO_PATH):
            with open(VEDANTU_LOGO_PATH, "rb") as logo_file:
                logo_bytes = logo_file.read()
            self.vedantu_logo_hash = self._get_image_hash(logo_bytes)

    def _get_image_hash(self, image_data: bytes) -> str:
        # Return MD5 hash of the image bytes (used for comparison)
        with Image.open(BytesIO(image_data)) as img:
            img = img.convert("RGB")
            return hashlib.md5(img.tobytes()).hexdigest()

    def _save_image(self, image_bytes: bytes, path: str) -> bool:
        # Save image to disk at given path
        try:
            with open(path, "wb") as f:
                f.write(image_bytes)
            return True
        except:
            return False

    def _clean_question_text(self, text: str) -> str:
        # Remove unwanted patterns like "Ans. [A]" and page tags
        text = re.sub(r'Ans\.?\s*\[?[A-D]\]?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'---page\d+---', '', text)
        return ' '.join(text.split()).strip()

    def _extract_options(self, question_text: str) -> List[Dict[str, str]]:
        # Extract options formatted like [A] Option Text
        options = []
        option_parts = re.split(r'(\[[A-D]\][^\[\]]*)', question_text)
        for part in option_parts:
            if not part.strip():
                continue
            match = re.match(r'\[([A-D])\](.*)', part.strip())
            if match:
                label = match.group(1)
                text = match.group(2).strip()
                if text:
                    options.append({"label": label, "text": text})
        return options

    def _should_skip_page(self, text: str, image_infos: list, doc: fitz.Document) -> bool:
        # Skip page if it's blank except Vedantu logo
        if not text and len(image_infos) == 1 and self.vedantu_logo_hash:
            xref = image_infos[0][0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            return self._get_image_hash(image_bytes) == self.vedantu_logo_hash
        return False

    def _is_question_with_image(self, text: str) -> bool:
        # Check if question likely refers to a diagram/image
        patterns = [
            r'\d+\s*[=≠<>]\s*\d+',
            r'_\s*_\s*_',
            r'see (figure|image|diagram)',
            r'below\s*:?$'
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def extract_content(self) -> List[Dict[str, Union[str, List, Dict]]]:
        doc = fitz.open(PDF_PATH)
        all_text = ""
        all_images = []

        # Extract and save valid images from each page
        for page_number in range(len(doc)):
            page = doc.load_page(page_number)
            image_infos = page.get_images(full=True)
            for img_index, img in enumerate(image_infos, 1):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"].lower()
                if ext not in VALID_IMAGE_EXTS:
                    continue
                if self.vedantu_logo_hash and self._get_image_hash(image_bytes) == self.vedantu_logo_hash:
                    continue
                filename = f"page{page_number+1}_image{img_index}.{ext}"
                path = os.path.join(IMAGE_DIR, filename)
                if self._save_image(image_bytes, path):
                    all_images.append({
                        "page": page_number + 1,
                        "image": path
                    })

        # Extract text from each page
        for page_number in range(len(doc)):
            page = doc.load_page(page_number)
            text = page.get_text().strip()
            if self._should_skip_page(text, page.get_images(full=True), doc):
                continue
            all_text += f"\n---page{page_number + 1}---\n{text}"

        # Split text into individual questions
        question_pattern = r'(?=\n\d+\.\s|\A\d+\.\s)'
        raw_questions = re.split(question_pattern, all_text)
        raw_questions = [q.strip() for q in raw_questions if re.match(r'^\d+\.\s', q.strip())]

        questions_data = []
        image_index = 0

        # Process each question
        for q_text in raw_questions:
            if q_text.upper().startswith("CLASS") or "SECTION" in q_text.upper():
                continue

            question_num_match = re.match(r'^(\d+)\.', q_text)
            if not question_num_match:
                continue

            clean_text = self._clean_question_text(q_text)
            current_page = int(re.search(r'---page(\d+)---', q_text).group(1)) if re.search(r'---page(\d+)---', q_text) else None

            question_images = []
            if image_index < len(all_images):
                if self._is_question_with_image(clean_text) or current_page:
                    page_images = [img for img in all_images if img["page"] == current_page]
                    if page_images:
                        question_images = [img["image"] for img in page_images]
                        image_index += len(page_images)
                else:
                    question_images = [all_images[image_index]["image"]]
                    image_index += 1

            option_images = []
            while image_index < len(all_images) and len(option_images) < 4:
                option_images.append(all_images[image_index]["image"])
                image_index += 1

            question_obj = {
                "question": clean_text,
                "images": question_images[0] if question_images else None
            }

            if option_images:
                question_obj["option_images"] = option_images
            else:
                options = self._extract_options(q_text)
                if options:
                    question_obj["options"] = options

            questions_data.append(question_obj)

        return questions_data

    def save_to_json(self, data: List[Dict]) -> None:
        # Save extracted data to JSON
        with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Extracted content saved to: {JSON_OUTPUT}")

# Run everything
if __name__ == "__main__":
    extractor = PDFExtractor()
    data = extractor.extract_content()
    extractor.save_to_json(data)

    # Run additional post-processing scripts
    subprocess.run(["python", "generate_image_captions.py"])
    subprocess.run(["python", "generate_questions_from_captions.py"])
