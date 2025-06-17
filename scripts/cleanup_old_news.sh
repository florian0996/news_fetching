#!/usr/bin/env bash
# cleanup_old_news.sh
set -e

# where GitHub Actions has checked out your repo
DATA_DIR="${GITHUB_WORKSPACE}/data"
cd "$DATA_DIR"

# how many days to keep
RETENTION_DAYS=5
# cutoff in seconds since epoch
CUTOFF=$(( $(date +%s) - RETENTION_DAYS * 86400 ))

echo "Removing JSON files whose embedded date is older than $RETENTION_DAYS days…"

for f in *.json; do
  # never remove these
  [[ "$f" == "all_news.json" ]] && continue
  [[ "$f" == ".gitkeep"    ]] && continue

  # extract YYYY-MM-DD from the filename
  if [[ "$f" =~ ([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
    filedate=${BASH_REMATCH[1]}
    # convert to epoch seconds
    file_ts=$(date -d "$filedate" +%s)
    if (( file_ts < CUTOFF )); then
      echo "Deleting $f (date $filedate)"
      rm "$f"
    fi
  else
    echo "Skipping $f (no date in name)"
  fi
done
