# Project Workflow

This workflow is a customized copy of the Conductor default workflow.
Changes from the default:

- One commit for each phase, not for each task.
- Code coverage target is 70 percent.
- No git notes. Task and phase summaries go into `plan.md`.
- Sections for mobile, databases, and deployment are removed. They do not apply to this demo.

The project root is `gemini_decisions_api/`. This folder is one demo in the `agentic-demos`
repository. All commands in this file run from the project root.

## Guiding Principles

1. **The plan is the source of truth.** Record all work in `plan.md`.
2. **The tech stack is deliberate.** Record a change to the stack in `tech-stack.md`
   before you implement it.
3. **Test-driven development.** Write unit tests before the code.
4. **Code coverage.** The target is 70 percent or more for each module.
5. **The developer comes first.** A new user must run the demo in less than 5 minutes.
6. **Non-interactive commands.** Use commands that do not wait for input.
7. **Public repository.** Obey the publication rules in `product-guidelines.md` in every commit.

## Task Workflow

### Standard Task Workflow

1. **Select a task.** Select the next task from `plan.md` in sequence.

2. **Mark the task in progress.** In `plan.md`, change the task from `[ ]` to `[~]`.

3. **Write failing tests (red phase).**
   - Write one or more unit tests that define the expected behavior of the task.
   - Use a fake Decisions API client. Unit tests must not call the network.
   - Run the tests. Make sure that they fail. Do not continue until they fail.

4. **Implement the code (green phase).**
   - Write the minimum code that makes the tests pass.
   - Run the tests again. Make sure that all tests pass.

5. **Refactor.** Make the code clearer without a change to its behavior.
   Run the tests again after the refactor.

6. **Verify coverage.** Run `pytest --cov=src --cov-report=term-missing`.
   The target is 70 percent or more for new code.

7. **Record deviations.** If the code differs from `tech-stack.md`:
   - Stop the implementation.
   - Update `tech-stack.md` and add a dated note about the change.
   - Continue the implementation.

8. **Mark the task complete.** In `plan.md`, change the task from `[~]` to `[x]`.
   Under the task, add a summary of two to four lines: what changed, which files, and why.
   Do not commit yet. The commit occurs at the end of the phase.

### Task Correction and Plan Amendment Workflows

1. **Changes during a task.** If you find a small gap while a task is `[~]`, fix it in
   the same task. Make sure that the tests pass.
2. **Code review corrections (`conductor-review`).** The review agent adds a
   `Review Fixes` phase to `plan.md`. Do the fix tasks in that phase.
3. **Reverts (`conductor-revert`).** A revert removes a full phase commit, because
   each phase has one commit. The revert sets the tasks in that phase back to `[ ]`.

### Phase Completion and Checkpoint Protocol

**Trigger:** Do this protocol when you complete the last task of a phase in `plan.md`.

1. **Announce the start.** Tell the user that the phase is complete and that the
   checkpoint protocol starts.

2. **Make sure that tests exist for the phase.**
   - Find the previous checkpoint SHA in `plan.md`. If there is no checkpoint, the
     scope is all changes in `gemini_decisions_api/`.
   - Run `git diff --name-only <previous_checkpoint_sha> -- .` and
     `git status --porcelain -- .` to list the changed files.
   - For each changed `.py` file, make sure that a test file exists. If it does not
     exist, write one. Use the same naming and style as the other tests.

3. **Run the automated tests.**
   - Before you run them, tell the user the exact command.
     Example: "I will run the tests. Command: `pytest --cov=src`"
   - If tests fail, tell the user and fix the problem. You can try a maximum of two
     fixes. After the second failed fix, stop and ask the user for guidance.

4. **Give a manual verification plan.**
   - Read `product.md`, `product-guidelines.md`, and `plan.md` to find the goal of the phase.
   - Give the user numbered steps with the exact commands and the expected output.
     Example:
     1. Run `python -m decisions_demo routing`.
     2. Make sure that the output shows a probability table and the selected model tier.

5. **Wait for the user.** Ask: "Does this meet your expectations? Confirm with yes,
   or tell me what to change." Do not continue without an explicit yes.

6. **Scan the diff before the commit.**
   - Scan the diff for the items that `product-guidelines.md` forbids: internal links,
     customer data, real project IDs, and API keys.
   - Make sure that `.gitignore` includes `.env`, `.venv/`, and result files.

7. **Commit the phase.**
   - Run `git pull` first.
   - Stage explicit paths only. Do not run `git add .`.
   - Commit with a message in the format in the Commit Guidelines section.
     Example: `feat(decisions-demo): Add raw API use cases`.

8. **Record the checkpoint.**
   - Get the SHA with `git log -1 --format="%h"`.
   - In `plan.md`, add `[checkpoint: <sha>]` to the phase heading.
   - Under the phase heading, add the verification summary: the test command, the
     coverage result, and the user confirmation.

9. **Commit the plan update.** Stage `conductor/` and commit with the message
   `conductor(plan): Mark phase '<PHASE NAME>' as complete`.

10. **Ask about the push.** The repository rules allow a push to `main`. Ask the user
    before each push.

### Quality Gates

Before you mark a task complete, make sure that:

- [ ] All tests pass.
- [ ] Coverage is 70 percent or more for new code.
- [ ] The code obeys the guides in `code_styleguides/`.
- [ ] All public functions have docstrings.
- [ ] All functions have type hints.
- [ ] `ruff check` shows no errors.
- [ ] Text obeys the writing rules in `product-guidelines.md`.
- [ ] The code contains no API keys and no hardcoded results.

## Development Commands

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Then set GEMINI_API_KEY in .env.
```

### Daily Development

```bash
pytest                                   # Unit tests. No network.
pytest -m integration                    # Real API test. Needs GEMINI_API_KEY.
ruff check . && ruff format --check .    # Lint and format check.
adk web                                  # Start the ADK agent in the browser.
```

### Before a Commit

```bash
ruff format . && ruff check . && pytest --cov=src --cov-report=term-missing
```

## Testing Requirements

### Unit Tests

- Each module has a test file.
- Use pytest fixtures for the fake client and the sample data.
- Use a fake for each external call: the Decisions API, `generateContent`, and the clock.
- Test the success case and the failure case.

### Integration Tests

- Mark them with `@pytest.mark.integration`.
- Skip them when `GEMINI_API_KEY` is not set.
- Test the full flow of one use case against the real API.

## Self-Review Checklist

1. **Function**
   - The feature works as `product.md` specifies.
   - The code handles edge cases, for example an empty dataset or an unknown label.
   - Error messages state the problem and the fix.
2. **Code quality**
   - The code obeys the style guides.
   - Names are clear. Comments explain why, not what.
3. **Tests**
   - The unit tests cover the behavior. The integration test passes.
4. **Security and publication**
   - No secrets in the code. The code reads the key from the environment.
   - No internal links and no customer data.

## Commit Guidelines

### Message Format

```
<type>(<scope>): <description>

[optional body]
```

Use the scope `decisions-demo` for code. Use the scope `conductor` for plan changes.

### Types

- `feat`: A new feature.
- `fix`: A bug fix.
- `docs`: Documentation only.
- `refactor`: A code change that does not add a feature and does not fix a bug.
- `test`: New or changed tests.
- `chore`: Maintenance.

## Definition of Done

A task is complete when:

1. The code obeys the specification.
2. The unit tests exist and pass.
3. Coverage is 70 percent or more.
4. The documentation is up to date.
5. `ruff check` shows no errors.
6. The task summary is in `plan.md`.

A phase is complete when all its tasks are complete, the user confirms the manual
verification, and the phase commit and the checkpoint are recorded.
