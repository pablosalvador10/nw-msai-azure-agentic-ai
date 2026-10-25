# Contributing

This repository contains teaching materials, a starter service, and a grading harness. A useful change should make a concept easier to understand, fix a reproducible problem, or make the student workflow more reliable.

If you are taking the course, start with the [FY26 course home](fy26/index.html) or [course README](fy26/README.md). The weekly overview defines your exercise. These notes are for changes to the course itself.

## Work in the current cohort

All new course work belongs in [fy26/](fy26/README.md). Run Python commands from that folder and use its Python 3.12 environment. It has its own dependencies and lockfile; the repository-root environment may belong to last year's course.

- Install dependencies with `uv sync --locked`.
- Add a dependency with `uv add <package>` from the cohort folder; include the updated lockfile in the change.
- Leave [FY25](fy25/README.md) unchanged except for broken-link repairs.
- Keep changes focused. Do not mix a content correction, a dependency upgrade, and a redesign in one pull request.

## Keep the exercises intact

The starting services are deliberately limited. The students' work is to improve them. Do not replace the starter with a reference solution.

| Area | Where it belongs | What to preserve |
|---|---|---|
| Request and response shapes | [fy26/app/contract.py](fy26/app/contract.py) | The HTTP contract used by the harness |
| Fares, credits and station rules | [fy26/app/domain.py](fy26/app/domain.py) | Deterministic calculations; models must not calculate prices |
| Agent tools | [fy26/app/tools.py](fy26/app/tools.py) and [fy26/app/mcp_server.py](fy26/app/mcp_server.py) | Clear descriptions, constrained arguments, and recorded results |
| Public scoring | [fy26/harness/](fy26/harness/__main__.py) | Checks that reward useful behavior rather than constant or fabricated answers |
| Infrastructure | [fy26/infra/](fy26/infra/README.md) | One resource group per student, keyless Azure access, readable Terraform |

Students must not change the contract or scoring code. If a maintainer needs to change either, update the service, harness, datasets, tests and affected weekly instructions together. Keep hidden data and reference solutions outside this repository.

## Python and tests

- Use type hints and built-in generics such as `list[str]`. Use Pydantic for API models and settings, and plain Python for domain rules.
- Write a short docstring for public functions. Explain a non-obvious decision near the code; do not restate what each line does.
- Use logging for service diagnostics. Notebook cells, the CLI, and teaching helpers may print results and commands deliberately.
- Catch errors where they can be handled. Do not add a blanket `try/except` that hides a failure or reports success when a step did not finish.
- Add a regression test for a bug. Include an error case as well as the successful path.
- Tests run offline: no Azure calls, network access or real credentials. Use the fixtures in [fy26/tests/conftest.py](fy26/tests/conftest.py).

Install the commit hooks once from the repository root with `pre-commit install`. They run Ruff (lint and format), file hygiene, a secret scan, the notebook-output check and `terraform fmt` on every commit; `pre-commit run --all-files` runs them on everything. From the cohort folder, `uv run pytest --cov` runs the offline tests with branch coverage; the build fails below the floor in `pyproject.toml`, and the floor only moves up. Ruff is the only formatter (do not add Black: the two disagree). There are no registered `unit`, `integration` or `slow` test markers; register a marker before introducing it because pytest uses strict marker checking.

Some Week 8 tests are skipped until the student-built feature exists. That is intentional. Do not silence a new failure by skipping its test or lowering a grading threshold.

## Teaching materials

Use direct language. Define a term before relying on it, explain why the example is needed, and say what the student should observe. Avoid promises such as “always correct” when the example only demonstrates a schema or one measured run.

Each week has a clear division of work:

- The weekly overview describes preparation, the exercise, grading and submission.
- The Markdown lecture is the source for the reading page. Keep numbered sections and copied Python examples aligned with the HTML version in the week's documentation folder.
- The slides summarize the same concepts for class. They are not an additional assignment.
- The main notebook is the required lab. Mark extensions as optional, and leave enough time to deploy before the session ends.
- The deep-dive notebook contains optional experiments. It must not become a hidden prerequisite for the main lab.

Link to official documentation for the concepts taught. Label approximate timings, model-dependent behavior and measured examples. An observation from one run is not a benchmark or a guarantee.

Before saving a notebook for commit, clear all outputs and execution counts in VS Code. Then check its links from the notebook's actual folder. Do not include account details, resource names, endpoints or keys in committed examples or outputs.

For browser changes, check a lecture and a slide deck at desktop and phone widths. Check keyboard navigation, contents links, reduced-motion behavior and print output. The shared styles and scripts live in [fy26/assets/](fy26/assets/lecture.css); a change there affects every week.

## Safety and privacy

- Never commit environment files, Terraform variable files, state, plan files, reports or credentials. Ignore rules are a safeguard, not a substitute for reviewing the diff.
- Use managed identity or `DefaultAzureCredential` for Azure access. Do not add Azure API keys to make an example easier to run.
- Keep course scenarios fictional and original. Do not copy customer code, data, screenshots or internal material into a lesson.
- A local design reference is not course content. Leave it untracked unless its provenance and publication rights have been checked.
- Do not deploy, destroy resources, push a branch or publish materials as part of an unrelated edit.

## Before opening a pull request

1. Explain the problem and how the change addresses it. For a teaching change, name what students should understand or be able to do differently.
2. Run the checks above. For infrastructure changes, also run `terraform fmt -check -recursive`, initialize the provider with no backend, and run `terraform validate` from the infrastructure folder. Validation does not prove that a deployment will succeed in Azure.
3. Review every changed file, including notebooks, lockfiles and generated pages. Remove outputs, private values and unrelated edits.
4. Check the affected reading page, slides and notebook agree. The tests in [fy26/tests/test_teaching_consistency.py](fy26/tests/test_teaching_consistency.py) and [fy26/tests/test_presentation_assets.py](fy26/tests/test_presentation_assets.py) cover section and code drift, shared assets, and local HTML links.
5. Use a conventional commit prefix: `fix:`, `docs:`, `feat:`, `test:` or `refactor:`. In the pull request, record which checks ran and any behavior that remains unverified.

The [CI workflow](.github/workflows/ci.yml) runs the same pre-commit hooks, a secret scan of the pushed commits, the locked install, Ruff, the offline tests with coverage, clean notebook outputs, and Terraform formatting and validation. Keep it green before merging.
