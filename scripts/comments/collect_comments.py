#!/usr/bin/env python3
"""Frazeologik iboralar va ko'chma ma'noli so'zlar qatnashgan izohlarni yig'ish.

Manbalar:
  youtube   - YouTube video izohlari (API kaliti shart emas)
  telegram  - ochiq Telegram kanallaridagi post izohlari (Telethon, API ID kerak)
  file      - boshqa yo'l bilan olingan izohlar (CSV / JSONL / TXT)

Har bir topilgan moslik natija CSV faylida alohida qator bo'ladi:
bitta izohda 3 ta ibora bo'lsa - 3 qator (izoh_id bir xil).

Misollar:
  python scripts/comments/collect_comments.py youtube \\
      --url https://www.youtube.com/watch?v=XXXXXXXXXXX --out natija.csv
  python scripts/comments/collect_comments.py youtube \\
      --search "o'zbek kino" --search "kun.uz yangiliklar" --videos-per-query 20
  python scripts/comments/collect_comments.py telegram \\
      --channel kunuzofficial --channel daryo --posts 300
  python scripts/comments/collect_comments.py file --input izohlar.csv --text-column text
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Iterable, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lexicon import LexiconMatcher  # noqa: E402

FIELDS = [
    "izoh_id", "manba", "manba_id", "manba_nomi", "muallif", "sana", "layklar",
    "izoh_matni", "sentiment", "leksikon", "birlik", "topilgan_qism", "izoh_manosi",
    "uslub", "manba_sahifa", "tekshiruv_belgisi",
]


# --------------------------------------------------------------------------
# Manbalar: har biri {id, source, source_id, source_title, author, date, likes, text}
# --------------------------------------------------------------------------

def youtube_video_ids(args) -> Iterator[tuple[str, str]]:
    """(video_url, sarlavha) juftliklarini qaytaradi."""
    for url in args.url or []:
        yield url, ""
    if args.search or args.channel:
        try:
            import yt_dlp
        except ImportError:
            sys.exit("--search / --channel uchun yt-dlp kerak: pip install yt-dlp")
        opts = {"quiet": True, "extract_flat": True, "skip_download": True}
        targets = [f"ytsearch{args.videos_per_query}:{q}" for q in args.search or []]
        targets += [c.rstrip("/") + "/videos" if "youtube.com" in c
                    else f"https://www.youtube.com/@{c.lstrip('@')}/videos"
                    for c in args.channel or []]
        with yt_dlp.YoutubeDL(opts) as ydl:
            for target in targets:
                try:
                    info = ydl.extract_info(target, download=False)
                except Exception as exc:  # tarmoq / topilmadi
                    print(f"  ! {target}: {exc}", file=sys.stderr)
                    continue
                entries = list(info.get("entries") or [])[: args.videos_per_query]
                print(f"  {target}: {len(entries)} ta video", file=sys.stderr)
                for e in entries:
                    vid = e.get("id")
                    if vid:
                        yield f"https://www.youtube.com/watch?v={vid}", e.get("title") or ""


def youtube_comments(args) -> Iterator[dict]:
    try:
        from youtube_comment_downloader import SORT_BY_POPULAR, SORT_BY_RECENT, YoutubeCommentDownloader
    except ImportError:
        sys.exit("YouTube uchun kutubxona kerak: pip install youtube-comment-downloader")
    downloader = YoutubeCommentDownloader()
    sort = SORT_BY_POPULAR if args.sort == "popular" else SORT_BY_RECENT
    seen_videos = set()
    for url, title in youtube_video_ids(args):
        if url in seen_videos:
            continue
        seen_videos.add(url)
        vid = url.split("v=")[-1].split("&")[0] if "v=" in url else url.rsplit("/", 1)[-1]
        print(f"→ YouTube: {url} {title[:60]}", file=sys.stderr)
        try:
            for i, c in enumerate(downloader.get_comments_from_url(url, sort_by=sort)):
                if args.comments_per_video and i >= args.comments_per_video:
                    break
                yield {
                    "id": c.get("cid"), "source": "youtube", "source_id": vid,
                    "source_title": title, "author": c.get("author", ""),
                    "date": c.get("time", ""), "likes": c.get("votes", ""),
                    "text": c.get("text", ""),
                }
        except Exception as exc:
            print(f"  ! {url}: {exc}", file=sys.stderr)
        time.sleep(args.delay)


def telegram_comments(args) -> Iterator[dict]:
    try:
        from telethon.sync import TelegramClient
    except ImportError:
        sys.exit("Telegram uchun kutubxona kerak: pip install telethon")
    api_id = args.api_id or os.environ.get("TG_API_ID")
    api_hash = args.api_hash or os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        sys.exit("TG_API_ID va TG_API_HASH kerak (https://my.telegram.org -> API development tools)")
    with TelegramClient(args.session, int(api_id), api_hash) as client:
        for channel in args.channel:
            print(f"→ Telegram: {channel}", file=sys.stderr)
            try:
                entity = client.get_entity(channel)
            except Exception as exc:
                print(f"  ! {channel}: {exc}", file=sys.stderr)
                continue
            for post in client.iter_messages(entity, limit=args.posts):
                if not (post.replies and post.replies.replies):
                    continue
                try:
                    for c in client.iter_messages(entity, reply_to=post.id,
                                                  limit=args.comments_per_post or None):
                        if not c.message:
                            continue
                        sender = getattr(c.sender, "username", None) or str(c.sender_id or "")
                        yield {
                            "id": f"{channel}/{post.id}/{c.id}", "source": "telegram",
                            "source_id": f"{channel}/{post.id}",
                            "source_title": (post.message or "")[:80].replace("\n", " "),
                            "author": sender, "date": c.date.isoformat() if c.date else "",
                            "likes": "", "text": c.message,
                        }
                except Exception as exc:  # izohlar yopiq bo'lishi mumkin
                    print(f"  ! {channel}/{post.id}: {exc}", file=sys.stderr)
                time.sleep(args.delay)


def file_comments(args) -> Iterator[dict]:
    path = Path(args.input)
    suffix = path.suffix.lower()
    with path.open(encoding="utf-8-sig", newline="") as fh:
        if suffix in (".csv", ".tsv"):
            reader = csv.DictReader(fh, delimiter="\t" if suffix == ".tsv" else ",")
            if args.text_column not in (reader.fieldnames or []):
                sys.exit(f"'{args.text_column}' ustuni topilmadi. Mavjud: {reader.fieldnames}")
            for i, row in enumerate(reader, 1):
                yield {
                    "id": row.get(args.id_column) or str(i),
                    "source": row.get("source") or args.source_name,
                    "source_id": path.name, "source_title": row.get("dataset", ""),
                    "sentiment": row.get("sentiment", ""),
                    "author": row.get("author", ""), "date": row.get("date", ""),
                    "likes": row.get("likes", ""), "text": row.get(args.text_column, ""),
                }
        elif suffix in (".jsonl", ".ndjson"):
            for i, line in enumerate(fh, 1):
                if line.strip():
                    row = json.loads(line)
                    yield {
                        "id": str(row.get(args.id_column) or i), "source": args.source_name,
                        "source_id": path.name, "source_title": "",
                        "author": row.get("author", ""), "date": row.get("date", ""),
                        "likes": row.get("likes", ""), "text": row.get(args.text_column, ""),
                    }
        else:  # TXT: har qator - bitta izoh
            for i, line in enumerate(fh, 1):
                if line.strip():
                    yield {"id": str(i), "source": args.source_name, "source_id": path.name,
                           "source_title": "", "author": "", "date": "", "likes": "",
                           "text": line.strip()}


# --------------------------------------------------------------------------
# Asosiy jarayon
# --------------------------------------------------------------------------

def anonymize(author: str, keep: bool) -> str:
    if keep or not author:
        return author
    return "u_" + hashlib.sha1(author.encode("utf-8")).hexdigest()[:10]


def run(comments: Iterable[dict], matcher: LexiconMatcher, args) -> None:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    seen_ids: set[str] = set()
    seen_texts: set[str] = set()
    if args.append and out.exists():
        with out.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                seen_ids.add(row["izoh_id"])
                seen_texts.add(row["izoh_matni"].strip().lower())
    mode = "a" if args.append and out.exists() else "w"
    all_fh = None
    if args.save_all:
        all_fh = open(args.save_all, mode, encoding="utf-8")

    total = matched = rows = 0
    by_lexicon: Counter = Counter()
    by_item: Counter = Counter()
    with out.open(mode, encoding="utf-8-sig" if mode == "w" else "utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if mode == "w":
            writer.writeheader()
        for c in comments:
            text = (c.get("text") or "").strip()
            if not text or len(text) < args.min_length:
                continue
            key = text.lower()
            if c["id"] in seen_ids or key in seen_texts:
                continue
            seen_ids.add(c["id"])
            seen_texts.add(key)
            total += 1
            if all_fh:
                all_fh.write(json.dumps({**c, "author": anonymize(c.get("author", ""), args.keep_author)},
                                        ensure_ascii=False) + "\n")
            matches = matcher.find(text)
            if not matches:
                continue
            matched += 1
            for m in matches:
                rows += 1
                by_lexicon[m.lexicon] += 1
                by_item[(m.lexicon, m.item)] += 1
                writer.writerow({
                    "izoh_id": c["id"], "manba": c["source"], "manba_id": c["source_id"],
                    "manba_nomi": c.get("source_title", ""),
                    "muallif": anonymize(c.get("author", ""), args.keep_author),
                    "sana": c.get("date", ""), "layklar": c.get("likes", ""),
                    "izoh_matni": text, "sentiment": c.get("sentiment", ""), "leksikon": m.lexicon, "birlik": m.item,
                    "topilgan_qism": m.span, "izoh_manosi": m.meaning,
                    "uslub": m.extra.get("uslub", ""),
                    "manba_sahifa": m.extra.get("manba_sahifa", ""),
                    "tekshiruv_belgisi": "",  # annotator to'ldiradi: ha / yo'q
                })
            fh.flush()
            if args.limit and matched >= args.limit:
                print(f"--limit {args.limit} ga yetildi.", file=sys.stderr)
                break
    if all_fh:
        all_fh.close()

    print("\n=== Natija ===", file=sys.stderr)
    print(f"Ko'rib chiqilgan izohlar: {total}", file=sys.stderr)
    print(f"Moslik topilgan izohlar:  {matched}", file=sys.stderr)
    print(f"Jami mosliklar (qatorlar): {rows}  {dict(by_lexicon)}", file=sys.stderr)
    if by_item:
        print("Eng ko'p uchragan birliklar:", file=sys.stderr)
        for (lex, item), n in by_item.most_common(15):
            print(f"  {n:5d}  [{lex}] {item}", file=sys.stderr)
    print(f"Saqlandi: {out}", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out", default="data/comments/izohlar_mosliklar.csv",
                        help="natija CSV fayli (default: %(default)s)")
    common.add_argument("--lexicon", choices=["both", "frazeologik", "kochma"], default="both",
                        help="qaysi leksikon ishlatilsin (default: both)")
    common.add_argument("--include-aux", action="store_true",
                        help="turmoq, qolmoq, bermoq kabi yordamchi fe'llarni ham ko'chma so'z sifatida izlash")
    common.add_argument("--gap", type=int, default=0,
                        help="ibora so'zlari orasida nechta boshqa so'z kelishi mumkin (default: 0)")
    common.add_argument("--min-length", type=int, default=10, help="eng qisqa izoh uzunligi (belgi)")
    common.add_argument("--limit", type=int, default=0, help="shuncha mos izoh topilgach to'xtash")
    common.add_argument("--append", action="store_true", help="mavjud natija fayliga qo'shish (takrorlarsiz)")
    common.add_argument("--save-all", metavar="FILE.jsonl",
                        help="mos kelmaganlarini ham JSONL ga saqlash (keyinroq qayta tahlil uchun)")
    common.add_argument("--keep-author", action="store_true",
                        help="muallif ismini saqlash (default: anonim xesh)")
    common.add_argument("--delay", type=float, default=1.0, help="so'rovlar orasidagi pauza, soniya")
    sub = p.add_subparsers(dest="cmd", required=True)

    yt = sub.add_parser("youtube", parents=[common], help="YouTube izohlari")
    yt.add_argument("--url", action="append", help="video havolasi (bir necha marta berish mumkin)")
    yt.add_argument("--search", action="append", help="qidiruv so'rovi (yt-dlp kerak)")
    yt.add_argument("--channel", action="append", help="kanal: @nom yoki havola (yt-dlp kerak)")
    yt.add_argument("--videos-per-query", type=int, default=10)
    yt.add_argument("--comments-per-video", type=int, default=2000, help="0 = cheklovsiz")
    yt.add_argument("--sort", choices=["recent", "popular"], default="popular")

    tg = sub.add_parser("telegram", parents=[common], help="Telegram kanal izohlari")
    tg.add_argument("--channel", action="append", required=True, help="kanal username (masalan kunuzofficial)")
    tg.add_argument("--posts", type=int, default=200, help="har kanaldan nechta oxirgi post")
    tg.add_argument("--comments-per-post", type=int, default=0, help="0 = cheklovsiz")
    tg.add_argument("--api-id")
    tg.add_argument("--api-hash")
    tg.add_argument("--session", default="izoh_yiguvchi", help="Telethon sessiya fayli nomi")

    fl = sub.add_parser("file", parents=[common], help="tayyor fayldagi izohlar (CSV/JSONL/TXT)")
    fl.add_argument("--input", required=True)
    fl.add_argument("--text-column", default="text")
    fl.add_argument("--id-column", default="id")
    fl.add_argument("--source-name", default="file")

    args = p.parse_args()
    if args.cmd == "youtube" and not (args.url or args.search or args.channel):
        p.error("youtube: --url, --search yoki --channel dan kamida bittasi kerak")

    print("Leksikonlar yuklanmoqda...", file=sys.stderr)
    matcher = LexiconMatcher(use_frazeologik=args.lexicon in ("both", "frazeologik"),
                             use_kochma=args.lexicon in ("both", "kochma"),
                             include_aux=args.include_aux, gap=args.gap)
    print(f"  {len(matcher.entries)} ta izlash namunasi tayyor.", file=sys.stderr)

    source = {"youtube": youtube_comments, "telegram": telegram_comments, "file": file_comments}[args.cmd]
    try:
        run(source(args), matcher, args)
    except KeyboardInterrupt:
        print("\nTo'xtatildi. Shu paytgacha topilganlar saqlangan.", file=sys.stderr)


if __name__ == "__main__":
    main()
