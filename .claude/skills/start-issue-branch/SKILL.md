---
name: start-issue-branch
description: Start work on a GitHub issue following the team's Git Flow - create the feature branch from an up-to-date develop and scaffold its spec. Use when asked to start, pick up or develop an issue.
---

# Start an issue branch

Input: an issue number.

1. Read the issue: `gh issue view <n>`. Note title, tasks, acceptance criteria,
   assignee and dependencies. If it depends on an unmerged issue, tell the user
   and ask whether to stack the branch on that one.
2. Check the working tree: `git status --short`. Leave unrelated local changes
   alone; never stash or discard them without asking.
3. Update the base: `git fetch origin`.
4. Create the branch from the remote integration branch:
   `git checkout -b feature/<n>-<short-kebab-description> origin/develop`
   - 2 to 4 words, lowercase, derived from the issue title.
   - `fix/<n>-<description>` for bug fixes.
5. Write the spec with the `write-branch-spec` skill before any code.
6. Do not push and do not open a Pull Request unless the user asks.

When the work is done, commit by explicit path with a Conventional Commit:

```bash
git add <path> [<path> ...]
git commit -m "<type>(<scope>): <imperative subject>" -- <path> [<path> ...]
```

Passing the paths to `git commit` keeps unrelated staged files out of the commit.
