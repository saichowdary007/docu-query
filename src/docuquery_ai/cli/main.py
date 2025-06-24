"""
Command-line interface for DocuQuery AI.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import click

from docuquery_ai import DocumentQueryClient, __version__


@click.group()
@click.version_option(version=__version__, prog_name="docuquery")
@click.option(
    "--google-api-key",
    envvar="GOOGLE_API_KEY",
    help="Google API key for Vertex AI (can also be set via GOOGLE_API_KEY env var)",
)
@click.option(
    "--google-project-id",
    envvar="GOOGLE_PROJECT_ID",
    help="Google Cloud project ID (can also be set via GOOGLE_PROJECT_ID env var)",
)
@click.option(
    "--vector-store-path",
    default="./vector_db_data",
    help="Path to store vector database",
)
@click.pass_context
def cli(ctx, google_api_key, google_project_id, vector_store_path):
    """DocuQuery AI - Document querying with RAG and LLM."""
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store configuration in context
    ctx.obj["google_api_key"] = google_api_key
    ctx.obj["google_project_id"] = google_project_id
    ctx.obj["vector_store_path"] = vector_store_path


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--user-id", default="cli_user", help="User identifier")
@click.option(
    "--output",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.pass_context
def upload(ctx, file_path, user_id, output):
    """Upload and process a document."""
    try:
        client = DocumentQueryClient(
            google_api_key=ctx.obj["google_api_key"],
            google_project_id=ctx.obj["google_project_id"],
            vector_store_path=ctx.obj["vector_store_path"],
        )

        result = client.upload_document(file_path, user_id)

        if output == "json":
            click.echo(json.dumps(result, indent=2))
        else:
            if result["success"]:
                click.echo(f"✅ Successfully uploaded: {result['filename']}")
                click.echo(f"   File ID: {result['file_id']}")
                click.echo(f"   Type: {result['file_type']}")
                click.echo(f"   Structured: {result['is_structured']}")
                if "chunks_count" in result:
                    click.echo(f"   Chunks: {result['chunks_count']}")
            else:
                click.echo(f"❌ Upload failed: {result['error']}", err=True)
                sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("question")
@click.option("--user-id", default="cli_user", help="User identifier")
@click.option("--file-ids", help="Comma-separated list of file IDs to query")
@click.option(
    "--output",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.pass_context
def query(ctx, question, user_id, file_ids, output):
    """Query uploaded documents."""
    try:
        client = DocumentQueryClient(
            google_api_key=ctx.obj["google_api_key"],
            google_project_id=ctx.obj["google_project_id"],
            vector_store_path=ctx.obj["vector_store_path"],
        )

        file_id_list = file_ids.split(",") if file_ids else None
        result = client.query(question, user_id, file_id_list)

        if output == "json":
            # Convert QueryResponse to dict for JSON serialization
            result_dict = {
                "answer": result.answer,
                "sources": result.sources,
                "type": result.type,
                "download_url": result.download_url,
                "metadata": result.metadata,
            }
            click.echo(json.dumps(result_dict, indent=2))
        else:
            click.echo(f"🤖 Answer: {result.answer}")
            if result.sources:
                click.echo(f"📄 Sources: {', '.join(result.sources)}")
            if result.download_url:
                click.echo(f"💾 Download: {result.download_url}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--user-id", default="cli_user", help="User identifier")
@click.option(
    "--output",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.pass_context
def list(ctx, user_id, output):
    """List uploaded documents."""
    try:
        client = DocumentQueryClient(
            google_api_key=ctx.obj["google_api_key"],
            google_project_id=ctx.obj["google_project_id"],
            vector_store_path=ctx.obj["vector_store_path"],
        )

        documents = client.list_documents(user_id)

        if output == "json":
            click.echo(json.dumps(documents, indent=2))
        else:
            if not documents:
                click.echo("No documents found.")
            else:
                click.echo(f"📄 Found {len(documents)} document(s):")
                for doc in documents:
                    click.echo(
                        f"   • {doc['filename']} ({doc['file_type']}) - ID: {doc['file_id']}"
                    )
                    if doc["created_at"]:
                        click.echo(f"     Created: {doc['created_at']}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("file_id")
@click.option("--user-id", default="cli_user", help="User identifier")
@click.pass_context
def delete(ctx, file_id, user_id):
    """Delete a document."""
    try:
        client = DocumentQueryClient(
            google_api_key=ctx.obj["google_api_key"],
            google_project_id=ctx.obj["google_project_id"],
            vector_store_path=ctx.obj["vector_store_path"],
        )

        success = client.delete_document(file_id, user_id)

        if success:
            click.echo(f"✅ Successfully deleted document: {file_id}")
        else:
            click.echo(f"❌ Document not found: {file_id}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize DocuQuery AI configuration."""
    click.echo("🚀 Initializing DocuQuery AI...")

    # Check for Google credentials
    google_api_key = ctx.obj["google_api_key"] or os.getenv("GOOGLE_API_KEY")
    google_project_id = ctx.obj["google_project_id"] or os.getenv("GOOGLE_PROJECT_ID")

    if not google_api_key:
        click.echo(
            "⚠️  GOOGLE_API_KEY not found. Please set it as an environment variable."
        )
        click.echo("   export GOOGLE_API_KEY='your-api-key'")

    if not google_project_id:
        click.echo(
            "⚠️  GOOGLE_PROJECT_ID not found. Please set it as an environment variable."
        )
        click.echo("   export GOOGLE_PROJECT_ID='your-project-id'")

    if google_api_key and google_project_id:
        try:
            client = DocumentQueryClient(
                google_api_key=google_api_key,
                google_project_id=google_project_id,
                vector_store_path=ctx.obj["vector_store_path"],
            )
            click.echo("✅ DocuQuery AI initialized successfully!")
            click.echo(f"   Vector store: {ctx.obj['vector_store_path']}")
        except Exception as e:
            click.echo(f"❌ Initialization failed: {str(e)}", err=True)
            sys.exit(1)


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
