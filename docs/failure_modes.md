# Failure Modes

This document lists common operational failure modes in the OMERO import pipeline and how to respond.

The point is not to eliminate every possible failure. The point is to make failures visible and recoverable.

## 1. Raw dataset path does not exist

Symptoms:
- `generate` fails immediately
- `validate` reports missing raw dataset

Likely causes:
- wrong dataset name
- wrong `RAW_ROOT`
- raw data not mounted or not present yet

What to do:
1. verify the dataset name
2. check `RAW_ROOT` in `config.sh`
3. verify the raw dataset path directly on the OMERO host
4. rerun `validate`

## 2. OME-TIFF generation fails partway through

Symptoms:
- `generate` exits non-zero
- build directory exists but content is incomplete
- logs show tool or environment errors

Likely causes:
- bad input data
- storage exhaustion
- environment activation failure
- tool crash

What to do:
1. inspect the log file under `logs/<dataset>/`
2. inspect the build directory directly
3. fix the underlying issue
4. rerun `generate`
5. rerun `validate-local`

What not to do:
- do not assume partial output is valid
- do not continue directly to `companion`

## 3. `validate-local` fails because no plate directories were found

Symptoms:
- build directory exists
- validation says no plate directories are present

Likely causes:
- generator wrote to an unexpected layout
- wrong build root
- generation failed earlier than expected

What to do:
1. inspect the directory layout manually
2. confirm how `generate-ome-tiffs-batch` writes output
3. adjust the validation logic if the layout is valid but different
4. otherwise fix generation and rerun

## 4. `validate-local` fails because no OME-TIFF files were found

Symptoms:
- plate directories exist
- no `.ome.tif` or `.ome.tiff` files are found

Likely causes:
- generation did not complete
- generator produced a different filename pattern
- validation assumptions are wrong

What to do:
1. inspect actual filenames with `find`
2. confirm expected output naming from the generator
3. fix validation if the output is correct but named differently
4. otherwise rerun generation after fixing the root issue

## 5. Companion generation fails

Symptoms:
- `companion` exits non-zero
- build dataset exists but companion files are missing

Likely causes:
- missing environment or tool
- malformed generated dataset
- incompatible input structure

What to do:
1. inspect logs
2. verify the conda environment on the host
3. run the companion command manually once if needed
4. fix the issue
5. rerun `companion`

Do not continue to import setup if companion generation is required and missing.

## 6. Permissions stage fails

Symptoms:
- `permissions` exits non-zero
- logs show `sudo` or permission errors

Likely causes:
- insufficient privileges
- wrong owner/group settings in config
- filesystem permission policy

What to do:
1. verify `RACCOON_CHOWN_USER` and `RACCOON_CHOWN_GROUP`
2. verify that the operator can use `sudo`
3. test the ownership command manually on one path
4. rerun `permissions`

If your environment does not need this stage, remove or simplify it rather than keeping a fake step that always fails.

## 7. Missing screen mapping prefixes

Symptoms:
- `imports` fails during prefix validation
- error lists one or more missing prefixes

Likely causes:
- new plate prefix not yet added to `screen_mapping.json`
- typo in directory naming
- wrong dataset contents

What to do:
1. inspect the listed prefixes
2. confirm whether they are real plate prefixes
3. update `screen_mapping.json` if needed
4. rerun `imports`

This is a hard failure by design.

## 8. `generate-omero-imports` fails

Symptoms:
- `imports` exits non-zero before manifest generation
- command file is missing

Likely causes:
- tool is unavailable
- mapping file path cannot be read by the tool
- dataset structure is incompatible
- the tool itself failed

What to do:
1. verify the tool is installed and on `PATH`
2. verify that `screen_mapping.json` exists at the repo path
3. run the command manually once for debugging
4. fix the issue
5. rerun `imports`

## 9. Import command parsing fails

Symptoms:
- `imports` generates a command file but fails when creating the TSV manifest
- error says a command line could not be parsed

Likely causes:
- output format of `generate-omero-imports` changed
- parser regex is too strict
- command file contains unexpected content

What to do:
1. inspect `omero_import_commands.txt`
2. compare its format to what the parser expects
3. update the regex parser if needed
4. rerun `imports`

This is one of the current weak points of the pipeline.

## 10. Import manifest is missing

Symptoms:
- `import` fails because `omero_import_manifest.tsv` does not exist

Likely causes:
- `imports` did not run
- `imports` failed after command generation
- manifest path configuration is wrong

What to do:
1. rerun `imports`
2. inspect the build dataset directory
3. verify config values for generated filenames

## 11. OMERO import fails partway through

Symptoms:
- `import` starts but stops after some plates
- some data may already be in OMERO

Likely causes:
- authentication or session issue
- malformed import manifest
- individual plate import failure
- OMERO-side service problem

What to do:
1. inspect the log output
2. determine which plate failed
3. inspect that plate directory
4. fix the specific issue
5. rerun `import`

Important:
- do not immediately delete local build output
- partial import completion is a normal reason to keep local data around

## 12. Import does not execute because `EXECUTE_IMPORTS=0`

Symptoms:
- `import` appears to stop after reporting the manifest path

Cause:
- this is expected behavior

What to do:
1. inspect the manifest
2. if ready, set `EXECUTE_IMPORTS=1`
3. rerun `import`

This is a safety feature, not a bug.

## 13. Cleanup is refused

Symptoms:
- `cleanup-local` exits with a confirmation or retention error

Likely causes:
- `CONFIRM_DELETE=YES` was not set
- dataset is younger than `LOCAL_RETENTION_DAYS`

What to do:
1. verify you really want to delete the dataset
2. rerun with explicit confirmation:
   `CONFIRM_DELETE=YES ./run_omero_pipeline.sh DATASET cleanup-local`
3. if retention is blocking you intentionally, either wait or reduce the threshold in config

This refusal is intentional.

## 14. Cleanup deletes data that was still needed

Symptoms:
- you need to inspect or re-import a dataset, but the build output is gone

Root cause:
- cleanup was run too early

What to do:
1. regenerate the dataset if necessary
2. tighten your cleanup practice
3. consider increasing `LOCAL_RETENTION_DAYS`

Prevention:
- do not treat cleanup as part of the normal pipeline
- do not run cleanup on the same day as first import unless you are very sure

## 15. Script cannot find `screen_mapping.json`

Symptoms:
- `imports` or `validate` fails before remote work starts
- error says the local mapping file is missing

Likely causes:
- repo asset not present
- wrong file name in config
- script run from an unexpected checkout

What to do:
1. verify that `screen_mapping.json` exists in the repo root
2. verify `SCREEN_MAPPING_FILE` in `config.sh`
3. rerun from the intended checked-out repo

## 16. Config drift causes wrong paths or wrong ownership

Symptoms:
- stages fail unexpectedly
- output lands in the wrong directory
- ownership commands target the wrong paths

Likely causes:
- stale `config.sh`
- copied config from another machine
- local edits not reflected in docs

What to do:
1. compare `config.sh` to `config.example.sh`
2. verify all path settings directly on the OMERO host
3. verify owner/group values before rerunning `permissions`

## Operational guidance

When something fails:

1. stop advancing to later stages
2. inspect the most recent log file
3. inspect the dataset directory directly
4. fix the root cause
5. rerun the failed stage
6. rerun `validate`

Do not try to “push through” a broken earlier stage by continuing to later ones. That is how messy state accumulates.

## Longer-term hardening ideas

These are not required immediately, but they are the logical next improvements:

- make `generate-omero-imports` emit TSV directly
- add a status marker file per dataset
- make validation more specific to expected plate counts
- record publish/import timestamps explicitly instead of relying on directory mtime
- improve OMERO authentication/session handling without embedding passwords in files
