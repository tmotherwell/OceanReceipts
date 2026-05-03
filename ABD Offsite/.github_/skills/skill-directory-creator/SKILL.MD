---
name: skill-directory-creator
description: Scaffolds a skill directory with standard folders and starter docs.
---

## Summary
Create a reproducible skill scaffold in a chosen parent folder. The scaffold includes standard subfolders, placeholder files, and a starter `SKILL.MD` + `README.MD` to document the new skill.

## Purpose
Provide a lightweight, opinionated template for creating new "skills" (agent customization packages). This reduces setup time and ensures consistency across skills in a workspace.

## Inputs
- parent_directory (required): absolute or workspace-relative path where the new skill folder will be created.
- skill_name (required): kebab-case name for the skill (e.g., `my-new-skill`).
- options (optional):
  - force: boolean, overwrite existing skill folder if present.
  - license: string, include a basic LICENSE file (MIT/Apache/etc).
  - git: boolean, initialize a git repo and add `.gitignore`.

## Output
A new folder at `parent_directory/skill_name` (or an updated folder if `force` is used) containing:
- input/
- output/
- context/
- references/
- assets/
- scripts/
- README.MD (starter)
- SKILL.MD (this file, personalized)

## Workflow (step-by-step)
1. Validate inputs:
	- Confirm `parent_directory` exists and is writable (or ask to create it).
	- Validate `skill_name` against the kebab-case pattern: `^[a-z0-9]+(-[a-z0-9]+)*$`.
2. Resolve destination: `dest = parent_directory/skill_name`.
3. Conflict resolution:
	- If `dest` exists and `force` is false, prompt user to choose: abort / merge / overwrite.
4. Create directories (atomic or best-effort):
	- Create the six standard folders and any requested extras.
5. Create files:
	- Write `README.MD` with a short description and next steps.
	- Write `SKILL.MD` populated with the template below and the exact inputs used.
	- Optionally create `scripts/create-structure.sh` and a minimal `.gitignore`.
6. Verify:
	- Ensure all items were written successfully; return a summary of created paths.

## Decision points and branching logic
- Existing destination: abort, merge, or overwrite.
- Invalid skill_name: attempt a safe normalization (lowercase, replace spaces/underscores with `-`); if normalization changes the input, report and confirm with the user.
- Parent directory missing: create it (if permitted) or abort with instructions.

## Quality criteria / Completion checks
- All listed directories exist.
- `README.MD` and `SKILL.MD` contain the required headings (Summary, Purpose, Inputs, Workflow, Examples).
- File permissions are set so the user can modify files.
- A short verification report is returned after creation.

## Example prompts (assistant)
- "Create a new skill named `skill-directory-creator` under `/Users/you/projects/skills`."
- "Create `analytics-skill` in the current folder and overwrite if it exists."

## Template snippets

README.MD (starter)

> # skill-directory-creator
>
> Short description: scaffolds a skill directory with standard folders and starter docs.
>
> Created by: [your name]
> Inputs: parent_directory, skill_name
>
> Next steps:
> - Customize `SKILL.MD` with the workflow that this skill will automate.
> - Add assets, test data, and scripts in their respective folders.

SKILL.MD (this file will be updated for each created skill)

 - Purpose: explain what the skill automates
 - Inputs: list and explain required inputs
 - Outputs: list files/folders created
 - Workflow: step-by-step instructions the agent follows
 - Examples: sample prompts and usage
 - Questions: clarifying questions the skill should ask the user

## Questions for the user (ambiguities to resolve)
1. Should the skill initialize a git repository (`git: true`)?
2. Include a license file? If yes, which license (MIT/Apache-2.0)?
3. Preferred default templates for README and SKILL (short vs. long)?

## Related customizations / follow-ups
- Add language-specific scaffolds (Python, Node, terraform).
- Add CI templates (GitHub Actions) and test-harness templates.

## Troubleshooting
- Permission denied creating folders: suggest running with elevated permissions or choosing a different parent directory.
- Invalid skill name: show normalization and ask for confirmation.

## Verification / test
- After running, the agent should return a JSON-like summary of created paths and any conflicts resolved.

## Author / changelog
Created by: assistant — created from conversation on 2026-04-09.
