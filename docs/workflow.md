# Workflow

## Overview

This workflow imports Cell Painting datasets into OMERO using a single-host pipeline on the OMERO host.

The pipeline is structured as staged execution rather than a long sequence of copy-pasted commands.

The goals are:

- reduce operator mistakes
- make reruns easier
- keep generated artifacts in predictable places
- separate normal processing from destructive cleanup

## High-level flow

For a dataset `DATASET`, the pipeline does:

1. generate OME-TIFFs from raw input
2. validate that generated output exists and looks plausible
3. generate companion metadata
4. fix permissions
5. validate plate prefixes against `screen_mapping.json`
6. generate OMERO import commands
7. convert the commands to a structured TSV manifest
8. optionally execute the OMERO imports
9. keep local build output until explicitly cleaned up

## Directory model

### Raw input

Raw input is expected at:

```text
RAW_ROOT/DATASET
```

### Build output

Generated OME-TIFFs and related artifacts are written to:

```text
BUILD_ROOT/DATASET
```

### Repo asset

The plate prefix mapping is stored in the repo as:

```text
screen_mapping.json
```

### Generated import artifacts

Generated files live inside the dataset build directory:

```text
BUILD_ROOT/DATASET/omero_import_commands.txt
BUILD_ROOT/DATASET/omero_import_manifest.tsv
```

## Stage details

## `generate`

Purpose:
- create OME-TIFFs for the dataset

Input:
- `RAW_ROOT/DATASET`

Output:
- `BUILD_ROOT/DATASET`

Expected behavior:
- fails if the raw dataset path does not exist
- creates the build directory if needed
- runs `generate-ome-tiffs-batch`

Typical command:

```bash
./run_omero_pipeline.sh DATASET generate
```

## `validate-local`

Purpose:
- sanity-check generated output before downstream stages

Checks:
- build dataset directory exists
- at least one plate directory exists
- at least one `.ome.tif` or `.ome.tiff` file exists

Typical command:

```bash
./run_omero_pipeline.sh DATASET validate-local
```

This is not a full data validation framework. It is a basic operational sanity check.

## `companion`

Purpose:
- generate companion metadata for the built dataset

Input:
- `BUILD_ROOT/DATASET`

Expected behavior:
- runs `generate-companion-batch`
- fails if build output is missing

Typical command:

```bash
./run_omero_pipeline.sh DATASET companion
```

## `permissions`

Purpose:
- normalize ownership and permissions for OMERO-side access

Input:
- `BUILD_ROOT/DATASET`

Expected behavior:
- changes ownership to the configured user and group
- makes files world-readable
- makes directories world-readable and executable

Typical command:

```bash
./run_omero_pipeline.sh DATASET permissions
```

This stage may require `sudo` rights depending on the environment.

## `imports`

Purpose:
- validate screen mappings and generate import artifacts

Input:
- `BUILD_ROOT/DATASET`
- `screen_mapping.json`

Output:
- `omero_import_commands.txt`
- `omero_import_manifest.tsv`

What happens:
1. the script loads `screen_mapping.json`
2. the script checks all plate prefixes found in the dataset
3. if any prefix is missing from the mapping, the stage fails
4. the script runs `generate-omero-imports`
5. the generated command file is parsed into a TSV manifest

Manifest format:

```text
# screen_id    plate_path
103    /path/to/plate1
60     /path/to/plate2
```

Typical command:

```bash
./run_omero_pipeline.sh DATASET imports
```

## `import`

Purpose:
- import the dataset into OMERO from the TSV manifest

Input:
- `BUILD_ROOT/DATASET/omero_import_manifest.tsv`

Behavior:
- if `EXECUTE_IMPORTS=0`, the stage stops after telling you where the manifest is
- if `EXECUTE_IMPORTS=1`, the stage loops through the manifest and runs OMERO import commands

Typical command:

```bash
./run_omero_pipeline.sh DATASET import
```

Default recommendation:
- keep `EXECUTE_IMPORTS=0` until you trust the workflow for your environment

## `validate`

Purpose:
- inspect current pipeline state for a dataset

Checks:
- raw dataset path exists
- build dataset path exists or is reported as missing
- `screen_mapping.json` is present
- screen prefix validation runs if build output exists
- import manifest existence is reported

Typical command:

```bash
./run_omero_pipeline.sh DATASET validate
```

This is useful before imports and after partial failures.

## `cleanup-local`

Purpose:
- delete local build output after explicit confirmation

Input:
- `BUILD_ROOT/DATASET`

Guardrails:
- requires `CONFIRM_DELETE=YES`
- requires dataset age to be at least `LOCAL_RETENTION_DAYS`

Typical command:

```bash
CONFIRM_DELETE=YES ./run_omero_pipeline.sh DATASET cleanup-local
```

This stage is intentionally not part of `all`.

## `all`

Purpose:
- run the standard non-destructive pipeline sequence

Sequence:
1. `generate`
2. `validate-local`
3. `companion`
4. `permissions`
5. `imports`
6. `import`

Typical command:

```bash
./run_omero_pipeline.sh DATASET all
```

Keep in mind:
- `import` still obeys `EXECUTE_IMPORTS`
- `cleanup-local` is not included

## Recommended operator workflow

For a new dataset:

```bash
./run_omero_pipeline.sh DATASET generate
./run_omero_pipeline.sh DATASET validate-local
./run_omero_pipeline.sh DATASET companion
./run_omero_pipeline.sh DATASET permissions
./run_omero_pipeline.sh DATASET imports
./run_omero_pipeline.sh DATASET validate
```

Then inspect:
- logs
- generated manifest
- expected plate coverage

Then either:
- run `import` manually
- or enable `EXECUTE_IMPORTS=1` and rerun `import`

## Screen mapping policy

`screen_mapping.json` is a required asset for the pipeline.

The workflow assumes:
- each plate directory name begins with a 4-character prefix
- that prefix maps to an OMERO screen ID
- missing mappings are treated as hard failures during `imports`

This is intentional. Silent fallback behavior would be risky.

## Cleanup policy

Local build output is temporary but should not be deleted automatically at the end of the main pipeline.

Why:
- imports may partially fail
- you may need to rerun import logic
- you may need to inspect generated artifacts
- immediate deletion makes recovery harder

The cleanup stage is separate on purpose.

## Notes on generated artifacts

The command file exists mainly because it is what the current tool produces.

The TSV manifest exists because it is a safer structured representation for import execution.

Longer-term, the cleaner design would be to make `generate-omero-imports` emit TSV directly.
