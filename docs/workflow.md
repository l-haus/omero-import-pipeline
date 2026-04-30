# Workflow

## Overview

This document describes the current OMERO import workflow implemented by this repo.

The workflow is now:
- single-host
- stage-based
- driven from the OMERO host
- backed by helper CLIs vendored into this repo

The main purpose is to turn a raw Cell Painting dataset into imported OMERO plates with predictable intermediate artifacts and review points.

## Execution model

The pipeline runs on the OMERO host.

It uses:
- host-visible raw input paths
- host-visible build/output paths
- container-visible image paths during the actual OMERO import step

That distinction matters:
- generation and companion writing run on host paths
- import execution runs inside the OMERO container
- manifest paths therefore use container path semantics

## High-level stage flow

For a dataset `DATASET`, the normal flow is:

1. `generate`
2. `validate-local`
3. `companion`
4. `permissions`
5. `imports`
6. `import`

The `all` stage runs this same sequence.

`cleanup-local` is intentionally separate and not included in `all`.

## Paths and artifacts

### Raw input

Expected at:

```text
RAW_ROOT/DATASET
```

### Build dataset

Generated output lives at:

```text
BUILD_ROOT/DATASET
```

This dataset directory becomes the main working location for:
- OME-TIFF files
- companion files
- generated import command file
- generated import manifest

### Repo asset

The screen mapping file lives in the repo root:

```text
screen_mapping.json
```

The shell pipeline resolves it relative to the script directory.

## Stage details

## `generate`

Purpose:
- generate OME-TIFFs from raw TIFF inputs

Input:
- `RAW_ROOT/DATASET`

Output:
- `BUILD_ROOT/DATASET/<plate>/...*.ome.tiff`

Implementation notes:
- uses `generate-ome-tiffs-batch`
- helper code is vendored into this repo under `src/omero_import_pipeline/`
- runs in the configured conda environment

Failure should stop the workflow here.

## `validate-local`

Purpose:
- basic operational sanity check after generation

Checks:
- build dataset exists
- at least one plate directory exists
- at least one `.ome.tif` or `.ome.tiff` exists

This is not a complete scientific validation layer. It is a workflow safety check.

## `companion`

Purpose:
- create `.companion.ome` files for each plate directory

Input:
- plate directories under `BUILD_ROOT/DATASET`

Implementation notes:
- uses `generate-companion-batch`
- companion files are written into each plate directory
- the helper code is vendored into this repo

## `permissions`

Purpose:
- normalize ownership and readability for OMERO access

Input:
- `BUILD_ROOT/DATASET`

Behavior:
- recursively chowns the dataset to the configured user/group
- makes files world-readable
- makes directories world-readable and executable

This stage may require `sudo`.

## `imports`

Purpose:
- validate screen routing and generate import artifacts

Inputs:
- `BUILD_ROOT/DATASET`
- `screen_mapping.json`
- configured OMERO user
- optional `SCREEN_ID_OVERRIDE`

Outputs:
- `BUILD_ROOT/DATASET/omero_import_commands.txt`
- `BUILD_ROOT/DATASET/omero_import_manifest.tsv`

### What happens inside `imports`

1. the pipeline validates plate prefixes against `screen_mapping.json`
2. the helper CLI generates grouped OMERO import commands
3. those grouped commands are expanded into a TSV manifest
4. the manifest contains one row per plate path

### OMERO user behavior

Generated commands use the configured OMERO user, for example:

```text
-u luettria
```

This keeps the generated commands aligned with runtime import behavior.

### Screen override behavior

By default, screen IDs come from `screen_mapping.json`.

If `SCREEN_ID_OVERRIDE` is set, the generated import commands and manifest use that screen ID instead of the mapped one.

This is useful when screen IDs are effectively user-context dependent or when a one-off target screen is needed.

## `import`

Purpose:
- execute the OMERO imports from the manifest

Input:
- `BUILD_ROOT/DATASET/omero_import_manifest.tsv`

### Manifest format

```text
# screen_id    plate_path
401    /omero_images/run_2026-03-19/KCII_...
```

Important:
- `plate_path` is a **container-visible path**
- the pipeline validates these paths **inside the OMERO container**

### Review-first mode

When:

```bash
EXECUTE_IMPORTS=0
```

The stage does not execute imports. It only points you at the manifest.

### Execution mode

When:

```bash
EXECUTE_IMPORTS=1
```

The stage:
- prompts once for the OMERO password if needed
- validates each plate path inside the container
- runs OMERO import commands from the manifest rows

### Authentication behavior

The password is collected once and reused across the import loop.

It is not written to:
- the manifest
- the generated command file
- config files

## `validate`

Purpose:
- inspect the current dataset state and configuration alignment

Checks:
- raw dataset exists
- build dataset exists or is reported missing
- `screen_mapping.json` exists
- prefix validation succeeds when build output exists
- manifest existence is reported

This is useful both before import and after partial failures.

## `cleanup-local`

Purpose:
- delete local build output after explicit confirmation

Guards:
- requires `CONFIRM_DELETE=YES`
- requires dataset age to be at least `LOCAL_RETENTION_DAYS`

This stage is intentionally separate from `all`.

## `all`

Purpose:
- run the standard pipeline sequence in one command

Sequence:
1. `generate`
2. `validate-local`
3. `companion`
4. `permissions`
5. `imports`
6. `import`

When `EXECUTE_IMPORTS=1`, the script prompts for the OMERO password near the start of `all` so the long run does not wait until the very end for authentication.

## Host paths vs container paths

This is one of the most important operational details.

### Host path examples

Used by generation and metadata-writing stages:

```text
/mnt/data/cell_painting/omero_images/run_2026-03-19
```

### Container path examples

Used by import commands and manifest rows:

```text
/omero_images/run_2026-03-19/KCII_...
```

If these are confused, imports will fail even when the dataset exists.

## Generated command grouping

The generated OMERO command file may group multiple plate paths into a single OMERO import command.

The manifest expands those grouped commands into one row per plate.

This design keeps:
- the command file useful for human review
- the manifest simple for deterministic pipeline execution

## Recommended operator workflow

For a new dataset:

```bash
./run_omero_pipeline.sh DATASET generate
./run_omero_pipeline.sh DATASET validate-local
./run_omero_pipeline.sh DATASET companion
./run_omero_pipeline.sh DATASET permissions
./run_omero_pipeline.sh DATASET imports
./run_omero_pipeline.sh DATASET validate
./run_omero_pipeline.sh DATASET import
```

For a confident repeat run:

```bash
./run_omero_pipeline.sh DATASET all
```

## Why the workflow is staged

This workflow intentionally keeps explicit stage boundaries because they help with:
- debugging
- reviewability
- reruns after partial failure
- avoiding premature cleanup
- avoiding hidden operator state

## Current design tradeoffs

The current design is deliberately practical rather than over-abstracted.

It favors:
- one repo
- one host
- vendored helper tooling
- shell orchestration plus small Python CLIs

It does not yet include:
- a preflight stage
- session-based OMERO auth
- richer state tracking beyond logs and generated artifacts
