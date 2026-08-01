# Eldritch Harvester: Engineering Contribution Guidelines

This document outlines the branch taxonomy, commit message standards, and development workflows required to maintain high codebase hygiene, automated changelog generation, and clean system traceability across the **Eldritch Harvester** component of the Works-by-Worrell (WBW) platform.

---

## 1. Branch Strategy & Taxonomy

All development work MUST occur on a feature or task branch before targeting the `main` branch. All branches MUST align with one of the following prefix categories:

### Branch Prefix Categories

*   `feat/` - Application feature delivery
*   `infra/` - Declarative infrastructure and cloud configurations
*   `fix/` - Immediate bug triage, error corrections, and hotfixes
*   `test/` - Verification frameworks, mock configurations, and test suite enhancements
*   `docs/` - Runbook updates, architectural design documents, ADRs, and blueprints
*   `chore/` - Maintenance, dependency updates, and workspace configuration adjustments

### Branch Naming Convention

All branches MUST follow this format: 
`<type>/issue-<id>-<description>` or `<type>/phase<num>-<short-description>`

**Examples:**
*   `feat/issue-4-github-api`
*   `docs/phase1-git-hygiene`

---

## 2. Commit Message Conventions

We strictly adhere to the [Conventional Commits](https://www.conventionalcommits.org/) specification. This enables automated release notes, changelog generation, and clear system auditability.

### Commit Format

Commit messages MUST follow the structure:
```
<type>(<scope>): <short description>

[Optional body explaining design rationale or context]

[Optional footer(s) for issue linking, e.g., Closes #12]
```

### Approved Commit Types

*   `feat`: A new user-facing or platform-facing feature.
*   `fix`: A bug fix or patch.
*   `infra`: Infrastructure or CI/CD changes.
*   `docs`: Documentation-only modifications.
*   `test`: Adding missing tests or correcting existing tests.
*   `chore`: Maintenance tasks, dependency updates, directory restructures.

### Scope Boundaries (Repository Specific)

When writing a commit, the `scope` MUST represent the logical area of the target repository being modified. Select the appropriate scope for the repository you are contributing to:

| Repository | Valid Scope Boundaries | Example Commit |
| :--- | :--- | :--- |
| **eldritch-harvester** | `scraper`, `llm`, `queue`, `mcp`, `chore`, `gov` | `feat(llm): update gemini extraction prompt schema (#1)` |

---

## 3. Pull Request & Code Hygiene Guidelines

Before submitting a Pull Request for review:

1.  **Branch Check:** Ensure your branch name aligns with the naming taxonomy.
2.  **Commit Hygiene:** Squash intermediate, redundant, or "work-in-progress" commits before requesting review. Every commit on the main branch SHOULD represent a deployable state.
3.  **Traceability Linkage:** Link associated GitHub issues or project cards in the PR description using standard closing keywords (e.g., `Closes #4` or `Fixes #7`).
