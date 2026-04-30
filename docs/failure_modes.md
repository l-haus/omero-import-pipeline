# Failure Modes

This document describes common failure modes in the current OMERO import pipeline and how to respond.

The goal is not to make failures impossible. The goal is to make them understandable and recoverable.

## 1. Raw dataset path does not exist

Symptoms:
- `generate` fails immediately
- `validate` reports missing raw dataset

Likely causes:
- wrong dataset name
- wrong `RAW_ROOT`
- raw storage not mounted or not available

What to do:
1. verify the dataset name
2. verify `RAW_ROOT` in `config.sh`
3. check the path directly on the OMERO host
4. rerun `validate`

## 2. OME-TIFF generation fails or stops partway through

Symptoms:
- `generate` exits non-zero
- partial output exists under the build dataset
- logs show tool or environment errors

Likely causes:
- broken raw input
- storage exhaustion
- missing Python package dependency
- conda environment activation failure

What to do:
1. inspect the log file under `logs/<dataset>/`
2. inspect the build dataset directly
3. fix the underlying problem
4. rerun `generate`
5. rerun `validate-local`

Do not continue downstream on partial output unless you have confirmed it is complete.

## 3. `validate-local` fails because no plate directories were found

Symptoms:
- build dataset exists
- validation reports no plate directories

Likely causes:
- generator wrote to a different layout than expected
- output root is wrong
- generation failed before plate-level output was created

What to do:
1. inspect the build dataset manually
2. confirm the expected directory layout
3. fix the root cause
4. rerun `generate`

## 4. `validate-local` fails because no OME-TIFFs were found

Symptoms:
- plate directories exist
- validation reports no `.ome.tif` or `.ome.tiff` files

Likely causes:
- generation did not complete
- naming pattern differs from validation assumptions
- output path is wrong

What to do:
1. inspect actual filenames with `find`
2. confirm generator output naming
3. update validation if naming is valid but different
4. rerun generation if output is actually incomplete

## 5. Companion generation command not found

Symptoms:
- `companion` fails with `command not found`

Likely causes:
- repo package is not installed in the active environment
- editable install points somewhere unexpected
- the active shell is using the wrong environment

What to do:
1. activate the intended environment
2. run `which generate-companion-batch`
3. run `python -c "import omero_import_pipeline.generate_companion_batch as m; print(m.__file__)"`
4. reinstall the repo with `pip install -e .`

## 6. Companion generation fails on specific plates

Symptoms:
- `companion` starts but prints errors for one or more plate directories

Likely causes:
- a plate directory contains no `.ome.tiff` files
- a plate has an unexpected file layout
- OME metadata generation logic hit bad inputs

What to do:
1. inspect the specific plate directory
2. verify that `.ome.tiff` files exist
3. rerun the stage after fixing the plate contents

## 7. Permissions stage fails

Symptoms:
- `permissions` exits non-zero
- logs show `sudo` or ownership errors

Likely causes:
- insufficient privilege
- wrong `RACCOON_CHOWN_USER` or `RACCOON_CHOWN_GROUP`
- filesystem policy conflict

What to do:
1. verify config values
2. verify that the operator can use `sudo`
3. test the relevant chown/chmod command manually on one path
4. rerun `permissions`

If this stage is not needed in your environment, simplify it rather than keeping a failing step.

## 8. Missing screen mapping prefixes

Symptoms:
- `imports` fails during prefix validation
- error lists prefixes missing from `screen_mapping.json`

Likely causes:
- new prefix not yet added to mapping
- typo in plate directory names
- dataset contents not what you expected

What to do:
1. inspect the listed prefixes
2. confirm they are real
3. update `screen_mapping.json` if needed
4. rerun `imports`

This is an intentional hard failure.

## 9. Wrong OMERO user appears in generated import commands

Symptoms:
- `omero_import_commands.txt` shows the wrong `-u <user>` value

Likely causes:
- generator is still using a stale hardcoded user
- `run_omero_pipeline.sh` is not passing the configured OMERO user
- the installed CLI is coming from an old repo/version

What to do:
1. check `OMERO_DEFAULT_USER` in `config.sh`
2. run `which generate-omero-imports`
3. confirm the installed command comes from this repo
4. rerun `imports`

## 10. Wrong screen ID appears in generated imports

Symptoms:
- generated command file or manifest uses the wrong `screen_id`

Likely causes:
- `screen_mapping.json` points to the wrong screen
- the target screen differs for the current OMERO user
- screen override was not provided when needed

What to do:
1. verify the desired target screen in OMERO
2. inspect `screen_mapping.json`
3. use `SCREEN_ID_OVERRIDE=<id>` when needed
4. rerun `imports`

## 11. Generated commands file lands in the wrong directory

Symptoms:
- `imports` claims command generation succeeded but the file is not found where expected

Likely causes:
- generator writes to the current working directory
- pipeline did not `cd` into the dataset directory first

What to do:
1. look in the repo root or current shell directory for the generated file
2. confirm the pipeline runs the generator from inside the dataset directory
3. rerun `imports`

## 12. Import command parsing fails

Symptoms:
- `imports` fails while converting `omero_import_commands.txt` into the manifest

Likely causes:
- generator output format changed
- parser assumed one path per line but commands now group multiple plate paths
- target syntax changed from one form to another

What to do:
1. inspect `omero_import_commands.txt`
2. compare it to the parser expectations
3. update the parser to match the actual grouped command format
4. rerun `imports`

## 13. Manifest paths do not exist on the host

Symptoms:
- `import` reports that manifest plate paths do not exist
- paths look like `/omero_images/...`

Likely causes:
- manifest paths are container-visible paths, not host paths
- import stage is validating them on the host instead of inside the container

What to do:
1. confirm whether the manifest uses container paths
2. validate paths inside the OMERO container, not on the host
3. rerun `import`

This was a real failure mode during development.

## 14. `stdin is not a terminal: cannot request password`

Symptoms:
- `import` starts, then OMERO fails trying to prompt for a password

Likely causes:
- OMERO CLI is running in a non-interactive context
- no password was supplied at runtime

What to do:
1. make sure the shell pipeline prompts once before import execution
2. pass the password explicitly at runtime to the OMERO CLI
3. rerun `import`

The current pipeline handles this by prompting once and reusing the password during the import loop.

## 15. Import review mode seems to do nothing

Symptoms:
- `import` only tells you where the manifest is and exits

Cause:
- `EXECUTE_IMPORTS=0`

What to do:
1. review the manifest
2. if ready, set `EXECUTE_IMPORTS=1`
3. rerun `import`

This is intentional behavior.

## 16. Import fails inside OMERO after authentication succeeds

Symptoms:
- import starts and authenticates, but one or more plates fail

Likely causes:
- malformed companion metadata
- problematic plate directory contents
- wrong target screen
- OMERO-side server issue

What to do:
1. inspect the import log carefully
2. identify the failing plate path
3. inspect that plate directory directly
4. verify the target screen and user
5. rerun once the specific issue is fixed

Do not run cleanup before understanding the failure.

## 17. Cleanup is refused

Symptoms:
- `cleanup-local` exits with a confirmation or retention message

Likely causes:
- `CONFIRM_DELETE=YES` not set
- dataset age is below `LOCAL_RETENTION_DAYS`

What to do:
1. confirm you really want to delete the build dataset
2. rerun with explicit confirmation
3. adjust retention only if you intentionally want more aggressive cleanup

The refusal is deliberate.

## 18. Cleanup removes data you still needed

Symptoms:
- you need to inspect or re-import plates, but the build dataset is gone

Root cause:
- cleanup ran too early

What to do:
1. regenerate the dataset if needed
2. delay cleanup in future
3. consider increasing `LOCAL_RETENTION_DAYS`

This is why cleanup is not part of `all`.

## 19. Wrong command version is being used

Symptoms:
- stage behavior does not match the current repo code
- generated outputs still reflect old hardcoded values

Likely causes:
- the shell resolves an older installed package
- editable install is stale
- environment is not the one you think it is

What to do:
1. run `which generate-ome-tiffs-batch`
2. run `which generate-companion-batch`
3. run `which generate-omero-imports`
4. verify the Python module path with `python -c ... print(__file__)`
5. reinstall the repo in editable mode if needed

## 20. Config drift causes unexpected behavior

Symptoms:
- paths, users, screen IDs, or container settings do not match expectations

Likely causes:
- stale `config.sh`
- copied config from another machine or user
- README and code evolved but local config did not

What to do:
1. compare `config.sh` to `config.example.sh`
2. verify the active OMERO user, screen override, and build root
3. rerun the affected stage only after fixing config

## Operational guidance

When a stage fails:
1. stop
2. inspect the latest log file
3. inspect the relevant generated files and dataset directory
4. fix the root cause
5. rerun the failed stage
6. rerun `validate`

Do not try to force later stages through a broken earlier state.

## Recommended future hardening

The next useful improvements would be:
- add a `preflight` stage
- verify OMERO container visibility of the image root
- validate required CLI commands before a run starts
- add a more explicit dataset state marker file
- improve auth/session handling if passwordless flows become available
