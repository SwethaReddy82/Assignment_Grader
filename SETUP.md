# AI Grading Assistant — Setup Guide
### AI for Analytics Course · Teaching Assistant Tool

---

## What This Does

This tool helps Teaching Assistants grade student assignments automatically using Claude AI. Given:
- The **assignment instructions** (PDF or DOCX)
- A **grading rubric** (PDF or DOCX)
- A **folder of student submissions** (PDF or DOCX)

It produces:
- **Per-student feedback files** — personalised `.txt` feedback for each student
- **CSV summary** — class-wide spreadsheet with scores per criterion
- **HTML dashboard** — interactive visual report you can open in a browser

---

## Quick Start (5 minutes)

### 1. Install Python dependencies

```bash
pip install anthropic pdfplumber python-docx rich
```

Or use the requirements file:
```bash
pip install -r requirements.txt
```

### 2. Get your Anthropic API key

Sign up at [console.anthropic.com](https://console.anthropic.com) and create an API key.

Set it as an environment variable (recommended):
```bash
# Mac / Linux
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows (Command Prompt)
set ANTHROPIC_API_KEY=sk-ant-...

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. (Optional) Generate sample data to test first

```bash
python create_sample_data.py
```

This creates 3 sample student submissions at different quality levels plus a rubric and instructions — no real student data needed for a demo.

### 4. Run the grader

**Interactive mode** (guided prompts):
```bash
python main.py
```

**Command-line mode** (pass all args):
```bash
python main.py \
    --instructions path/to/instructions.pdf \
    --rubric       path/to/rubric.docx \
    --submissions  path/to/students_folder/ \
    --output       path/to/output_folder/ \
    --assignment   "Assignment 1: EDA with Python"
```

---

## Folder Structure

```
ta_grader/
├── main.py                  ← Run this to start the app
├── grader.py                ← Claude API grading engine
├── document_reader.py       ← PDF + DOCX text extraction
├── report_generator.py      ← Feedback, CSV, and HTML reports
├── create_sample_data.py    ← Generate demo files
├── requirements.txt
└── sample_data/             ← Created by create_sample_data.py
    ├── assignment_instructions.docx
    ├── grading_rubric.docx
    ├── student_submissions/
    │   ├── alice_chen_assignment1.docx
    │   ├── bob_martinez_assignment1.docx
    │   └── carol_liu_assignment1.docx
    └── grading_output/      ← Created after running grader
        ├── grading_summary_TIMESTAMP.csv
        ├── grading_report_TIMESTAMP.html
        └── student_feedback/
            ├── Alice_Chen_feedback.txt
            ├── Bob_Martinez_feedback.txt
            └── Carol_Liu_feedback.txt
```

---

## Tips for Best Results

**Rubric formatting:** The more specific your rubric, the better Claude grades. Include:
- Criterion names
- Max points per criterion
- What full marks vs. partial credit looks like

**File naming:** Name student files as `firstname_lastname_assignment1.docx` — the app automatically extracts the student name from the filename.

**Supported file types:** `.pdf`, `.docx`, `.doc`, `.txt`, `.md`

**API costs:** Each grading call uses ~2,000–4,000 tokens. At standard Claude rates, grading 30 students costs roughly $0.30–$1.00.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: pdfplumber` | Run `pip install pdfplumber` |
| `ModuleNotFoundError: docx` | Run `pip install python-docx` |
| `AuthenticationError` | Check your API key is set correctly |
| Empty PDF extraction | The PDF may be image-based (scanned). Convert to text-PDF first. |
| Student name shows as filename | Rename files to `firstname_lastname.docx` format |
```
