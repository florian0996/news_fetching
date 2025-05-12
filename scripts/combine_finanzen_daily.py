def main():
    seen = set()
    all_items = []

    # load all JSON files
    for filepath in sorted(data_dir.glob("finanzen_*.json")):
        with open(filepath, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"⚠️ Failed to load {filepath}: {e}")
                continue

            for item in data:
                # Only handle items using the new schema
                url = item.get("url")
                if not url:
                    continue  # skip old-format entries without 'url'
                if url in seen:
                    continue  # skip duplicates

                seen.add(url)
                all_items.append(item)

    # Save merged results
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    outfile = data_dir / f"finanzen_combined_{today}.json"
    with outfile.open("w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(all_items)} unique entries to {outfile}")
