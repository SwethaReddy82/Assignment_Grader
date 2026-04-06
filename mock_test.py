"""
mock_test.py
------------
Runs the full grading pipeline with pre-written mock responses
instead of calling the real Claude API. Use this to test all
outputs (feedback files, CSV, HTML) without any API key or cost.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from document_reader import read_document, load_student_submissions
from report_generator import write_student_feedback, write_csv_summary, write_html_report

# ── Pre-written mock grading results ─────────────────────────────────────────
# These simulate exactly what Claude would return for each student.

MOCK_RESULTS = [
    {
        "student_name": "Alice Chen",
        "file": "alice_chen_assignment1.docx",
        "total_score": 91,
        "max_score": 100,
        "percentage": 91.0,
        "letter_grade": "A-",
        "overall_summary": (
            "Alice has produced an excellent EDA report that demonstrates a clear understanding "
            "of statistical concepts and Python best practices. Her dataset selection was well-justified, "
            "her cleaning steps were thorough and documented, and her visualisations were varied and "
            "insightful. A minor area for improvement is providing more interpretation of skewness "
            "values in the context of the domain, but overall this is a strong submission."
        ),
        "strengths": [
            "Outstanding dataset justification with specific relevance to AI for Analytics explained clearly",
            "Comprehensive data cleaning: missing value imputation, IQR-based outlier detection, and dtype validation all documented",
            "Six distinct chart types used — exceeds the minimum requirement of five",
            "Strong correlation analysis with r-values cited and interpreted (e.g. GDP vs Happiness r=0.78)",
            "Modular, PEP 8-compliant code with docstrings and a requirements.txt",
        ],
        "areas_for_improvement": [
            "Skewness and kurtosis values are computed but the domain implication (e.g. log-transform suggestion) could be expanded further",
            "The pair plot insight about the freedom threshold effect would benefit from a formal statistical test",
            "Consider adding a brief data dictionary explaining each feature",
        ],
        "criteria": [
            {"name": "Dataset Selection & Justification", "max_points": 10, "awarded_points": 10,
             "feedback": "Excellent justification. The World Happiness Report dataset is directly relevant to AI for Analytics and the 2-3 sentence rationale clearly explains why it was chosen for multi-dimensional EDA."},
            {"name": "Data Cleaning & Preprocessing", "max_points": 20, "awarded_points": 19,
             "feedback": "All missing values and outliers handled with well-documented rationale. The decision to retain outliers in GDP because they represent real countries is analytically sound. Minor deduction for not validating category columns."},
            {"name": "Descriptive Statistics", "max_points": 20, "awarded_points": 18,
             "feedback": "All 6 features analysed with mean, std, skew, and kurtosis. Interpretations are generally good. The note about right-skewed corruption perception suggesting a log-transform is insightful. Could expand on what the kurtosis values tell us practically."},
            {"name": "Visualisations", "max_points": 25, "awarded_points": 24,
             "feedback": "Six distinct chart types all properly labelled and each accompanied by a written insight. The correlation heatmap and pair plot add significant analytical depth. Minor: axis labels on the box plot could be more descriptive."},
            {"name": "Insights & Conclusions", "max_points": 15, "awarded_points": 13,
             "feedback": "Five well-stated findings, each supported by specific data points. The threshold effect for freedom is particularly perceptive. The multicollinearity observation shows forward-thinking about modelling. Could strengthen by quantifying confidence intervals."},
            {"name": "Code Quality & Documentation", "max_points": 10, "awarded_points": 7,
             "feedback": "Modular functions with docstrings and inline comments. PEP 8 compliant and includes requirements.txt. Deduction for one function (plot_visualisations) that exceeds 50 lines without internal comments."},
        ],
        "actionable_suggestions": (
            "1. Add domain interpretation to your skewness/kurtosis discussion — for instance, "
            "explain why right-skewed corruption perception may warrant a log-transform before modelling.\n"
            "2. For the freedom threshold effect, consider running a simple Pearson/Spearman test on "
            "the two sub-populations (freedom < 0.5 vs >= 0.5) to support the claim statistically.\n"
            "3. Break the plot_visualisations function into smaller, single-purpose functions — "
            "one per chart type — with docstrings describing what each shows.\n"
            "4. Add a brief data dictionary (markdown table or docstring) listing each feature, "
            "its units, and its source."
        ),
    },
    {
        "student_name": "Bob Martinez",
        "file": "bob_martinez_assignment1.docx",
        "total_score": 63,
        "max_score": 100,
        "percentage": 63.0,
        "letter_grade": "D",
        "overall_summary": (
            "Bob's submission covers the basic requirements but lacks the depth and rigour expected "
            "at this level. The dataset selection is not justified, data cleaning is destructive "
            "(dropping rows rather than imputing), and the statistical analysis is surface-level. "
            "Visualisations are present but not sufficiently explained. With more attention to "
            "interpretation and documentation, this work could be substantially improved."
        ),
        "strengths": [
            "Chose a well-known, accessible dataset suitable for EDA",
            "Produced four distinct chart types demonstrating awareness of different visualisation options",
            "Identified the key finding about gender-based survival rates correctly",
        ],
        "areas_for_improvement": [
            "No justification given for the dataset choice — why is the Titanic dataset relevant to AI for Analytics?",
            "Dropping rows with missing values (df.dropna()) is a destructive approach; imputation or justification is required",
            "Statistical analysis is limited to means only — no standard deviation, skewness, or kurtosis computed",
            "Visualisations are listed but not individually interpreted — each chart should have a written insight",
            "Code has no comments or documentation",
        ],
        "criteria": [
            {"name": "Dataset Selection & Justification", "max_points": 10, "awarded_points": 3,
             "feedback": "The Titanic dataset is a valid choice but no justification is provided. The assignment requires 2-3 sentences explaining the dataset's relevance to analytics. Simply naming the dataset and saying it 'has passenger information' does not meet the criterion."},
            {"name": "Data Cleaning & Preprocessing", "max_points": 20, "awarded_points": 10,
             "feedback": "Missing values were identified in the Age column but handled by dropping rows, which loses ~20% of the data. The rubric requires justification or alternative handling (e.g. median imputation). No outlier detection performed, and no dtype validation documented."},
            {"name": "Descriptive Statistics", "max_points": 20, "awarded_points": 12,
             "feedback": "Only mean values reported for age, fare, and survival rate. The rubric requires mean, median, standard deviation, skewness, and kurtosis for at least 5 features. Three features are analysed but the statistical depth is insufficient."},
            {"name": "Visualisations", "max_points": 25, "awarded_points": 20,
             "feedback": "Four chart types are present (histogram, bar chart, scatter plot, heatmap) which is one short of the minimum five required. Each chart is mentioned but not individually interpreted — the bar chart conclusion ('women survived more') is correct but brief. Each visualisation needs a 1-2 sentence analytical insight."},
            {"name": "Insights & Conclusions", "max_points": 15, "awarded_points": 12,
             "feedback": "Three findings are stated: gender survival, fare correlation, and age effect. These are valid observations but stated without supporting data (no r-values, no percentages cited to back up claims). The conclusion that 'age didn't seem to matter much' needs quantitative support."},
            {"name": "Code Quality & Documentation", "max_points": 10, "awarded_points": 6,
             "feedback": "Code is functional and readable in structure, but has no comments or docstrings. Variable names are generic (df) rather than descriptive. The rubric requires comments on non-obvious operations and meaningful variable names."},
        ],
        "actionable_suggestions": (
            "1. Add a 2-3 sentence justification for choosing the Titanic dataset, specifically connecting "
            "it to what you are learning in AI for Analytics.\n"
            "2. Replace df.dropna() with median or mode imputation for the Age column. Document why "
            "you chose that approach.\n"
            "3. Compute and report standard deviation, skewness, and kurtosis for all 5 numerical features "
            "using df.describe() and df.skew().\n"
            "4. Add a written insight paragraph below each chart — explain what pattern you see and "
            "what it means analytically.\n"
            "5. Add inline comments to your code, especially on non-obvious steps like the dropna and "
            "the correlation heatmap calculation."
        ),
    },
    {
        "student_name": "Carol Liu",
        "file": "carol_liu_assignment1.docx",
        "total_score": 22,
        "max_score": 100,
        "percentage": 22.0,
        "letter_grade": "F",
        "overall_summary": (
            "Carol's submission is significantly below the expected standard. The report is very brief, "
            "lacks almost all required analytical content, and does not demonstrate engagement with "
            "the assignment brief. The dataset is named but not described or justified, no cleaning "
            "steps are documented, statistics are absent, and the single visualisation is described "
            "as unreadable. This work requires a substantial resubmission to meet course requirements."
        ),
        "strengths": [
            "A dataset was identified and named, showing awareness of the first step",
            "An attempt at a visualisation was made, indicating some familiarity with charting tools",
        ],
        "areas_for_improvement": [
            "Dataset is not described — number of rows, columns, features, and source are missing",
            "No justification for dataset choice",
            "No data cleaning steps performed or mentioned",
            "Descriptive statistics are entirely absent",
            "Only one visualisation attempted; the rubric requires at least five distinct chart types",
            "Conclusions are vague ('some are better than others') with no data support",
            "No code or code documentation provided",
        ],
        "criteria": [
            {"name": "Dataset Selection & Justification", "max_points": 10, "awarded_points": 2,
             "feedback": "A movies dataset is mentioned but no source, size, or feature list is provided. No justification is given for why this dataset was chosen. The rubric requires 2-3 sentences of justification and basic dataset description."},
            {"name": "Data Cleaning & Preprocessing", "max_points": 20, "awarded_points": 0,
             "feedback": "No data cleaning is described or performed. The report does not mention missing values, outliers, or data types. This criterion scores zero as there is no evidence of any preprocessing work."},
            {"name": "Descriptive Statistics", "max_points": 20, "awarded_points": 2,
             "feedback": "Only one average value (6.5) is mentioned without context. No median, standard deviation, skewness, or kurtosis. The rubric requires these statistics for at least 5 numerical features with interpretation. This criterion is effectively unaddressed."},
            {"name": "Visualisations", "max_points": 25, "awarded_points": 8,
             "feedback": "One bar chart is mentioned but described as 'hard to read', which suggests it was not properly formatted or labelled. The rubric requires 5 distinct chart types, each with a written insight. Only 1 of 5 required charts is present, and it lacks any analytical explanation."},
            {"name": "Insights & Conclusions", "max_points": 15, "awarded_points": 5,
             "feedback": "The conclusion ('movies have different ratings, some are better than others') is a restatement of the obvious and is not a data-derived analytical insight. The rubric requires 3-5 specific findings supported by the statistical analysis and visualisations."},
            {"name": "Code Quality & Documentation", "max_points": 10, "awarded_points": 5,
             "feedback": "No code is included in the submission. It is unclear whether Python was used at all. The rubric requires well-commented Python code as part of the deliverable. Without code, this criterion cannot be fully assessed."},
        ],
        "actionable_suggestions": (
            "1. Start over with a clearly described, publicly available dataset (try Kaggle or UCI ML Repository). "
            "Include the dataset name, URL, number of rows/columns, and 2-3 sentences justifying your choice.\n"
            "2. Document every cleaning step: check for nulls with df.isnull().sum(), handle them with imputation "
            "or justified removal, and validate dtypes with df.dtypes.\n"
            "3. Use df.describe() and df.skew() to compute all required statistics for at least 5 numerical "
            "features. Write one sentence interpreting each result.\n"
            "4. Create all 5 required chart types: histogram, box plot, scatter plot, heatmap, and bar chart — "
            "each with a title, axis labels, and a written insight.\n"
            "5. Include your Python code (or Jupyter Notebook output) in the submission with inline comments "
            "explaining what each section does."
        ),
    },
]


# ── Run the pipeline ──────────────────────────────────────────────────────────

def run_mock_test():
    print("\n" + "="*60)
    print("  AI Grading Assistant — MOCK TEST (no API key needed)")
    print("="*60)

    # Step 1: Load documents to verify they're readable
    print("\n[1/3] Loading sample documents...")
    base = os.path.join(os.path.dirname(__file__), "sample_data")

    instructions_text = read_document(os.path.join(base, "assignment_instructions.docx"))
    print(f"  ✓  Instructions loaded  ({len(instructions_text):,} chars)")

    rubric_text = read_document(os.path.join(base, "grading_rubric.docx"))
    print(f"  ✓  Rubric loaded        ({len(rubric_text):,} chars)")

    submissions = load_student_submissions(os.path.join(base, "student_submissions"))
    print(f"  ✓  {len(submissions)} student submissions loaded:")
    for s in submissions:
        print(f"      • {s['name']}  ({len(s['text']):,} chars)")

    # Step 2: Use mock results (skip real API)
    print("\n[2/3] Applying mock grading results (no API call)...")
    for r in MOCK_RESULTS:
        print(f"  ✓  {r['student_name']}:  {r['total_score']}/100  ({r['letter_grade']})")

    # Step 3: Generate all reports
    print("\n[3/3] Generating reports...")
    output_dir = os.path.join(base, "grading_output")

    # Per-student feedback files
    feedback_dir = os.path.join(output_dir, "student_feedback")
    for r in MOCK_RESULTS:
        path = write_student_feedback(r, feedback_dir)
        print(f"  ✓  {os.path.basename(path)}")

    # CSV summary
    csv_path = write_csv_summary(MOCK_RESULTS, output_dir)
    print(f"  ✓  {os.path.basename(csv_path)}")

    # HTML dashboard
    html_path = write_html_report(MOCK_RESULTS, output_dir, "Assignment 1: EDA with Python")
    print(f"  ✓  {os.path.basename(html_path)}")

    print("\n" + "="*60)
    print("  Mock test complete! All output files generated.")
    print(f"  Output folder: {output_dir}")
    print("="*60 + "\n")

    return output_dir, csv_path, html_path, feedback_dir


if __name__ == "__main__":
    run_mock_test()
