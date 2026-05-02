import json
import time
import re
from html.parser import HTMLParser
import html as html_module
import fasttext

start_time = time.perf_counter()

model = fasttext.load_model("lid.176.bin")

def language_Filter(content):
    data = content.replace("\n", " ").strip()
    label, score = model.predict(data, k=1)
    if label[0] == "__label__en" and score[0] > 0.5:
        return content
    return None


def masking(text):
    if not text or not text.strip():
        return None

    text = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL]", text)

    text = re.sub(
        r"(?i)(?:tel(?:ephone)?|fax|phone):?\s?[\+\d\(\)][- \d\(\)]{5,30}[-\d\(\)](?:\s?ext\.?\s?\d+)?",
        "[PHONE/FAX]",
        text,
    )

    text = re.sub(r"(?i)\b(?:https?|ftp)://\S+|www\.\S+", "", text)

    return text.strip()


def remove_unwanted_sections(content):
    unwanted_sections = [
        "References", "Acknowledgements", "Acknowledgments", "Funding",
        "Author contributions", "Competing interests", "Disclosure Statement",
        "Supplementary Information", "Data Availability", "Conflict of Interest",
        "Affiliations", "Bibliography"
    ]

    header_pattern = re.compile(r"^(#+)\s*(.+)$", re.MULTILINE)
    headers = list(header_pattern.finditer(content))

    if not headers:
        return content

    cleaned_parts = []
    initial_text = content[: headers[0].start()]
    if initial_text.strip():
        cleaned_parts.append(initial_text)

    for i in range(len(headers)):
        start = headers[i].start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(content)

        header_title = headers[i].group(2).strip()
        section = content[start:end]

        if not any(u.lower() in header_title.lower() for u in unwanted_sections):
            cleaned_parts.append(section)

    return "".join(cleaned_parts)


_LINE_NUM_RE = re.compile(r'^(\d+)([\s\t]+)(\S.*?)\s*$')


def remove_line_numbers(content):
    lines = content.splitlines(keepends=True)
    result = []

    for line in lines:
        m = _LINE_NUM_RE.match(line.rstrip('\n'))
        if m:
            result.append(m.group(3) + "\n")
        else:
            result.append(line)

    return ''.join(result)


def preprocessing(content):
    lines = content.splitlines()
    cleaned = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("![]"):
            i += 1
            continue

        if re.match(r"^(Figure|Fig)\s*\d*", line, re.I):
            i += 1
            continue

        cleaned.append(lines[i])
        i += 1

    return "\n".join(cleaned)


def _escape_latex(text):
    replacements = {
        '\\': '\\textbackslash{}',
        '&': '\\&',
        '%': '\\%',
        '$': '\\$',
        '#': '\\#',
        '_': '\\_',
        '{': '\\{',
        '}': '\\}',
        '~': '\\textasciitilde{}',
        '^': '\\textasciicircum{}'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


class _TableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = None
        self.current_cell = None
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'tr':
            self.current_row = []
        elif tag in ('td', 'th'):
            self.current_cell = {
                'text': '',
                'colspan': int(attrs.get('colspan', 1)),
                'rowspan': int(attrs.get('rowspan', 1)),
            }
            self.in_cell = True

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.current_cell:
            self.current_cell['text'] = self.current_cell['text'].strip()
            self.current_row.append(self.current_cell)
            self.current_cell = None
            self.in_cell = False
        elif tag == 'tr' and self.current_row:
            self.rows.append(self.current_row)
            self.current_row = None

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell['text'] += data


def _html_table_to_latex(table_html):
    parser = _TableHTMLParser()
    parser.feed(table_html)

    rows = parser.rows
    if not rows:
        return table_html

    num_cols = max(sum(cell['colspan'] for cell in row) for row in rows)
    col_spec = '|' + '|'.join(['c'] * num_cols) + '|'

    lines = [f'\\begin{{tabular}}{{{col_spec}}}', '\\hline']

    for row in rows:
        parts = []
        for cell in row:
            text = _escape_latex(cell['text'])
            if cell['colspan'] > 1:
                parts.append(f'\\multicolumn{{{cell["colspan"]}}}{{|c|}}{{{text}}}')
            else:
                parts.append(text)
        lines.append(' & '.join(parts) + ' \\\\')
        lines.append('\\hline')

    lines.append('\\end{tabular}')
    return "\n".join(lines)


def convert_html_tables_to_latex(content):
    pattern = re.compile(r'<table>.*?</table>', re.DOTALL | re.IGNORECASE)
    return pattern.sub(lambda m: _html_table_to_latex(m.group(0)), content)


input_file = "datamd.jsonl"
output_file = "datamd_cleaned.jsonl"

total = 0
rejected = 0

with open(input_file, "r", encoding="utf-8") as md_input, open(output_file, "w", encoding="utf-8") as md_output:
    for line in md_input:
        data = json.loads(line)
        content = data["text"]

        content = remove_unwanted_sections(content)
        content = convert_html_tables_to_latex(content)
        content = remove_line_numbers(content)

        cleaned = preprocessing(content)
        cleaned = masking(cleaned)

        total += 1
        if cleaned:
            json.dump({"text": cleaned}, md_output, ensure_ascii=False)
            md_output.write("\n")
        else:
            rejected += 1

end_time = time.perf_counter()

print(f"Total processed: {total}")
print(f"Rejected: {rejected}")
print(f"Time taken: {end_time - start_time:.2f}s")
print(f"Saved to: {output_file}")
