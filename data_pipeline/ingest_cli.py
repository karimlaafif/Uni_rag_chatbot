"""
data_pipeline/ingest_cli.py — Command-Line Interface for Document Ingestion
============================================================================
Run this script to ingest documents into the Qdrant vector store.

Usage:
    # Ingest all documents in a folder
    python -m data_pipeline.ingest_cli --source data/documents/ --department academic --access-level student

    # Ingest a single file
    python -m data_pipeline.ingest_cli --source data/documents/guide_etudiant.txt --department academic

    # Ingest a URL
    python -m data_pipeline.ingest_cli --url https://www.uiz.ac.ma/guide --department academic

    # Delta mode (only new/changed files)
    python -m data_pipeline.ingest_cli --source data/documents/ --mode delta
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path so imports work from CLI
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest_cli")

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".html", ".jpg", ".jpeg", ".png", ".webp"}


def build_metadata(
    source: str,
    department: str,
    access_level: str,
    doc_version: str = "1.0",
) -> dict:
    return {
        "source":       source,
        "department":   department,
        "access_level": access_level,
        "doc_version":  doc_version,
        "url":          "",
    }


def ingest_directory(
    source_dir: str,
    department: str,
    access_level: str,
    force_reindex: bool,
    qdrant_manager,
    pipeline,
) -> int:
    """Ingest all supported files in a directory. Returns number of chunks indexed."""
    source_path = Path(source_dir)
    if not source_path.exists():
        logger.error(f"Directory not found: {source_dir}")
        return 0

    files = [f for f in source_path.rglob("*") if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    logger.info(f"Found {len(files)} supported file(s) in {source_dir}")

    total_chunks = 0
    for file_path in files:
        logger.info(f"Processing: {file_path.name}")
        metadata = build_metadata(
            source=file_path.name,
            department=department,
            access_level=access_level,
        )

        try:
            docs = pipeline.ingest_file(str(file_path), metadata, force_reindex)
            if not docs:
                logger.info(f"  → Skipped (already indexed or empty)")
                continue

            qdrant_manager.upsert_docs(docs)
            total_chunks += len(docs)
            logger.info(f"  → {len(docs)} chunks indexed ✓")
        except Exception as e:
            logger.error(f"  → Error processing {file_path.name}: {e}")

    return total_chunks


async def ingest_url_async(
    url: str,
    department: str,
    access_level: str,
    qdrant_manager,
    pipeline,
    force_reindex: bool = False,
) -> int:
    metadata = {
        "source":       url,
        "url":          url,
        "department":   department,
        "access_level": access_level,
        "doc_version":  "1.0",
    }
    docs = await pipeline.ingest_url(url, metadata, force_reindex)
    if not docs:
        logger.info(f"URL skipped (already indexed or no content): {url}")
        return 0
    qdrant_manager.upsert_docs(docs)
    logger.info(f"{len(docs)} chunks indexed from URL ✓")
    return len(docs)


def main():
    parser = argparse.ArgumentParser(description="RAG-UNIV Document Ingestion CLI")
    parser.add_argument("--source",       type=str, help="Path to file or directory")
    parser.add_argument("--url",          type=str, help="URL to crawl and ingest")
    parser.add_argument("--department",   type=str, default="general",
                        choices=["academic", "admin", "registrar", "library", "general"],
                        help="Department/category of the document")
    parser.add_argument("--access-level", type=str, default="student",
                        choices=["public", "student", "staff", "admin"],
                        help="Minimum access level to view this document")
    parser.add_argument("--mode",         type=str, default="delta",
                        choices=["delta", "full"],
                        help="delta=only new/changed files; full=re-ingest everything")
    parser.add_argument("--doc-version",  type=str, default="1.0")
    args = parser.parse_args()

    if not args.source and not args.url:
        parser.error("Provide --source (file/directory) or --url")

    logger.info("Initializing QdrantManager and DataIngestionPipeline...")
    try:
        from data_pipeline.vectorstore import QdrantManager
        from data_pipeline.ingestion import DataIngestionPipeline
        qdrant_manager = QdrantManager()
        pipeline       = DataIngestionPipeline(qdrant_manager=qdrant_manager)
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        logger.error("Make sure Qdrant is running (docker compose up qdrant)")
        sys.exit(1)

    force_reindex = args.mode == "full"
    if force_reindex:
        logger.warning(
            "Mode FULL activé — tous les documents seront ré-indexés, "
            "même ceux déjà présents dans Qdrant."
        )

    total = 0

    if args.source:
        p = Path(args.source)
        if p.is_dir():
            total = ingest_directory(
                str(p), args.department, args.access_level, force_reindex,
                qdrant_manager, pipeline,
            )
        elif p.is_file():
            metadata = build_metadata(
                source=p.name,
                department=args.department,
                access_level=args.access_level,
                doc_version=args.doc_version,
            )
            docs = pipeline.ingest_file(str(p), metadata, force_reindex)
            if docs:
                qdrant_manager.upsert_docs(docs)
                total = len(docs)
                logger.info(f"{total} chunks indexed ✓")
            else:
                logger.info("File skipped (already indexed or empty)")
        else:
            logger.error(f"Path not found: {args.source}")
            sys.exit(1)

    if args.url:
        total += asyncio.run(
            ingest_url_async(
                args.url, args.department, args.access_level,
                qdrant_manager, pipeline, force_reindex,
            )
        )

    logger.info(f"\n{'='*50}")
    logger.info(f"✅ Ingestion complete — {total} total chunks indexed")
    logger.info(f"{'='*50}")


if __name__ == "__main__":
    main()
