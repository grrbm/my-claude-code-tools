# Implement a Linear Task

Trigger:
When I ask to implement a Linear task and provide a Linear issue URL.

Workflow:

1. Parse the Linear issue URL.
2. Fetch the issue details from Linear.
3. Fetch all comments from the issue.
4. Checkout `main`.
5. Pull the latest `main` from origin.
6. Create a branch from the updated `main` using:

feat/<issue-key-lowercase>-<kebab-case-title>

Example:
feat/sho-114-cart-replace-hardcoded-tax-and-shipping-pricing

7. Checkout the new branch.
8. Review the issue description and all comments carefully.
9. Use the latest clarified requirements from the task discussion.
10. Start implementing the feature.

Rules:

- Always base the branch on the latest `main`.
- Always read the Linear task before coding.
- Always read all Linear comments before coding.
- Do not skip clarifying comments or implementation notes.
- Do not ask me whether to checkout `main` or pull first; do it automatically.
- Do not ask me whether to create the branch; do it automatically.
- Start implementation after the branch is ready and the task context is fully read.
- If there is an existing local branch for the same issue, mention it before creating a duplicate.
- If access/authentication fails, explain the exact missing command, credential, or permission.
