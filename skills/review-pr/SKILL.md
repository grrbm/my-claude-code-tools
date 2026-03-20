---
name: review-pr
description: Review a GitHub pull request. Use when asked to review a PR or given a PR URL to review. Reads the full diff, all existing comments and reviews, and posts a single consolidated review comment.
argument-hint: <pr-url>
allowed-tools: Bash(gh *)
---

Review the pull request at: $ARGUMENTS

Workflow:

1. Parse the PR URL to determine owner, repository, and pull request number.

2. Collect PR information:
   - title, description, changed files, full diff (`gh pr view`, `gh pr diff`)
   - existing issue comments (`gh api repos/<owner>/<repo>/issues/<number>/comments`)
   - existing review comments (`gh api repos/<owner>/<repo>/pulls/<number>/comments`)
   - all submitted reviews (`gh api repos/<owner>/<repo>/pulls/<number>/reviews`)

3. Read the entire diff before writing the review.

4. Read all previous comments and reviews first.

5. Verify whether previously reported issues are already resolved.

6. Write a consolidated review comment.

Requirements:

- Always read the diff before reviewing.
- Always read previous comments and reviews.
- Do not repeat feedback unless it is still unresolved.
- Base the review on the latest version of the PR.
- Focus on: bugs, regressions, edge cases, security, performance, maintainability, architecture.

Severity system:

Label every issue with one of the following severities:

- **[blocking]** — Must be fixed before merge. Bugs, regressions, security issues, data loss risks, or explicit violations of CLAUDE.md conventions.
- **[important]** — Should be fixed but won't block merge. Significant maintainability, performance, or correctness concerns.
- **[nit]** — Minor style, naming, or readability issue. Optional to address.

Do not invent issues to fill sections. Omit a section entirely if there is nothing to report.

Comment template:

Post the review using this exact structure:

```
## PR Review

### 📋 Summary
<1–3 sentence overview of what the PR does and your overall assessment.>

### 🚨 Blocking
<List of [blocking] issues. Each item: file path + line reference, clear description, and suggested fix.>
<If none: omit this section.>

### ⚠️ Important
<List of [important] issues with file path + line reference and explanation.>
<If none: omit this section.>

### 🔍 Nits
<List of [nit] items, grouped or brief.>
<If none: omit this section.>

### ✅ Strengths
<1–3 things done well. Always include this section.>
```

Posting behavior:
- Post a single consolidated PR comment via `gh pr comment` using the template above.
- Only submit an official GitHub review (Approve / Request changes) if explicitly asked.
