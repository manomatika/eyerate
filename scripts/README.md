# EyeRate Automation Scripts

This folder contains scripts to automate the development 
lifecycle of EyeRate.

## Prerequisites

- GitHub CLI (gh): Must be installed and authenticated
- Git: Must be configured locally
- Python 3.x: With PyYAML installed (pip install PyYAML)

---

## Starting a New Milestone

The start_milestone.py script automates creation of a GitHub
Milestone, a dedicated feature branch, and all associated 
issues defined in milestone_tasks.yaml.

### Instructions:
1. Update milestone_tasks.yaml:
   - Set the milestone name
   - Set the version (e.g. 0.0.4-dev)
   - Set the branch name
   - Update the description
   - List all issues with title, labels, and body
2. Run the script:
   PYTHONPATH=src:../matika/src .venv/bin/python scripts/start_milestone.py
3. Review the plan and confirm with y

### Files to update for each milestone:

| File | Purpose |
| :--- | :--- |
| VERSION | Updated automatically by start_milestone.py |
| scripts/milestone_tasks.yaml | Define milestone, branch, and issues |

---

## Notes

- VERSION is bumped automatically by start_milestone.py
- Do not manually edit VERSION when starting a new milestone
- All git operations except merge and rm -rf are permitted
