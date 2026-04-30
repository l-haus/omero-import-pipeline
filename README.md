# OMERO Import Pipeline

Single-host pipeline for preparing and importing Cell Painting datasets into OMERO on the OMERO host.

This repo now contains the helper tooling it needs for:
- OME-TIFF generation
- companion metadata generation
- OMERO import command generation

The pipeline runs on the OMERO host and is designed to be:
- reproducible
- stageable
- reviewable before import
- safer around cleanup and authentication

## What this repo does

For a dataset directory, the pipeline can:
1. generate OME-TIFFs from raw microscopy TIFFs
2. validate that output exists and looks plausible
3. generate companion `.companion.ome` files per plate
4. normalize ownership and permissions
5. generate OMERO import commands and a TSV manifest
6. optionally execute the OMERO imports
7. keep local build output until explicitly cleaned up

## Current workflow model

This is a **single-host workflow** on the OMERO host.

Key points:
- raw input is read from a host-visible path
- generated OME-TIFFs are written under `BUILD_ROOT/<dataset>`
- companion files are written into each plate directory
- generated import artifacts are written into the dataset directory
- import execution happens inside the OMERO container
- manifest plate paths are **container-visible paths**, not host paths

## Repo layout

```text
omero-import-pipeline/
├── README.md
├── .gitignore
├── config.example.sh
├── config.sh
├── pyproject.toml
├── run_omero_pipeline.sh
├── screen_mapping.json
├── src/
│   └── omero_import_pipeline/
├── docs/
│   ├── workflow.md
│   └── failure_modes.md
└── logs/
    └── .gitkeep
```

## Setup

Clone the repo on the OMERO host, then:

```bash
cp config.example.sh config.sh
chmod +x run_omero_pipeline.sh
```

Edit `config.sh` before first use.

## Python package / CLI setup

The helper CLI commands are provided by this repo.

Install the repo into the intended environment:

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate microscopy-utils
pip install -e .
```

Verify the commands resolve:

```bash
which generate-ome-tiffs-batch
which generate-companion-batch
which generate-omero-imports
```

## Main stages

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

### Stage summary

- `generate`: create OME-TIFFs under `BUILD_ROOT/<dataset>`
- `validate-local`: check that generated plate output exists and contains OME-TIFFs
- `companion`: generate `.companion.ome` files for each plate
- `permissions`: normalize ownership and readability for OMERO-side access
- `imports`: generate `omero_import_commands.txt` and `omero_import_manifest.tsv`
- `import`: execute OMERO imports from the manifest when enabled
- `validate`: inspect current dataset state and mapping readiness
- `cleanup-local`: delete local build output only with explicit confirmation
- `all`: run the standard non-destructive sequence through import

## Usage

Run individual stages when testing:

```bash
./run_omero_pipeline.sh DATASET generate
./run_omero_pipeline.sh DATASET validate-local
./run_omero_pipeline.sh DATASET companion
./run_omero_pipeline.sh DATASET permissions
./run_omero_pipeline.sh DATASET imports
./run_omero_pipeline.sh DATASET validate
```

Run the import stage in review mode first:

```bash
./run_omero_pipeline.sh DATASET import
```

Run the full pipeline:

```bash
./run_omero_pipeline.sh DATASET all
```

## Import behavior

By default, imports are review-first.

In `config.sh`:

```bash
EXECUTE_IMPORTS=0
```

With this setting:
- `imports` generates the commands file and manifest
- `import` stops after telling you where the manifest is

To execute imports automatically:

```bash
EXECUTE_IMPORTS=1
```

## Authentication behavior

When `EXECUTE_IMPORTS=1` and the selected stage is:
- `import`, or
- `all`

The script prompts once for the OMERO password.

The password:
- is entered interactively once
- is used only at runtime
- is not written to the manifest
- is not written to the generated command file

## OMERO user and screen override support

The import generation path now supports:
- configurable OMERO user
- optional screen override

### OMERO user

Use the configured user from `config.sh`:

```bash
OMERO_DEFAULT_USER="luettria"
```

That user is used for:
- generated import commands
- runtime import execution

### Screen override

If you need to import into a different screen than the one implied by `screen_mapping.json`, use a screen override.

Typical usage:

```bash
SCREEN_ID_OVERRIDE=401 ./run_omero_pipeline.sh DATASET imports
```

This is useful when:
- screen IDs differ by OMERO user context
- the mapping file was originally created around another user
- you want a one-off import target without editing the shared mapping file

## Generated files

The `imports` stage writes these files into the dataset build directory:

```text
BUILD_ROOT/DATASET/omero_import_commands.txt
BUILD_ROOT/DATASET/omero_import_manifest.tsv
```

### Commands file

Human-readable OMERO import commands grouped in batches.

### Manifest file

Structured TSV used by the pipeline import stage.

Format:

```text
# screen_id    plate_path
401    /omero_images/run_2026-03-19/KCII_... 
```

Important:
- `plate_path` values are **container-visible paths**
- they are validated inside the OMERO container during import

## Key config values

You should review these carefully in `config.sh`:
- `RAW_ROOT`
- `BUILD_ROOT`
- `MICROSCOPY_UTILS_ENV`
- `OMERO_DOCKER_CONTAINER`
- `OMERO_CLI_PATH`
- `OMERO_DEFAULT_USER`
- `RACCOON_CHOWN_USER`
- `RACCOON_CHOWN_GROUP`
- `EXECUTE_IMPORTS`
- `LOCAL_RETENTION_DAYS`

If supported in your shell usage, you may also pass:
- `SCREEN_ID_OVERRIDE`

## Cleanup behavior

Cleanup is separate from normal pipeline execution.

To delete local build output:

```bash
CONFIRM_DELETE=YES ./run_omero_pipeline.sh DATASET cleanup-local
```

Guardrails:
- requires explicit confirmation
- enforces `LOCAL_RETENTION_DAYS`
- is not part of `all`

## Logging

Logs are written under:

```text
logs/<dataset>/
```

Each run creates a timestamped log file.

## Recommended operator sequence

For a first run on a dataset:

```bash
./run_omero_pipeline.sh DATASET generate
./run_omero_pipeline.sh DATASET validate-local
./run_omero_pipeline.sh DATASET companion
./run_omero_pipeline.sh DATASET permissions
./run_omero_pipeline.sh DATASET imports
./run_omero_pipeline.sh DATASET validate
./run_omero_pipeline.sh DATASET import
```

Then enable real import execution only when you are satisfied with:
- generated screen ID
- OMERO user
- manifest paths
- expected plate coverage

## Current design goals

This repo intentionally prefers:
- one operational repo
- staged execution
- explicit review points
- minimal hidden state
- no automatic destructive cleanup during normal runs

## Known limitations

Current limitations include:
- import authentication is still password-based at runtime
- manifest execution assumes the container path mapping is correct
- cleanup uses directory modification time as a simple retention proxy
- there is not yet a dedicated preflight stage

## Next recommended improvement

Add a `preflight` stage to validate:
- required CLI commands
- config paths
- OMERO container presence
- container path visibility
- screen mapping file availability
