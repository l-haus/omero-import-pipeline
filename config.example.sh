#!/usr/bin/env bash

# Copy this file to config.sh and edit it for your environment.

# -----------------------------
# Paths
# -----------------------------
RAW_ROOT="/media/battlestar/cell_painting/staging"
BUILD_ROOT="/mnt/data/cell_painting/omero_images"

# -----------------------------
# Environment
# -----------------------------
MICROSCOPY_UTILS_ENV="microscopy-utils"

# -----------------------------
# Repo assets / generated files
# -----------------------------
SCREEN_MAPPING_FILE="screen_mapping.json"
IMPORT_COMMANDS_FILENAME="omero_import_commands.txt"
IMPORT_MANIFEST_FILENAME="omero_import_manifest.tsv"

# -----------------------------
# OMERO
# -----------------------------
OMERO_CLI_PATH="/opt/omero/server/OMERO.server/bin/omero"
OMERO_DOCKER_CONTAINER="omero-omeroserver-1"
OMERO_DEFAULT_USER="deisingj"

# -----------------------------
# Generate
# -----------------------------
GENERATE_WORKERS=60

# -----------------------------
# Permissions
# -----------------------------
RACCOON_CHOWN_USER="brownlab"
RACCOON_CHOWN_GROUP="cell_painting"

# -----------------------------
# Import behavior
# -----------------------------
# 0 = only review manifest
# 1 = execute imports automatically
EXECUTE_IMPORTS=0

# -----------------------------
# Cleanup behavior
# -----------------------------
LOCAL_RETENTION_DAYS=7
