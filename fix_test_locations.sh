#!/bin/bash
#
# Move misplaced test files from the scripts/ directory to the tests/ directory
# to ensure they are discovered by the CI test runner. This script uses 'git mv'
# to preserve file history.
#
# Run this script from the root of the expositor-archive-project repository.
#

# Exit immediately if a command exits with a non-zero status.
set -e

# Define source and destination directories relative to the project root.
SCRIPTS_DIR="scripts"
TESTS_DIR="tests"

# Create destination directories if they don't exist.
# 'git mv' requires the destination directory to exist.
mkdir -p "$TESTS_DIR/structuring"
mkdir -p "$TESTS_DIR/audit"

# --- Define files to move ---
# {source_path}:{destination_dir}
declare -A files_to_move=(
    ["$SCRIPTS_DIR/structuring/test_06_section_extractor.py"]="$TESTS_DIR/structuring/"
    ["$SCRIPTS_DIR/audit/test_10_pipeline_quality_audit.py"]="$TESTS_DIR/audit/"
    ["$SCRIPTS_DIR/audit/test_11_publication_id_consistency_audit.py"]="$TESTS_DIR/audit/"
    ["$SCRIPTS_DIR/test_08_title_consistency_audit.py"]="$TESTS_DIR/audit/"
    ["$SCRIPTS_DIR/test_09_low_confidence_scripture_audit.py"]="$TESTS_DIR/audit/"
)

# --- Move test files using git mv ---
MOVED_COUNT=0
for src in "${!files_to_move[@]}"; do
    dest=${files_to_move[$src]}
    if [ -f "$src" ]; then
        echo "Moving $src to $dest..."
        git mv "$src" "$dest"
        MOVED_COUNT=$((MOVED_COUNT + 1))
    fi
done

echo ""
echo "Moved $MOVED_COUNT misplaced test file(s) to the tests/ directory and staged them for commit."
echo "Run 'git status' to review the changes, then commit them to resolve the test discovery issue."