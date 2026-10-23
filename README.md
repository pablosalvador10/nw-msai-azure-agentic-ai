# Agentic AI on Azure · Northwestern MS AI

Teaching materials for Northwestern's MS AI program. Students build a support API for a fictional bike-share service, add retrieval and tools, coordinate agents, and test the service on Azure.

> **Students:** start with the **[FY26 course home](fy26/index.html)** in a browser. It links setup, Foundations, each week's lecture and slides, and the required lab. The **[FY26 README](fy26/README.md)** has the calendar, grading and deadlines. On GitHub, download or clone the repository to open the HTML pages locally; GitHub's file view shows their source.

## Cohorts

| Cohort | Status | Start here |
|---|---|---|
| **FY26** | Current | [Course home](fy26/index.html) · [README](fy26/README.md) |
| FY25 | Archived, read-only | [fy25/README.md](fy25/README.md) |

## How this repository is organized

```
.
├── fy26/                    # Current cohort
│   ├── README.md            # Calendar, weekly loop, grading
│   ├── index.html           # Browser home: reading, slides and labs
│   ├── setup/               # One-time setup: tools, Azure, Terraform, first deploy
│   ├── foundations/         # Short primers: Terraform, FastAPI, containers, identity, harness
│   ├── week05-…/ … week10-…/ # Overview, lecture source, main lab, optional deep dive
│   │   └── docs/            # Browser lecture and slides, together
│   ├── assets/              # Shared styles and navigation
│   ├── app/                 # The service students build and deploy
│   ├── harness/             # The local harness: checks and public data
│   ├── infra/               # Terraform for each student's resource group
│   └── pyproject.toml       # The cohort's own Python environment (uv)
├── fy25/                    # Archived cohort, frozen exactly as taught
├── .github/                 # CI, Copilot instructions and skills
└── LICENSE
```

Each cohort has its own dependency file, lockfile, Python version and environment template. This keeps one year's package changes separate from another's. Archived files preserve what was taught; cloud services, models and external links can still change or retire.

## Quick start

```bash
git clone https://github.com/pablosalvador10/northwestern-msai-azure-agentic-ai.git
cd northwestern-msai-azure-agentic-ai/fy26
uv sync
```

Then open the [course home](fy26/index.html) in a browser and follow [FY26 · Start here](fy26/README.md#start-here). Open the cohort folder in VS Code for notebook work.

## Starting a new cohort (instructors)

1. Copy the latest cohort's course files to the new year folder. Do not copy a local environment, credentials, Terraform state or plans, reports, or agent-generated memory. Update the calendar, session folders and model versions; check availability in the region used for class.
2. Run `uv lock --upgrade` inside `fyNN/`, run the tests, and commit the lockfile.
3. Update the cohort matrix and infrastructure working directory in the [CI workflow](.github/workflows/ci.yml). Update internal links, instructions and agent configuration that name the previous cohort.
4. Add the archived banner to the previous cohort's README and update the **Cohorts** table above.

Archived cohorts are never edited, except to fix broken links.

Before sharing a cohort with students, make sure its files and lockfile are available on the branch the setup instructions clone. Test the setup from a clean clone, not from the instructor's working directory.

## Contributing

See the [contributor guide](CONTRIBUTING.md) for the current code layout, testing commands, content workflow and privacy checks.

## License

MIT, see [LICENSE](LICENSE).
