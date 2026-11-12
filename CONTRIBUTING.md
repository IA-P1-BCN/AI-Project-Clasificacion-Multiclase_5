# Contributing Guide

This document defines the Git workflow and commit convention for the project.

## Branch model

We use a simplified **Git Flow**:

| Branch | Purpose |
|---|---|
| `main` | Stable, release-ready code. **Protected** — no direct commits. |
| `develop` | Integration branch. All features merge here first. |
| `feature/<name>` | New work. Branches **off `develop`**, merges back into `develop`. |

Examples of feature branch names:

```
feature/m0-docker-infra
feature/m2-eda
fix/model-overfitting
```

### Typical flow

```bash
git checkout develop
git pull
git checkout -b feature/my-task
# ... work & commit ...
git push -u origin feature/my-task
# open a Pull Request:  feature/my-task  ->  develop
```

- Open a **Pull Request** into `develop`; at least one teammate reviews it.
- `develop` is merged into `main` at milestone deliveries.

## Commit convention — Conventional Commits

Format:

```
<type>(<optional scope>): <short description in imperative mood>
```

**Types**

| Type | Use for |
|---|---|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `chore` | Tooling, config, scaffolding, dependencies |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or fixing tests |
| `style` | Formatting, no code-meaning change |
| `ci` | CI/CD configuration |

**Examples**

```
feat(app): add prediction form to Streamlit UI
fix(preprocessing): handle missing values in scaler
docs(readme): expand setup instructions
chore(docker): add Dockerfile and docker-compose
```

Keep the subject line under ~72 characters and write it in the imperative
("add", not "added"/"adds").
