---
name: prd-analyzer
description: "**WORKFLOW SKILL** — Analyze Product Requirement Documents (PRDs) and extract the canonical answers: customer, goal, constraints, major features, and key partners. Use when you have a PRD in the repo or attached in chat."
applyTo:
  - "analyze-prd/input/**"
  - "analyze-prd/**"
author: GitHub Copilot
version: 0.1.0
defaults:
  auto_save: true
  granularity: detailed
  output_dir: analyze-prd/output/
---

# PRD Analyzer

## Summary

`prd-analyzer` is a reusable workflow skill that reads a product requirements document (PRD) and produces a concise analysis answering these five questions:

- Who is the customer?
- What is the goal?
- What are the constraints?
- What are the major features needed?
- Who are the key partners?

The skill produces a short markdown analysis file and cites the source PRD.

## When To Use
- You have a PRD in `analyze-prd/input/` (or attached) and need a quick, consistent summary to hand to product, engineering, or stakeholders.

## When Not To Use
- Extremely short notes or fragmented requirements with no coherent narrative — in that case request clarification from the author first.

## Decision Points
- If multiple PRDs are supplied, ask which to analyze or run separately per-file.
- If items are ambiguous or absent, list them as "Missing / Ambiguous" and prepare targeted clarifying questions.
- Choose output granularity: `brief` (one-liners per question) vs `detailed` (supporting quotes and suggested next steps).

## Step-by-step Workflow
1. Accept input: workspace path (recommended) or pasted/attached PRD text. If multiple candidates exist, confirm target file.
2. Parse the document and identify canonical sections (Overview, Problem Statement, Target Audience, Proposed Solution, Success Metrics, Timeline).
3. Extract answers for each of the five canonical questions. For each answer include:
   - A concise summary (1–3 lines).
   - Supporting evidence: a short quote or reference to the source section.
4. Detect constraints (technical, timeline, platform, compliance) by scanning sections named "Constraints", "Timeline", "Timeline & Milestones", or references under "Backend Integration" and "Security".
5. Infer major features from "Proposed Solution", "Key Data Points", "Experiment Plan", and any feature lists. Normalize feature names into short bullets.
6. Identify key partners / stakeholders by scanning mentions of teams, vendors, gateways, or compliance groups.
7. Run quality checks (see below). If checks fail or items are missing, append a short "Ambiguities / Questions" section and prompt the user for clarifications.
8. Write the analysis to `analyze-prd/output/` using the filename pattern `<PRD_BASENAME>_ANALYSIS.md` and include a source link to the input PRD.

## Inputs & Options
- `input_path` (optional): workspace-relative PRD path. If omitted, prompt user for attachment/text.
- `output_dir` (optional): default `analyze-prd/output`.
- `granularity`: `brief` | `detailed` (default: `detailed`).
- `auto_save`: `true` | `false` (default: `true`) — when `true` the analysis is written automatically to `analyze-prd/output/`.

## Outputs
- Markdown file with sections: Summary, Customer, Goal, Constraints, Major Features, Key Partners, Ambiguities, Recommended Next Steps. File saved to `analyze-prd/output/<PRD_BASENAME>_ANALYSIS.md`.

## Quality Criteria (Completion Checks)
- Each of the five canonical answers exists (or is explicitly marked "missing").
- Each extracted answer contains at least one supporting quote or section reference when granularity=`detailed`.
- Output file includes a source link to the original PRD.
- If confidence is low for any item, that item is marked and accompanied by a clarifying question.

## Example Prompts / Invocations
- "Analyze the PRD at analyze-prd/input/Bill_Payment_Status_Tracking_PRD.md and save a detailed analysis to analyze-prd/output."
- "Run `prd-analyzer` on the latest PRD in analyze-prd/input and return brief answers only."

## Implementation Notes (for authors)
- Prefer workspace-relative paths in prompts to ensure deterministic behavior.
- Use the filename pattern to avoid overwriting existing analyses.
- When extracting supporting evidence include short excerpts (<= 2 lines) and the section heading if available.

## Ambiguities / Questions (to ask the user)
- Do you want the skill to also produce a task/checklist or map features to epics or acceptance criteria?
 
**Defaults set:** auto-save enabled; granularity = detailed; output written to `analyze-prd/output/`.

## Suggested Follow-ups
- Add an automation that runs the skill on new PRDs dropped into `analyze-prd/input/` and opens a draft PR with the analysis.
- Provide a prompt template in your user prompts folder for non-technical stakeholders to request analyses.

---
End of SKILL.md
