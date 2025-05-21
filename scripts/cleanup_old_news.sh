#!/usr/bin/env bash
# cleanup_old_news.sh

# exit on any error
set -e

# run against the checked-out `data/` folder
DATA_DIR="data"

# (optional) log what we’re about to delete
echo "Cleaning up JSON files older than 7 days in $DATA_DIR …"

# delete any *.json (except all_news.json) older than 7 days
find "$DATA_DIR" -maxdepth 1 \
     -type f \
     -name '*.json' \
     ! -name 'all_news.json' \
     -mtime +7 \
     -print -delete
