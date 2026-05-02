# 📄 MinerU OCR Markdown Cleaning Pipeline

## 📖 Overview
This project provides a preprocessing pipeline to clean and normalize Markdown (`.md`) output generated from OCR tools like :contentReference[oaicite:0]{index=0}.

OCR-generated Markdown often contains noise such as broken formatting, line numbers, figure artifacts, HTML tables, and unwanted sections. This pipeline transforms such raw outputs into clean, structured text suitable for NLP and LLM applications.

---

## 🚀 Features
- Removes unwanted sections (References, Acknowledgements, etc.)
- Converts HTML `<table>` content into LaTeX tabular format
- Removes PDF-style line numbers from OCR output
- Cleans figure/image noise (e.g., `![]`, "Figure 1")
- Masks sensitive data (emails, phone numbers, URLs)
- Filters invalid or empty documents

---

## ⚙️ Requirements
- Python 3.8+

Install dependencies:
```bash
pip install fasttext
