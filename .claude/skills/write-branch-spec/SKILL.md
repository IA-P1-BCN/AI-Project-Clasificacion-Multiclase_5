---
name: write-branch-spec
description: Write or update the spec file of the current branch in specs/, using the project template and ontology. Use before implementing a branch and again when closing it.
---

# Write the branch spec

1. Get the branch: `git branch --show-current`. The spec path is
   `specs/<branch with "/" replaced by "-">.md`.
2. Read `specs/ontology.md` and the template in `specs/README.md`.
3. Read the issue (`gh issue view <n>`) and copy its acceptance criteria
   verbatim into the spec; add criteria only when they make "done" testable.
4. Fill in:
   - **Goal**: what changes and why, in one or two sentences.
   - **Scope**: in scope, and out of scope with the issue number that owns it.
   - **Design**: files, public functions, each decision with its reason and
     the evidence (usually a section of `docs/EDA.md`).
   - **Verification**: exact commands and expected results.
5. Use ontology terms and identifiers. If you need a new term, add it to
   `specs/ontology.md` in the same branch.
6. When closing the branch, tick only the criteria you verified by running
   the verification commands, and record the observed results.
