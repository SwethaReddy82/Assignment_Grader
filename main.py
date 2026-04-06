#!/usr/bin/env python3
"""
main.py
-------
AI Grading Assistant for Teaching Assistants — AI for Analytics Course
----------------------------------------------------------------------
Reads assignment instructions, a grading rubric, and a folder of student
submissions (PDF or DOCX), then uses Claude to produce:

  •  Personalised per-student feedback (.txt)
  •  A class-wide CSV summary spreadsheet
  •  An interactive HTML dashboard

Usage (interactive):
    python main.py

Usage (command-line):
    python main.py \\
        --instructions path/to/instructions.pdf \\
        --rubric       path/to/rubric.docx \\
        --submissions  path/to/students_folder/ \\
        --output       path/to/output_folder/ \\
        --assignment   "Assignment 1: Data Preprocessing" \\
        --api-key      sk-ant-...
"""

import argparse
import os
import sys
from pathlib import Path


def _load_env_file():
    """Load a .env file in the same folder as main.py (if it exists)."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value

_load_env_file()

# ── Dependency check ──────────────────────────────────────────────────────────
def _check_dependencies():
    missing = []
    for pkg, import_name in [
        ("anthropic",     "anthropic"),
        ("pdfplumber",    "pdfplumber"),
        ("python-docx",   "docx"),
        ("rich",          "rich"),
    ]:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("❌  Missing packages. Please run:\n")
        print(f"    pip install {' '.join(missing)}\n")
        sys.exit(1)

_check_dependencies()

# ── Imports (after dependency check) ─────────────────────────────────────────
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import print as rprint

from document_reader import read_document, load_student_submissions
from grader import AssignmentGrader
from report_generator import (
    write_student_feedback,
    write_csv_summary,
    write_html_report,
)

console = Console()


# ── Banner ────────────────────────────────────────────────────────────────────

def print_banner():
    console.print(Panel.fit(
        "[bold purple]🎓  AI Grading Assistant[/bold purple]\n"
        "[dim]Powered by Claude · AI for Analytics Course[/dim]",
        border_style="purple",
        padding=(1, 4),
    ))


# ── Interactive prompts ───────────────────────────────────────────────────────

def prompt_for_inputs() -> dict:
    """Walk the TA through file selection interactively."""
    console.print("\n[bold]Step 1: Assignment Instructions[/bold]")
    instructions_path = Prompt.ask(
        "  Path to instructions file [dim](PDF or DOCX)[/dim]"
    ).strip().strip('"')

    console.print("\n[bold]Step 2: Grading Rubric[/bold]")
    rubric_path = Prompt.ask(
        "  Path to rubric file [dim](PDF or DOCX)[/dim]"
    ).strip().strip('"')

    console.print("\n[bold]Step 3: Student Submissions[/bold]")
    submissions_folder = Prompt.ask(
        "  Path to submissions folder [dim](containing all student files)[/dim]"
    ).strip().strip('"')

    console.print("\n[bold]Step 4: Output Folder[/bold]")
    default_output = str(Path(submissions_folder).parent / "grading_output")
    output_folder = Prompt.ask(
        "  Where should reports be saved?",
        default=default_output,
    ).strip().strip('"')

    console.print("\n[bold]Step 5: Assignment Name[/bold]")
    assignment_name = Prompt.ask(
        "  Assignment name (for reports)",
        default="Assignment",
    ).strip()

    console.print("\n[bold]Step 6: Anthropic API Key[/bold]")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        console.print("  [green]✓  Found ANTHROPIC_API_KEY in environment.[/green]")
    else:
        api_key = Prompt.ask(
            "  Enter your Anthropic API key [dim](starts with sk-ant-)[/dim]",
            password=True,
        ).strip()

    return {
        "instructions_path": instructions_path,
        "rubric_path": rubric_path,
        "submissions_folder": submissions_folder,
        "output_folder": output_folder,
        "assignment_name": assignment_name,
        "api_key": api_key,
    }


# ── Core grading pipeline ─────────────────────────────────────────────────────

def run_grading_pipeline(
    instructions_path: str,
    rubric_path: str,
    submissions_folder: str,
    output_folder: str,
    assignment_name: str,
    api_key: str,
):
    """Full grading pipeline: read → grade → report."""

    # 1. Load documents
    console.print("\n[bold cyan]📄  Loading documents...[/bold cyan]")
    with console.status("Reading assignment instructions..."):
        instructions_text = read_document(instructions_path)
        console.print(f"  [green]✓[/green]  Instructions loaded ({len(instructions_text):,} chars)")

    with console.status("Reading grading rubric..."):
        rubric_text = read_document(rubric_path)
        console.print(f"  [green]✓[/green]  Rubric loaded ({len(rubric_text):,} chars)")

    with console.status("Loading student submissions..."):
        submissions = load_student_submissions(submissions_folder)

    if not submissions:
        console.print("[bold red]No student submissions found! Check the folder path and file types.[/bold red]")
        sys.exit(1)

    console.print(f"  [green]✓[/green]  Found [bold]{len(submissions)}[/bold] student submissions:")
    for s in submissions:
        console.print(f"      • {s['name']}  [dim]({s['file']})[/dim]")

    # Confirm before proceeding
    console.print()
    if not Confirm.ask(f"Grade [bold]{len(submissions)}[/bold] submissions using Claude?", default=True):
        console.print("[yellow]Grading cancelled.[/yellow]")
        sys.exit(0)

    # 2. Grade all submissions
    console.print("\n[bold cyan]🤖  Grading with Claude...[/bold cyan]")
    grader = AssignmentGrader(api_key=api_key)
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Grading submissions...", total=len(submissions))

        def on_progress(current, total, student_name):
            progress.update(task, completed=current - 1, description=f"Grading: {student_name}")

        results = grader.grade_all(
            instructions_text=instructions_text,
            rubric_text=rubric_text,
            submissions=submissions,
            progress_callback=on_progress,
        )
        progress.update(task, completed=len(submissions), description="All submissions graded!")

    # 3. Show quick results table
    _print_results_table(results)

    # 4. Generate reports
    console.print("\n[bold cyan]📊  Generating reports...[/bold cyan]")
    feedback_dir = os.path.join(output_folder, "student_feedback")

    with console.status("Writing per-student feedback files..."):
        feedback_paths = []
        for r in results:
            p = write_student_feedback(r, feedback_dir)
            feedback_paths.append(p)
        console.print(f"  [green]✓[/green]  {len(feedback_paths)} feedback files → [dim]{feedback_dir}[/dim]")

    with console.status("Writing CSV summary..."):
        csv_path = write_csv_summary(results, output_folder)
        console.print(f"  [green]✓[/green]  CSV summary → [dim]{csv_path}[/dim]")

    with console.status("Generating HTML dashboard..."):
        html_path = write_html_report(results, output_folder, assignment_name)
        console.print(f"  [green]✓[/green]  HTML report → [dim]{html_path}[/dim]")

    # 5. Done!
    console.print(Panel(
        f"[bold green]✅  Grading complete![/bold green]\n\n"
        f"[white]Students graded :[/white] {len(results)}\n"
        f"[white]Feedback files  :[/white] {feedback_dir}/\n"
        f"[white]CSV summary     :[/white] {csv_path}\n"
        f"[white]HTML dashboard  :[/white] {html_path}",
        border_style="green",
        title="Done",
        padding=(1, 2),
    ))


def _print_results_table(results):
    """Print a quick summary table to the terminal."""
    table = Table(title="Grading Results", show_header=True, header_style="bold cyan")
    table.add_column("Student", style="bold", min_width=20)
    table.add_column("Score", justify="right")
    table.add_column("Grade", justify="center")
    table.add_column("Summary (preview)", max_width=45)

    for r in results:
        grade = r.get("letter_grade", "N/A")
        score_str = f"{r.get('total_score', 0)}/{r.get('max_score', 100)} ({r.get('percentage', 0)}%)"
        summary = (r.get("overall_summary", "")[:90] + "…") if r.get("overall_summary") else ""
        grade_color = {
            "A": "green", "B": "blue", "C": "yellow", "D": "red", "F": "bright_red"
        }.get(grade[0] if grade else "N", "white")
        table.add_row(
            r.get("student_name", ""),
            score_str,
            f"[{grade_color}]{grade}[/{grade_color}]",
            summary,
        )

    console.print()
    console.print(table)


# ── CLI argument parsing ──────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Grading Assistant for Teaching Assistants",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--instructions", help="Path to assignment instructions (PDF or DOCX)")
    parser.add_argument("--rubric",       help="Path to grading rubric (PDF or DOCX)")
    parser.add_argument("--submissions",  help="Path to folder containing student submissions")
    parser.add_argument("--output",       help="Path to output folder for reports", default="./grading_output")
    parser.add_argument("--assignment",   help="Assignment name (used in reports)", default="Assignment")
    parser.add_argument("--api-key",      help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    return parser.parse_args()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print_banner()
    args = parse_args()

    # Decide: interactive or CLI mode
    if args.instructions and args.rubric and args.submissions:
        # Full CLI mode
        api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            console.print("[red]Error: No API key provided. Use --api-key or set ANTHROPIC_API_KEY.[/red]")
            sys.exit(1)
        run_grading_pipeline(
            instructions_path=args.instructions,
            rubric_path=args.rubric,
            submissions_folder=args.submissions,
            output_folder=args.output,
            assignment_name=args.assignment,
            api_key=api_key,
        )
    else:
        # Interactive mode
        console.print("\n[dim]Welcome! Let's set up the grading session.[/dim]")
        try:
            inputs = prompt_for_inputs()
            run_grading_pipeline(**inputs)
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Goodbye![/yellow]")
            sys.exit(0)


if __name__ == "__main__":
    main()
