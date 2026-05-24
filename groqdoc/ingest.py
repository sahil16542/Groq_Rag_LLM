"""Ingestion pipeline: chunk documents and store embeddings in ChromaDB."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from rich.console import Console
from rich.progress import track

from groqdoc.utils import chunk_file, Chunk

console = Console()

DB_PATH = Path(__file__).parent.parent / "data"
CHROMA_COLLECTION = "groqdoc"
SQLITE_DB = DB_PATH / "metadata.db"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".markdown"}


def _get_chroma_client() -> chromadb.ClientAPI:
    DB_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(DB_PATH / "chroma"))


def _get_collection(client: chromadb.ClientAPI, reset: bool = False) -> chromadb.Collection:
    if reset:
        try:
            client.delete_collection(CHROMA_COLLECTION)
        except Exception:
            pass
    return client.get_or_create_collection(
        CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def _init_sqlite(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            source_file TEXT,
            page_num INTEGER,
            chunk_index INTEGER,
            char_start INTEGER
        )
        """
    )
    conn.commit()


def _sqlite_conn(reset: bool = False) -> sqlite3.Connection:
    DB_PATH.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_DB))
    if reset:
        conn.execute("DROP TABLE IF EXISTS chunks")
    _init_sqlite(conn)
    return conn


def _chunk_id(source_file: str, chunk_index: int) -> str:
    return f"{source_file}::chunk_{chunk_index}"


def ingest_folder(folder: Path, reset: bool = False) -> None:
    """Embed and store all supported documents in folder."""
    files = [
        f for f in folder.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not files:
        console.print(f"[yellow]No supported documents found in {folder}[/yellow]")
        return

    console.print(f"[bold]Loading embedding model...[/bold]")
    model = SentenceTransformer(EMBED_MODEL)

    chroma = _get_chroma_client()
    collection = _get_collection(chroma, reset=reset)
    db = _sqlite_conn(reset=reset)

    total_chunks = 0

    for file_path in track(files, description="Ingesting documents..."):
        try:
            chunks = list(chunk_file(file_path))
        except ValueError as e:
            console.print(f"[yellow]Skipping {file_path.name}: {e}[/yellow]")
            continue
        except Exception as e:
            console.print(f"[red]Error reading {file_path.name}: {e}[/red]")
            continue

        if not chunks:
            continue

        texts = [c.text for c in chunks]
        embeddings = model.encode(texts, show_progress_bar=False).tolist()
        ids = [_chunk_id(c.source_file, c.chunk_index) for c in chunks]
        metadatas = [
            {
                "source_file": c.source_file,
                "page_num": c.page_num,
                "chunk_index": c.chunk_index,
                "char_start": c.char_start,
            }
            for c in chunks
        ]

        collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

        db.executemany(
            "INSERT OR REPLACE INTO chunks VALUES (?, ?, ?, ?, ?)",
            [
                (ids[i], c.source_file, c.page_num, c.chunk_index, c.char_start)
                for i, c in enumerate(chunks)
            ],
        )
        db.commit()
        total_chunks += len(chunks)
        console.print(f"  [green]✓[/green] {file_path.name} — {len(chunks)} chunks")

    db.close()
    console.print(f"\n[bold green]Done.[/bold green] {total_chunks} chunks from {len(files)} file(s) stored.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into GroqDoc.")
    parser.add_argument("folder", type=Path, help="Folder containing documents to ingest.")
    parser.add_argument("--reset", action="store_true", help="Clear existing data before ingesting.")
    args = parser.parse_args()

    if not args.folder.is_dir():
        console.print(f"[red]Error: {args.folder} is not a directory.[/red]")
        raise SystemExit(1)

    ingest_folder(args.folder, reset=args.reset)


if __name__ == "__main__":
    main()
