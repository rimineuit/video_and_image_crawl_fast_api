import os
import json
import argparse
from typing import Iterable, List, Tuple, Any

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

def normalize_db_url(db_url: str) -> str:
    if db_url.startswith("postgres://"):
        return db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    if db_url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + db_url.split("://", 1)[1]
    return db_url

def read_data(engine, eer_min: float, duration_max: int) -> pd.DataFrame:
    query = f"""
            SELECT d.*
            FROM tiktok_trend_capture_detail d
            JOIN tiktok_trend_capture c 
            ON d.video_id = c.video_id
            WHERE d.eer_score > {eer_min}
            AND (
                    NULLIF(btrim(d.transcripts),  '') IS NOT NULL
                OR NULLIF(btrim(d.description), '') IS NOT NULL
                )
            AND d.duration <= {duration_max}
            ORDER BY d.video_id ASC;
    """
    df = pd.read_sql_query(query, con=engine, index_col="video_id")
    df.index.name = "id"
    return df

def clean_text_series(desc: pd.Series, tran: pd.Series) -> pd.Series:
    s = (desc.fillna('').astype(str).str.strip() + " " +
         tran.fillna('').astype(str).str.strip())

    s = (s.str.lower()
          .str.replace(r'https?://\S+|www\.\S+', ' ', regex=True)
          .str.replace(r'[^\w\s]', ' ', regex=True)
          .str.replace(r'_', ' ', regex=True)
          .str.replace(r'\s+', ' ', regex=True)
          .str.strip())
    return s

def unique_preserve_order(iterable: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in iterable:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def build_ngrams_df(df_text: pd.DataFrame, nmin: int, nmax: int,
                    distinct: bool = True, drop_empty: bool = True) -> pd.DataFrame:
    if 'text' not in df_text.columns:
        raise ValueError("df_text phải có cột 'text'.")

    rows: List[Tuple[Any, int, List[str]]] = []
    text_series = df_text['text'].fillna('').astype(str)

    for id_, text in text_series.items():
        toks = text.split()
        L = len(toks)
        for n in range(nmin, nmax + 1):
            if L < n:
                grams_list: List[str] = []
            else:
                grams_iter = (" ".join(toks[i:i + n]) for i in range(L - n + 1))
                grams_list = unique_preserve_order(grams_iter) if distinct else list(grams_iter)
            rows.append((id_, n, grams_list))

    out = pd.DataFrame(rows, columns=['id', 'n', 'list_n_gram'])
    if drop_empty:
        out = out[out['list_n_gram'].map(bool)].reset_index(drop=True)
    return out


def compute_groups(df_text: pd.DataFrame,
                   nmin: int, nmax: int, min_id_count: int) -> pd.DataFrame:
    ngrams_df = build_ngrams_df(df_text, nmin=nmin, nmax=nmax, distinct=True, drop_empty=True)

    exploded = (
        ngrams_df
        .explode('list_n_gram', ignore_index=False)
        .rename(columns={'list_n_gram': 'ngram'})
    )
    exploded = exploded[exploded['ngram'].notna() & (exploded['ngram'] != '')]
    exploded = exploded.drop_duplicates(subset=['id', 'n', 'ngram'])

    dups = (
        exploded.groupby(['n', 'ngram'])['id']
        .agg(lambda s: sorted(set(s)))
        .reset_index()
        .rename(columns={'id': 'ids'})
    )
    dups['id_count'] = dups['ids'].str.len()

    dups = dups[dups['id_count'] >= 2].sort_values(
        ['n', 'id_count'], ascending=[True, False]
    ).reset_index(drop=True)

    dups = dups.copy()
    dups['ids'] = dups['ids'].map(lambda L: sorted(set(L)))
    dups['ids_key'] = dups['ids'].map(tuple)
    dups['n_max'] = dups.groupby('ids_key')['n'].transform('max')
    dups_keep = dups[dups['n'] == dups['n_max']].drop(columns=['n_max']).copy()

    groups = (
        dups_keep
        .groupby(['ids_key', 'n'], as_index=False)
        .agg(
            ngrams=('ngram', lambda s: sorted(set(s))),
            ngram_count=('ngram', 'nunique')
        )
    )
    groups['ids'] = groups['ids_key'].map(list)
    groups['id_count'] = groups['ids'].str.len()
    groups = groups[['n', 'ids', 'id_count', 'ngram_count', 'ngrams']]

    g = groups.copy()
    g['ids'] = g['ids'].map(lambda L: sorted(set(L)))
    g['ids_set'] = g['ids'].map(frozenset)
    g_sorted = g.sort_values(['n', 'id_count', 'ngram_count'],
                             ascending=[False, False, False]).reset_index(drop=True)

    kept_idx: List[int] = []
    kept: List[Tuple[int, frozenset]] = []
    for i, row in g_sorted.iterrows():
        s = row['ids_set']
        ncur = int(row['n'])
        conflict = any(((nkept > ncur) or (nkept == ncur)) and (not s.isdisjoint(ks))
                       for nkept, ks in kept)
        if conflict:
            continue
        kept_idx.append(i)
        kept.append((ncur, s))

    groups_pruned = (
        g_sorted.loc[kept_idx]
        .drop(columns=['ids_set'])
        .sort_values(['id_count', 'n', 'ngram_count'], ascending=[False, False, False])
        .reset_index(drop=True)
    )

    groups_pruned = groups_pruned[groups_pruned['id_count'] >= min_id_count].reset_index(drop=True)
    return groups_pruned

import sys
def main():
    parser = argparse.ArgumentParser(description="In JSON của DataFrame groups_pruned (không giới hạn).")
    parser.add_argument("--nmin", type=int, default=2, help="Độ dài n-gram nhỏ nhất (mặc định: 2)")
    parser.add_argument("--nmax", type=int, default=100, help="Độ dài n-gram lớn nhất (mặc định: 20)")
    parser.add_argument("--eer-min", type=float, default=1.0, help="Ngưỡng eer_score > eer_min (mặc định: 1)")
    parser.add_argument("--duration-max", type=int, default=60, help="Chỉ lấy video có duration <= (mặc định: 30s)")
    parser.add_argument("--min-id-count", type=int, default=2, help="Giữ nhóm xuất hiện ở >= min id (mặc định: 2)")
    parser.add_argument("--pretty", action="store_true", help="In JSON đẹp (indent=2)")

    # NEW: hỗ trợ truyền URL qua flag hoặc positional
    parser.add_argument("--db-url", dest="db_url_flag", help="PostgreSQL connection URL (override env DATABASE_URL)")
    parser.add_argument("db_url_pos", nargs="?", help="PostgreSQL connection URL (positional, optional)")

    args = parser.parse_args()

    # Ưu tiên: --db-url > positional > env
    db_url = args.db_url_flag or args.db_url_pos or os.getenv("DATABASE_URL")

    if not db_url:
        parser.error("Thiếu DB URL: truyền --db-url, hoặc positional db_url, hoặc đặt env DATABASE_URL")

    # (Tuỳ bạn: chuẩn hoá prefix nếu dùng SQLAlchemy)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    db_url = normalize_db_url(db_url)

    engine = create_engine(db_url, pool_pre_ping=True)

    df = read_data(engine, eer_min=args.eer_min, duration_max=args.duration_max)

    desc = df.get('description', pd.Series(index=df.index)).fillna('').astype(str)
    tran = df.get('transcripts', pd.Series(index=df.index)).fillna('').astype(str)
    clean_text = clean_text_series(desc, tran)
    df_text = pd.DataFrame({'text': clean_text}, index=df.index)
    df_text.index.name = "id"

    groups_pruned = compute_groups(df_text, nmin=args.nmin, nmax=args.nmax, min_id_count=args.min_id_count)

    # ✅ In CHỈ nội dung groups_pruned
    out = groups_pruned.to_dict(orient="records")
    print("Results:\n")
    print(json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()