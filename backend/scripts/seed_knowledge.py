"""
Seed shared RAG knowledge from local Assets + brand websites.

Usage (from backend/ with venv active):

  python -m scripts.seed_knowledge
  python -m scripts.seed_knowledge --user-id <uuid>
  python -m scripts.seed_knowledge --skip-websites
  python -m scripts.seed_knowledge --skip-assets

Requires:
  - migrations 001–003 applied
  - at least one user in public.users (Owner signup), OR --user-id
  - OPENROUTER + Supabase credentials in .env
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai.service import create_ai_service
from app.core.brand import DEFAULT_CRAWL_SEEDS
from app.database.client import get_supabase_admin
from app.rag.ingestion import IngestionService
from app.rag.website import WebsiteCrawler
from app.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)

ASSETS_ROOT = ROOT.parent / "Assets" / "extracted"
BRAND_ROOT = ROOT.parent / "Assets" / "brand"
SUPPORTED = {".txt", ".csv", ".pdf", ".docx", ".xlsx"}


def _iter_asset_files():
    for root in (ASSETS_ROOT, BRAND_ROOT):
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED:
                yield root, path


def resolve_owner_user_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    db = get_supabase_admin()
    result = (
        db.table("users")
        .select("id, role, email")
        .order("created_at")
        .limit(5)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise RuntimeError(
            "No users found. Sign up Owner at http://localhost:3000/signup first, "
            "then re-run this seed script."
        )
    owner = next((r for r in rows if r.get("role") == "owner"), rows[0])
    logger.info("seed_owner", user_id=owner["id"], email=owner.get("email"))
    return owner["id"]


async def ingest_assets(ingestion: IngestionService, user_id: str) -> int:
    files = list(_iter_asset_files())
    if not files:
        logger.warning("assets_missing", extracted=str(ASSETS_ROOT), brand=str(BRAND_ROOT))
        return 0

    db = get_supabase_admin()
    existing = (
        db.table("business_documents")
        .select("original_filename, status")
        .eq("user_id", user_id)
        .eq("source_type", "asset")
        .execute()
    )
    done = {
        row["original_filename"]
        for row in (existing.data or [])
        if row.get("status") == "ready"
    }

    count = 0
    for root, path in files:
        if path.name in done:
            logger.info("skip_existing_asset", file=path.name)
            continue
        logger.info("ingesting_asset", file=path.name)
        try:
            data = path.read_bytes()
            await ingestion.ingest_upload(
                user_id=user_id,
                filename=path.name,
                file_bytes=data,
                source_type="asset",
                is_shared=True,
                source_url=f"asset://{path.relative_to(root).as_posix()}",
            )
            count += 1
        except Exception as exc:
            logger.exception("asset_ingest_error", file=path.name, error=str(exc))
    return count


async def ingest_websites(ingestion: IngestionService, user_id: str) -> int:
    crawler = WebsiteCrawler(max_pages=30)
    pages = await crawler.crawl(DEFAULT_CRAWL_SEEDS)
    db = get_supabase_admin()
    existing = (
        db.table("business_documents")
        .select("source_url, status")
        .eq("source_type", "website")
        .execute()
    )
    done = {
        row["source_url"]
        for row in (existing.data or [])
        if row.get("status") == "ready" and row.get("source_url")
    }

    count = 0
    for page in pages:
        if page["url"] in done:
            logger.info("skip_existing_page", url=page["url"])
            continue
        title = page["title"] or page["url"]
        logger.info("ingesting_page", url=page["url"])
        try:
            await ingestion.ingest_text(
                user_id=user_id,
                title=f"web_{title}",
                text=f"Source URL: {page['url']}\n\n{page['content']}",
                source_type="website",
                source_url=page["url"],
                is_shared=True,
                file_type="web",
            )
            count += 1
        except Exception as exc:
            logger.exception("page_ingest_error", url=page["url"], error=str(exc))
    return count


async def main_async(args: argparse.Namespace) -> None:
    setup_logging()
    user_id = resolve_owner_user_id(args.user_id)
    ai = create_ai_service()
    ingestion = IngestionService(ai_service=ai)

    assets_n = 0
    web_n = 0
    if not args.skip_assets:
        assets_n = await ingest_assets(ingestion, user_id)
    if not args.skip_websites:
        web_n = await ingest_websites(ingestion, user_id)

    logger.info("seed_complete", assets=assets_n, website_pages=web_n, user_id=user_id)
    print(f"Seed complete. Assets={assets_n}, website_pages={web_n}, owner={user_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Jarvis shared knowledge base")
    parser.add_argument("--user-id", help="Owner user UUID (optional)")
    parser.add_argument("--skip-assets", action="store_true")
    parser.add_argument("--skip-websites", action="store_true")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
