import pandas as pd
from pathlib import Path

MASTER = Path("Master_Entities_Table - Originator_Platforms_Funds_and_Competitors.csv")
OUT    = Path("Entity_GNews_Queries.csv")

# ------------ helper ------------
def build_query_short(aliases: str, max_chars: int = 480) -> str:
    alias_terms = [f'"{a.strip()}"' for a in aliases.split(";") if a.strip()]
    base_terms  = ["loan", "lending", "credit", "fintech"]
    query       = " OR ".join(alias_terms + base_terms)

    if len(query) > max_chars:          # trim if necessary
        for i in range(len(alias_terms), 0, -1):
            q = " OR ".join(alias_terms[:i] + base_terms)
            if len(q) <= max_chars:
                query = q
                break
    return query
# ---------------------------------

df = pd.read_csv(MASTER, dtype=str)

df_out = (
    df[["entity_name", "aliases"]]
      .assign(QUERY_short=lambda d: d["aliases"].apply(build_query_short))
)

df_out.to_csv(OUT, index=False)
print(f"→ Saved {len(df_out):,} queries to {OUT}")
