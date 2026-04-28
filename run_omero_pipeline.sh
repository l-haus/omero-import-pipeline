#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/config.sh"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "ERROR: config.sh not found at ${CONFIG_FILE}" >&2
  echo "Copy config.example.sh to config.sh and edit it first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${CONFIG_FILE}"

DATASET="${1:-}"
STAGE="${2:-all}"

if [[ -z "${DATASET}" ]]; then
  echo "Usage: $0 <dataset_name> [stage]"
  echo "Stages: generate, validate-local, companion, permissions, imports, import, validate, cleanup-local, all"
  exit 1
fi

LOG_DIR="${SCRIPT_DIR}/logs/${DATASET}"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/$(date +%Y%m%d_%H%M%S)_${STAGE}.log"

exec > >(tee -a "${LOG_FILE}") 2>&1

RAW_DATASET="${RAW_ROOT}/${DATASET}"
BUILD_DATASET="${BUILD_ROOT}/${DATASET}"

SCREEN_MAPPING_PATH="${SCRIPT_DIR}/${SCREEN_MAPPING_FILE}"
IMPORT_COMMANDS_PATH="${BUILD_DATASET}/${IMPORT_COMMANDS_FILENAME}"
IMPORT_MANIFEST_PATH="${BUILD_DATASET}/${IMPORT_MANIFEST_FILENAME}"

timestamp() {
  date +"%Y-%m-%d %H:%M:%S"
}

log() {
  echo "[$(timestamp)] $*"
}

die() {
  echo "[$(timestamp)] ERROR: $*" >&2
  exit 1
}

check_dir() {
  local path="$1"
  [[ -d "${path}" ]] || die "Directory not found: ${path}"
}

check_file() {
  local path="$1"
  [[ -f "${path}" ]] || die "File not found: ${path}"
}

load_mapping_json() {
  python3 - <<PY
from pathlib import Path
import json
path = Path(${SCREEN_MAPPING_PATH@Q})
print(json.dumps(json.loads(path.read_text())))
PY
}

run_in_microscopy_env() {
  local cmd="$1"

  if command -v conda >/dev/null 2>&1; then
    bash -lc "
      set -euo pipefail
      source ~/.bashrc >/dev/null 2>&1 || true
      conda activate \"${MICROSCOPY_UTILS_ENV}\"
      ${cmd}
    "
    return
  fi

  if [[ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]]; then
    bash -lc "
      set -euo pipefail
      source \"$HOME/miniconda3/etc/profile.d/conda.sh\"
      conda activate \"${MICROSCOPY_UTILS_ENV}\"
      ${cmd}
    "
    return
  fi

  if [[ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]]; then
    bash -lc "
      set -euo pipefail
      source \"$HOME/anaconda3/etc/profile.d/conda.sh\"
      conda activate \"${MICROSCOPY_UTILS_ENV}\"
      ${cmd}
    "
    return
  fi

  die "Could not find a working conda initialization path"
}

validate_screen_mapping_prefixes() {
  local dataset_path="$1"
  local mapping_json="$2"

  log "Validating plate prefixes against screen mapping"

  python3 - <<PY
import json
import pathlib
import sys

dataset = pathlib.Path(${dataset_path@Q})
mapping = json.loads(${mapping_json@Q})

if not dataset.exists():
    print(f'Dataset path does not exist: {dataset}', file=sys.stderr)
    sys.exit(2)

prefixes = set()
for p in dataset.iterdir():
    if p.is_dir():
        prefixes.add(p.name[:4])

missing = sorted(prefix for prefix in prefixes if prefix not in mapping)
if missing:
    print('Missing screen mapping for prefixes: ' + ', '.join(missing), file=sys.stderr)
    sys.exit(1)

print('Screen mapping validation passed for prefixes:', ', '.join(sorted(prefixes)) if prefixes else '(none)')
PY
}

stage_generate() {
  log "Stage: generate"
  check_dir "${RAW_DATASET}"

  mkdir -p "${BUILD_DATASET}"
  run_in_microscopy_env "generate-ome-tiffs-batch \"${RAW_DATASET}\" \"${BUILD_DATASET}\" --workers \"${GENERATE_WORKERS}\""

  check_dir "${BUILD_DATASET}"
  log "Generate stage complete"
}

stage_validate_local() {
  log "Stage: validate-local"
  check_dir "${BUILD_DATASET}"

  python3 - <<PY
from pathlib import Path
import sys

dataset = Path(${BUILD_DATASET@Q})

if not dataset.exists():
    print(f'Missing build dataset: {dataset}', file=sys.stderr)
    sys.exit(1)

plate_dirs = [p for p in dataset.iterdir() if p.is_dir()]
if not plate_dirs:
    print(f'No plate directories found in {dataset}', file=sys.stderr)
    sys.exit(1)

ome_files = list(dataset.rglob('*.ome.tif')) + list(dataset.rglob('*.ome.tiff'))
print(f'Found {len(plate_dirs)} plate directories in {dataset}')
print(f'Found {len(ome_files)} OME-TIFF files in {dataset}')

if len(ome_files) == 0:
    print(f'No OME-TIFF files found in {dataset}', file=sys.stderr)
    sys.exit(1)
PY

  log "Local validation stage complete"
}

stage_companion() {
  log "Stage: companion"
  check_dir "${BUILD_DATASET}"

  run_in_microscopy_env "generate-companion-batch \"${BUILD_DATASET}\""
  log "Companion stage complete"
}

stage_permissions() {
  log "Stage: permissions"
  check_dir "${BUILD_DATASET}"

  sudo chown -R "${RACCOON_CHOWN_USER}:${RACCOON_CHOWN_GROUP}" "${BUILD_DATASET}"
  sudo find "${BUILD_DATASET}" -type f -exec chmod o+r {} +
  sudo find "${BUILD_DATASET}" -type d -exec chmod o+rx {} +

  log "Permissions stage complete"
}

stage_imports() {
  local mapping_json
  log "Stage: imports"

  check_file "${SCREEN_MAPPING_PATH}"
  check_dir "${BUILD_DATASET}"

  mapping_json="$(load_mapping_json)"
  validate_screen_mapping_prefixes "${BUILD_DATASET}" "${mapping_json}"

  run_in_microscopy_env "generate-omero-imports \"${BUILD_DATASET}\" \"${SCREEN_MAPPING_PATH}\""

  check_file "${IMPORT_COMMANDS_PATH}"
  log "Import command generation complete: ${IMPORT_COMMANDS_PATH}"

  python3 - <<PY
from pathlib import Path
import re
import sys

commands = Path(${IMPORT_COMMANDS_PATH@Q})
manifest = Path(${IMPORT_MANIFEST_PATH@Q})

if not commands.exists():
    print(f'Missing commands file: {commands}', file=sys.stderr)
    sys.exit(1)

pattern = re.compile(r'-d\\s+Screen:(\\d+)\\s+(.+)$')

rows = []
for raw in commands.read_text().splitlines():
    raw = raw.strip()
    if not raw:
        continue
    m = pattern.search(raw)
    if not m:
        print(f'Could not parse import command: {raw}', file=sys.stderr)
        sys.exit(1)
    screen_id, plate_path = m.groups()
    rows.append((screen_id, plate_path))

if not rows:
    print('No import rows parsed from command file', file=sys.stderr)
    sys.exit(1)

manifest.write_text(
    '# screen_id\\tplate_path\\n' +
    ''.join(f'{screen_id}\\t{plate_path}\\n' for screen_id, plate_path in rows)
)

print(f'Wrote manifest: {manifest}')
print(f'Rows: {len(rows)}')
PY

  check_file "${IMPORT_MANIFEST_PATH}"
  log "Import manifest generation complete: ${IMPORT_MANIFEST_PATH}"
}

stage_import() {
  log "Stage: import"
  check_file "${IMPORT_MANIFEST_PATH}"

  if [[ "${EXECUTE_IMPORTS}" != "1" ]]; then
    log "EXECUTE_IMPORTS=0, so imports will not be executed automatically."
    log "Generated import manifest is located at: ${IMPORT_MANIFEST_PATH}"
    log "Review it with:"
    echo "cat \"${IMPORT_MANIFEST_PATH}\""
    log "Set EXECUTE_IMPORTS=1 in config.sh to execute imports automatically."
    return 0
  fi

  log "EXECUTE_IMPORTS=1, executing imports from manifest"

  while IFS=$'\t' read -r screen_id plate_path || [[ -n "${screen_id:-}" || -n "${plate_path:-}" ]]; do
    [[ -z "${screen_id:-}" ]] && continue
    [[ "${screen_id:0:1}" == "#" ]] && continue
    [[ -z "${plate_path:-}" ]] && die "Malformed manifest line: missing plate path"

    [[ -d "${plate_path}" ]] || die "Plate path does not exist: ${plate_path}"

    echo "[IMPORT] screen_id=${screen_id} plate_path=${plate_path}"

    docker exec -u omero-server "${OMERO_DOCKER_CONTAINER}" \
      "${OMERO_CLI_PATH}" import \
      -s localhost \
      -u "${OMERO_DEFAULT_USER}" \
      -d "Screen:${screen_id}" \
      "${plate_path}"
  done < "${IMPORT_MANIFEST_PATH}"

  log "Import stage complete"
}

stage_validate() {
  local mapping_json
  log "Stage: validate"

  check_file "${SCREEN_MAPPING_PATH}"
  check_dir "${RAW_DATASET}"
  log "Found raw dataset: ${RAW_DATASET}"

  if [[ -d "${BUILD_DATASET}" ]]; then
    log "Found build dataset: ${BUILD_DATASET}"
  else
    log "Build dataset not yet present: ${BUILD_DATASET}"
  fi

  mapping_json="$(load_mapping_json)"

  if [[ -d "${BUILD_DATASET}" ]]; then
    validate_screen_mapping_prefixes "${BUILD_DATASET}" "${mapping_json}"
  else
    log "Skipping screen mapping validation because build dataset is not present"
  fi

  if [[ -f "${IMPORT_MANIFEST_PATH}" ]]; then
    log "Found import manifest: ${IMPORT_MANIFEST_PATH}"
  else
    log "Import manifest not yet present: ${IMPORT_MANIFEST_PATH}"
  fi

  log "Validation stage complete"
}

stage_cleanup_local() {
  log "Stage: cleanup-local"

  if [[ "${CONFIRM_DELETE:-}" != "YES" ]]; then
    die "Refusing cleanup. Re-run with CONFIRM_DELETE=YES"
  fi

  check_dir "${BUILD_DATASET}"

  python3 - <<PY
from pathlib import Path
from datetime import datetime, timezone
import sys

dataset = Path(${BUILD_DATASET@Q})
retention_days = int(${LOCAL_RETENTION_DAYS@Q})

if not dataset.exists():
    print(f'Dataset does not exist: {dataset}', file=sys.stderr)
    sys.exit(1)

mtime = dataset.stat().st_mtime
age_days = (datetime.now(timezone.utc).timestamp() - mtime) / 86400

print(f'Dataset age: {age_days:.2f} days')
print(f'Retention threshold: {retention_days} days')

if age_days < retention_days:
    print('Dataset is too recent for cleanup', file=sys.stderr)
    sys.exit(1)
PY

  rm -rf "${BUILD_DATASET}"
  log "Build dataset deleted: ${BUILD_DATASET}"
}

run_stage() {
  case "$1" in
    generate) stage_generate ;;
    validate-local) stage_validate_local ;;
    companion) stage_companion ;;
    permissions) stage_permissions ;;
    imports) stage_imports ;;
    import) stage_import ;;
    validate) stage_validate ;;
    cleanup-local) stage_cleanup_local ;;
    all)
      stage_generate
      stage_validate_local
      stage_companion
      stage_permissions
      stage_imports
      stage_import
      ;;
    *)
      die "Unknown stage: $1"
      ;;
  esac
}

log "Dataset: ${DATASET}"
log "Stage: ${STAGE}"
log "Log file: ${LOG_FILE}"

run_stage "${STAGE}"

log "Done"
