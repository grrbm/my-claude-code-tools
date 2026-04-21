---
name: linear-implement-task
description: Implement a Linear task given its URL. Use when asked to implement a Linear task or given a Linear issue URL. Fetches the issue and all comments, creates a branch from main, then implements the feature.
argument-hint: <linear-issue-url>
allowed-tools: Bash(curl *), Bash(git *), Read, Glob, Grep, Edit, Write
---

Implement the Linear task at: $ARGUMENTS

Workflow:

1. Parse the Linear issue URL.
2. Read the `LINEAR_API_KEY` by running:
   ```bash
   grep '^LINEAR_API_KEY=' /Users/guilhermereis/Desktop/clones/shopit-monorepo/.env.local | tail -1 | cut -d'=' -f2
   ```
   Use this value directly in the Authorization header — never use `$LINEAR_API_KEY` from the environment, as it may be stale.
3. Fetch the issue details from Linear using the key from step 2.
4. Fetch all comments from the issue.
4. Checkout `main` and pull the latest from origin.
5. Create a branch from the updated `main` using:

   ```
   feat/<issue-key-lowercase>-<kebab-case-title>
   ```

   Example: `feat/sho-114-cart-replace-hardcoded-tax-and-shipping-pricing`

6. Checkout the new branch.
7. Review the issue description and all comments carefully — use the latest clarified requirements from the task discussion.
8. Implement the feature.

Rules:

- Always base the branch on the latest `main`.
- Always read the Linear task and all comments before coding.
- Do not skip clarifying comments or implementation notes.
- Do not ask whether to checkout `main`, pull, or create the branch — do it automatically.
- Start implementation after the branch is ready and task context is fully read.
- If an existing local branch for the same issue exists, mention it before creating a duplicate.
- If access/authentication fails, explain the exact missing command, credential, or permission.
