# OMERO Import Pipeline

Small Bash pipeline for importing Cell Painting datasets into OMERO on the OMERO host.

This repo assumes:
- raw input datasets are available on the OMERO host
- OME-TIFF generation, companion generation, permissions, and OMERO import all run on the OMERO host
- `screen_mapping.json` is a repo asset
- generated import artifacts are written into the dataset build directory

## Repo layout

```text
omero-import-pipeline/
├── README.md
├── .gitignore
├── config.example.sh
├── config.sh
├── run_omero_pipeline.sh
├── screen_mapping.json
├── docs/
│   ├── workflow.md
│   └── failure_modes.md
└── logs/
    └── .gitkeep
```

## Setup

```bash
cp config.example.sh config.sh
chmod +x run_omero_pipeline.sh
```

Edit `config.sh` before first use.

## Main files

- `config.example.sh`: template config
- `config.sh`: local machine-specific config, not tracked in git
- `run_omero_pipeline.sh`: main pipeline entrypoint
- `screen_mapping.json`: mapping from plate prefixes to OMERO screen IDs
- `docs/workflow.md`: operational workflow notes
- `docs/failure_modes.md`: common failure modes and how to respond

## Stage model

The pipeline stages are:

- `generate`
- `validate-local`
- `companion`
- `permissions`
- `imports`
- `import`
- `validate`
- `cleanup-local`
- `all`

### What each stage does

- `generate`: creates OME-TIFFs for a dataset
- `validate-local`: checks that generated output exists and looks plausible
- `companion`: generates companion metadata files
- `permissions`: fixes ownership and permissions for downstream OMERO access
- `imports`: validates screen mappings and generates import files
- `import`: imports plates into OMERO from the generated manifest
- `validate`: checks overall pipeline state for a dataset
- `cleanup-local`: deletes local build output only when explicitly confirmed
- `all`: runs the normal pipeline from generation through import

## Usage

Run stages individually first when testing:

```bash
./run_omero_pipeline.sh TEST_DATASET generate
./run_omero_pipeline.sh TEST_DATASET validate-local
./run_omero_pipeline.sh TEST_DATASET companion
./run_omero_pipeline.sh TEST_DATASET permissions
./run_omero_pipeline.sh TEST_DATASET imports
./run_omero_pipeline.sh TEST_DATASET validate
```

When ready:

```bash
./run_omero_pipeline.sh TEST_DATASET import
```

Or run the main sequence:

```bash
./run_omero_pipeline.sh TEST_DATASET all
```

## Import behavior

By default, imports are not executed automatically.

In `config.sh`:

```bash
EXECUTE_IMPORTS=0
```

That means the pipeline will generate the import manifest and stop before actual import execution.

To allow automatic import execution:

```bash
EXECUTE_IMPORTS=1
```

Be careful with this setting.

## Cleanup behavior

Cleanup is intentionally separate from the normal pipeline.

It requires explicit confirmation:

```bash
CONFIRM_DELETE=YES ./run_omero_pipeline.sh TEST_DATASET cleanup-local
```

The script also checks that the dataset is older than `LOCAL_RETENTION_DAYS`.

Cleanup is not part of `all`.

## Logging

Logs are written under:

```text
logs/<dataset>/
```

Each run creates a timestamped log file.

## Safety model

This pipeline is designed around a few simple rules:

- do not hide important operational state
- do not auto-delete build output during normal runs
- do not execute imports by default
- do not make cleanup part of `all`
- fail early on missing paths or missing screen mappings

## Important assumptions

This repo assumes that:

- the script is run from a checked-out repo on the OMERO host
- `screen_mapping.json` is available at the repo path
- `generate-ome-tiffs-batch`, `generate-companion-batch`, and `generate-omero-imports` are installed and available
- the configured conda environment contains the required tools
- the current user can reach the OMERO host over SSH and can use `sudo` for the permissions stage if needed

## Known weak points

There are still a few things to keep in mind:

- the manifest parser depends on the exact output format of `generate-omero-imports`
- the cleanup age check uses directory modification time, which is simple but not perfect
- OMERO password/session handling is intentionally not over-automated in this version

## Recommended first-run order

Do not start with `all`.

Use this order first:

```bash
./run_omero_pipeline.sh TEST_DATASET generate
./run_omero_pipeline.sh TEST_DATASET validate-local
./run_omero_pipeline.sh TEST_DATASET companion
./run_omero_pipeline.sh TEST_DATASET permissions
./run_omero_pipeline.sh TEST_DATASET imports
./run_omero_pipeline.sh TEST_DATASET validate
```

Then inspect the generated artifacts and only then run:

```bash
./run_omero_pipeline.sh TEST_DATASET import
```
