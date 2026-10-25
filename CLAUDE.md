# Development Rules

- Never create git commits unless explicitly requested. Invoking the `summarize-changes` skill counts as an explicit request to commit.
- When committing (including via `summarize-changes`), only commit what is already staged. Do not run `git add` on additional files to sweep in unstaged or untracked changes, even if they look related to the same task — leave non-staged changes untouched unless the user explicitly asks for them to be included.
- Never push to remote repositories.
- Never create, delete, or switch branches.
- Never create git worktrees. Work directly in this checkout, on whatever branch is already checked out. A new session should continue on the same branch rather than starting a fresh one.
- Never use `git stash` (including to temporarily revert a file for testing and restore it after). Plain `git stash pop` only restores the working tree, not the index, so it can silently drop staged changes you didn't make yourself. To test before/after behavior, round-trip the file content through the Edit/Write tool instead, or use `git diff`/`git apply` to a patch file — neither touches the index.
- Commit messages must not include a `Co-Authored-By` line.
- After code modifications, stop and wait for review.
