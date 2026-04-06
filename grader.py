"""
grader.py
---------
Core grading engine powered by the Anthropic Claude API.

For each student submission it:
  1. Sends the assignment instructions + rubric + student work to Claude
  2. Asks Claude to return a structured JSON grade + feedback object
  3. Validates and returns the parsed result
"""

import json
import re
import time
from typing import Dict, List, Optional

import anthropic


# ── Prompt templates ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert Teaching Assistant for the course "AI for Analytics".
Your job is to evaluate student assignments fairly, constructively, and consistently.

You MUST always respond with a valid JSON object and nothing else — no preamble, no markdown fences.

The JSON schema is:
{
  "student_name": "<string>",
  "total_score": <integer>,
  "max_score": <integer>,
  "percentage": <float, 1 decimal>,
  "letter_grade": "<A+|A|A-|B+|B|B-|C+|C|C-|D|F>",
  "overall_summary": "<2-4 sentence personalised overview of the student's work>",
  "strengths": ["<strength 1>", "<strength 2>", ...],
  "areas_for_improvement": ["<area 1>", "<area 2>", ...],
  "criteria": [
    {
      "name": "<criterion name from rubric>",
      "max_points": <integer>,
      "awarded_points": <integer>,
      "feedback": "<specific 2-3 sentence feedback for this criterion>"
    },
    ...
  ],
  "actionable_suggestions": "<3-5 concrete, numbered steps the student can take to improve>"
}

Grading guidelines:
- Be fair but rigorous. Do not inflate grades.
- Give PERSONALISED feedback that references the student's actual work.
- If a criterion is missing entirely from the submission, award 0 points and explain what was expected.
- Match the point values exactly to those specified in the rubric.
- The letter grade should follow standard academic conventions based on the percentage.
"""

USER_PROMPT_TEMPLATE = """Please grade the following student assignment.

═══════════════════════════════════════
ASSIGNMENT INSTRUCTIONS
═══════════════════════════════════════
{instructions}

═══════════════════════════════════════
GRADING RUBRIC
═══════════════════════════════════════
{rubric}

═══════════════════════════════════════
STUDENT: {student_name}
SUBMISSION FILE: {filename}
═══════════════════════════════════════
{submission}

Now evaluate this submission and return the JSON grade object.
"""


# ── Grade letter helper ───────────────────────────────────────────────────────

def percentage_to_letter(pct: float) -> str:
    """Convert a percentage score to a letter grade."""
    if pct >= 97:  return "A+"
    if pct >= 93:  return "A"
    if pct >= 90:  return "A-"
    if pct >= 87:  return "B+"
    if pct >= 83:  return "B"
    if pct >= 80:  return "B-"
    if pct >= 77:  return "C+"
    if pct >= 73:  return "C"
    if pct >= 70:  return "C-"
    if pct >= 60:  return "D"
    return "F"


# ── Main Grader class ─────────────────────────────────────────────────────────

class AssignmentGrader:
    """
    Orchestrates grading of multiple student submissions using Claude.

    Usage:
        grader = AssignmentGrader(api_key="sk-ant-...")
        results = grader.grade_all(
            instructions_text="...",
            rubric_text="...",
            submissions=[{"name": "Alice", "file": "alice.pdf", "text": "..."}]
        )
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    # ── Public API ────────────────────────────────────────────────────────────

    def grade_all(
        self,
        instructions_text: str,
        rubric_text: str,
        submissions: List[Dict],
        progress_callback=None,
    ) -> List[Dict]:
        """
        Grade all student submissions.

        Args:
            instructions_text:  Full text of the assignment instructions document.
            rubric_text:        Full text of the grading rubric document.
            submissions:        List of dicts from document_reader.load_student_submissions()
            progress_callback:  Optional callable(current, total, student_name) for progress updates.

        Returns:
            List of grading result dicts (one per student).
        """
        results = []
        total = len(submissions)

        for idx, submission in enumerate(submissions, start=1):
            if progress_callback:
                progress_callback(idx, total, submission["name"])

            result = self._grade_single(
                instructions_text=instructions_text,
                rubric_text=rubric_text,
                submission=submission,
            )
            results.append(result)

            # Small delay between API calls to be kind to rate limits
            if idx < total:
                time.sleep(0.5)

        return results

    def grade_single(
        self,
        instructions_text: str,
        rubric_text: str,
        submission: Dict,
    ) -> Dict:
        """Public wrapper for grading a single student (for interactive use)."""
        return self._grade_single(instructions_text, rubric_text, submission)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _grade_single(
        self,
        instructions_text: str,
        rubric_text: str,
        submission: Dict,
    ) -> Dict:
        """Grade one student submission with retry logic."""
        prompt = USER_PROMPT_TEMPLATE.format(
            instructions=instructions_text,
            rubric=rubric_text,
            student_name=submission["name"],
            filename=submission.get("file", "unknown"),
            submission=submission["text"],
        )

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw_text = response.content[0].text.strip()
                parsed = self._parse_response(raw_text, submission["name"])
                # Ensure student name is always set
                parsed["student_name"] = submission["name"]
                parsed["file"] = submission.get("file", "")
                return parsed

            except anthropic.RateLimitError:
                wait = self.retry_delay * attempt
                print(f"    Rate limited. Waiting {wait}s before retry {attempt}/{self.max_retries}...")
                time.sleep(wait)
                last_error = "Rate limit exceeded"

            except anthropic.APIError as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    break

            except Exception as e:
                last_error = str(e)
                break

        # If all retries failed, return an error result
        return self._error_result(submission["name"], submission.get("file", ""), last_error)

    def _parse_response(self, raw_text: str, student_name: str) -> Dict:
        """
        Parse Claude's JSON response. Handles edge cases where Claude
        accidentally wraps JSON in markdown code fences.
        """
        # Strip markdown fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON object using regex as fallback
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise ValueError(f"Could not parse JSON from Claude's response for '{student_name}'")

        # Fill in any missing fields with defaults
        data.setdefault("student_name", student_name)
        data.setdefault("total_score", 0)
        data.setdefault("max_score", 100)
        data.setdefault("criteria", [])
        data.setdefault("strengths", [])
        data.setdefault("areas_for_improvement", [])
        data.setdefault("overall_summary", "No summary provided.")
        data.setdefault("actionable_suggestions", "No suggestions provided.")

        # Compute percentage and letter grade if missing
        if data["max_score"] > 0:
            pct = round((data["total_score"] / data["max_score"]) * 100, 1)
        else:
            pct = 0.0
        data.setdefault("percentage", pct)
        data.setdefault("letter_grade", percentage_to_letter(pct))

        return data

    def _error_result(self, student_name: str, filename: str, error_msg: str) -> Dict:
        """Return a structured error result when grading fails."""
        return {
            "student_name": student_name,
            "file": filename,
            "total_score": 0,
            "max_score": 100,
            "percentage": 0.0,
            "letter_grade": "N/A",
            "overall_summary": f"Grading failed: {error_msg}",
            "strengths": [],
            "areas_for_improvement": [],
            "criteria": [],
            "actionable_suggestions": "Please re-run grading for this student.",
            "error": error_msg,
        }
