"""CLI entrypoint: ask a question over ingested documents."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from groq import Groq
from rich.console import Console
from rich.markdown import Markdown

from groqdoc.ingest import ingest_folder, CHROMA_COLLECTION, DB_PATH
from groqdoc.retriever import retrieve, load_models
from groqdoc.prompt import build_system_prompt, has_citations, format_raw_chunks

load_dotenv()

console = Console()

GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024
DOCS_FOLDER = Path(__file__).parent.parent / "docs"


def _ensure_collection_exists() -> None:
    """Auto-ingest docs/ if the ChromaDB collection is missing."""
    try:
        client = chromadb.PersistentClient(path=str(DB_PATH / "chroma"))
        client.get_collection(CHROMA_COLLECTION)
    except Exception:
        console.print(
            "[yellow]No ingested documents found. Running ingest on ./docs ...[/yellow]"
        )
        if not DOCS_FOLDER.is_dir():
            console.print(
                "[red]Error: ./docs folder not found. "
                "Add documents there and run: python -m groqdoc.ingest ./docs[/red]"
            )
            sys.exit(1)
        ingest_folder(DOCS_FOLDER)


def answer_question(question: str) -> None:
    """Retrieve relevant chunks and call the Groq LLM to answer."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        console.print(
            "[red]Error: GROQ_API_KEY is not set. "
            "Copy .env.example to .env and add your key.[/red]"
        )
        sys.exit(1)

    _ensure_collection_exists()

    console.print("[bold]Loading models...[/bold]")
    embed_model, rerank_model = load_models()

    console.print("[bold]Retrieving relevant chunks...[/bold]")
    chunks = retrieve(question, embed_model, rerank_model)

    if not chunks:
        console.print("\n[yellow]No relevant documents found.[/yellow]")
        return

    system_prompt = build_system_prompt(chunks)

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )

    answer = response.choices[0].message.content or ""

    console.print("\n[bold green]Answer:[/bold green]")
    console.print(Markdown(answer))

    if not has_citations(answer):
        console.print(
            "\n[yellow]⚠ Answer may not be grounded in your documents. "
            "Here are the closest chunks found:[/yellow]"
        )
        console.print(format_raw_chunks(chunks))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a question over your documents.")
    parser.add_argument("question", type=str, help="The question to answer.")
    args = parser.parse_args()
    answer_question(args.question)


if __name__ == "__main__":
    main()
