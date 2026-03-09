#!/usr/bin/env bash
# Wrapper: generates token tree + compressed repomix output
set -euo pipefail

# Optional input directory (defaults to repo root)
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# file names
TREE_FILE="token-tree"
COMPRESSED_FILE="repo-compressed"
LOSSLESS_FILE="repomix"
DOCS_ONLY_FILE="repomix-docs"
GIT_RANKED_FILE="repomix-git-ranked"
DIFF_SUMMARY="diff-summary"
GIT_TOP_20="gitlog-top20"

# input /output directories
INPUT_PATH="scripts/repomix"
OUTPUT_PATH="docs/repomix"

# output absolute filepaths
OUT_DIR="$ROOT/$OUTPUT_PATH"
TOKEN_TREE_FILE="$OUT_DIR/$TREE_FILE.txt"
COMPRESSED_REPO_FILE="$OUT_DIR/$COMPRESSED_FILE.xml"
LOSSLESS_REPO_FILE="$OUT_DIR/$LOSSLESS_FILE.xml"
DOCS_ONLY_REPO_FILE="$OUT_DIR/$DOCS_ONLY_FILE.xml"
GIT_RANKED_REPO_FILE="$OUT_DIR/$GIT_RANKED_FILE.xml"
GITLOG_TOP_FILE="$OUT_DIR/$GIT_TOP_20.txt"
DIFF_SUMMARY="$OUT_DIR/$DIFF_SUMMARY.xml"

# input absolute filepaths
INPUT_DIR="$ROOT/$INPUT_PATH"
TOKEN_TREE_SCRIPT="$INPUT_DIR/$TREE_FILE.sh"
COMPRESS_SCRIPT="$INPUT_DIR/$COMPRESSED_FILE.sh"
LOSSLESS_SCRIPT="$INPUT_DIR/$LOSSLESS_FILE.sh"
DOCS_ONLY_SCRIPT="$INPUT_DIR/generate-repomix-docs.sh"
GIT_RANKED_SCRIPT="$INPUT_DIR/generate-repomix-git-ranked.sh"
DIFF_SUMMARY_SCRIPT="$INPUT_DIR/generate-diff-summary.sh"
GIT_RANKED_INCLUDE_LOGS_COUNT="${REPOMIX_GIT_RANKED_INCLUDE_LOGS_COUNT:-200}"

echo "File set up..."
# make output dir if not exists
mkdir -p "$OUT_DIR"

# delete only the artifacts this wrapper regenerates
rm -f \
  "$TOKEN_TREE_FILE" \
  "$COMPRESSED_REPO_FILE" \
  "$LOSSLESS_REPO_FILE" \
  "$DOCS_ONLY_REPO_FILE" \
  "$GIT_RANKED_REPO_FILE" \
  "$GITLOG_TOP_FILE" \
  "$DIFF_SUMMARY"

# project-level logging
PROJECT_DIR="$(basename "$ROOT")"
# relative filepaths
TREE_FILE="$OUTPUT_PATH/$TREE_FILE.txt"
COMPRESSED_FILE_NAME="$OUTPUT_PATH/$COMPRESSED_FILE.xml"
LOSSLESS_FILE_NAME="$OUTPUT_PATH/$LOSSLESS_FILE.xml"
DOCS_ONLY_FILE_NAME="$OUTPUT_PATH/$DOCS_ONLY_FILE.xml"
GIT_RANKED_FILE_NAME="$OUTPUT_PATH/$GIT_RANKED_FILE.xml"
GITLOG_TOP_FILE_NAME="$OUTPUT_PATH/$GIT_TOP_20.txt"
DIFF_SUMMArY_FILE="$OUTPUT_PATH/$DIFF_SUMMARY.xml"


echo "Generating token count tree for $PROJECT_DIR at $TREE_FILE"
bash "$TOKEN_TREE_SCRIPT" "$ROOT" "$TOKEN_TREE_FILE"
echo "Success!"
echo

echo "Generating compressed repomix file for $PROJECT_DIR at $COMPRESSED_FILE_NAME"
bash "$COMPRESS_SCRIPT" "$ROOT" "$COMPRESSED_REPO_FILE"
echo "Success!"
echo

echo "Generating repomix file for $PROJECT_DIR at $LOSSLESS_FILE_NAME"
bash "$LOSSLESS_SCRIPT" "$ROOT" "$LOSSLESS_REPO_FILE"
echo "Success!"
echo

echo "Generating docs-only repomix file for $PROJECT_DIR at $DOCS_ONLY_FILE_NAME"
bash "$DOCS_ONLY_SCRIPT" "$ROOT" "$DOCS_ONLY_REPO_FILE"
echo "Success!"
echo

echo "Generating git-ranked repomix file for $PROJECT_DIR at $GIT_RANKED_FILE_NAME"
bash "$GIT_RANKED_SCRIPT" "$ROOT" "$GIT_RANKED_REPO_FILE" "$GIT_RANKED_INCLUDE_LOGS_COUNT"
echo "Success!"
echo

echo "Generating top-file git history at $GITLOG_TOP_FILE_NAME"
(
  cd "$ROOT"
  bash "$DIFF_SUMMARY_SCRIPT"
)
echo "Success!"
echo

echo "Artifacts:"

print_artifact() {
  local file_path="$1"
  local display_name="$2"

  if [[ -f "$file_path" ]]; then
    chars=$(wc -c < "$file_path" | tr -d ' ')
    tokens=$((chars / 4))
    echo " - $display_name (~$tokens tokens, $chars chars)"
  else
    echo " - $display_name (missing)"
  fi
}

print_artifact "$TOKEN_TREE_FILE" "$TREE_FILE"
print_artifact "$COMPRESSED_REPO_FILE" "$COMPRESSED_FILE_NAME"
print_artifact "$LOSSLESS_REPO_FILE" "$LOSSLESS_FILE_NAME"
print_artifact "$DOCS_ONLY_REPO_FILE" "$DOCS_ONLY_FILE_NAME"
print_artifact "$GIT_RANKED_REPO_FILE" "$GIT_RANKED_FILE_NAME"
print_artifact "$GITLOG_TOP_FILE" "$GITLOG_TOP_FILE_NAME"
