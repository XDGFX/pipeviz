"""pipeviz CLI — interface identical to WireViz."""

import sys
from pathlib import Path

import click

from pipeviz import __version__
from pipeviz.pipeviz import parse


@click.command()
@click.version_option(__version__, "-V", "--version")
@click.option(
    "-f",
    "--format",
    "formats",
    default=["svg"],
    multiple=True,
    type=click.Choice(["svg", "png", "html", "gv"], case_sensitive=False),
    help="Output format(s). May be specified multiple times. Default: svg",
)
@click.option(
    "-p",
    "--prepend",
    "prepend_paths",
    multiple=True,
    type=click.Path(exists=True),
    help="YAML file to prepend (shared definitions). May be repeated.",
)
@click.option(
    "-o",
    "--output-dir",
    default=None,
    type=click.Path(file_okay=False),
    help="Output directory. Defaults to the same directory as each input file.",
)
@click.option(
    "-O",
    "--output-name",
    default=None,
    help="Output filename base (no extension). Only valid with a single input file.",
)
@click.argument("files", nargs=-1, required=True, type=click.Path(exists=True))
def pipeviz(formats, prepend_paths, output_dir, output_name, files):
    """Generate plumbing system diagrams from YAML source files."""
    if output_name and len(files) > 1:
        raise click.UsageError("--output-name can only be used with a single input file.")

    failed = []
    for file_path in files:
        for fmt in formats:
            try:
                parse(
                    file_path=file_path,
                    prepend_paths=list(prepend_paths),
                    format_type=fmt,
                    output_dir=output_dir,
                    output_name=output_name,
                )
            except Exception as exc:
                click.echo(f"Error processing {file_path} ({fmt}): {exc}", err=True)
                failed.append(file_path)

    if failed:
        sys.exit(1)
