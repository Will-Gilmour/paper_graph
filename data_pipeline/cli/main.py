"""
Main CLI entry point.

Usage:
    python -m data_pipeline run-all --seeds seeds.json --db-url $DATABASE_URL
"""

import sys
import json
from pathlib import Path
import click

from data_pipeline.config.settings import PipelineConfig
from data_pipeline.workflow.orchestrator import PipelineOrchestrator
from data_pipeline import __version__


@click.group()
@click.version_option(version=__version__)
def cli():
    """LitSearch Data Pipeline - Modular citation graph builder."""
    pass


@cli.command(name="run-all")
@click.option("--seeds", type=click.Path(exists=True), help="JSON file with seed DOIs")
@click.option("--seed-doi", multiple=True, help="Single seed DOI (can specify multiple)")
@click.option("--output-dir", type=click.Path(), default="./data_pipeline_output", help="Output directory")
@click.option("--db-url", envvar="DATABASE_URL", help="PostgreSQL URL")
@click.option("--gpu/--no-gpu", default=True, help="Use GPU for layout")
@click.option("--max-depth", type=int, default=1, help="Citation crawl depth")
@click.option("--verbose", is_flag=True, help="Verbose logging")
def run_all(seeds, seed_doi, output_dir, db_url, gpu, max_depth, verbose):
    """Run complete pipeline from seeds to PostgreSQL."""
    
    # Load seed DOIs
    seed_dois = []
    if seeds:
        with open(seeds) as f:
            data = json.load(f)
            if isinstance(data, list):
                seed_dois = data
            elif isinstance(data, dict) and "seeds" in data:
                seed_dois = data["seeds"]
    
    if seed_doi:
        seed_dois.extend(seed_doi)
    
    if not seed_dois:
        click.echo("Error: No seed DOIs provided", err=True)
        sys.exit(1)
    
    if not db_url:
        click.echo("Error: Database URL required (use --db-url or set DATABASE_URL env var)", err=True)
        sys.exit(1)
    
    # Create config
    config = PipelineConfig(
        seed_dois=seed_dois,
        output_dir=Path(output_dir),
        max_depth=max_depth,
        verbose=verbose,
    )
    
    config.layout.use_gpu = gpu
    config.export.database_url = db_url
    
    # Run pipeline
    orchestrator = PipelineOrchestrator(config)
    orchestrator.run_full_pipeline(seed_dois)
    
    click.echo("\n✅ Pipeline complete!")


@cli.command()
@click.option("--seeds", type=click.Path(exists=True), required=True, help="JSON file with seed DOIs")
@click.option("--output", type=click.Path(), default="graph.pkl.gz", help="Output pickle file")
@click.option("--max-depth", type=int, default=1, help="Citation crawl depth")
@click.option("--verbose", is_flag=True, help="Verbose logging")
def build(seeds, output, max_depth, verbose):
    """Build citation graph from seeds."""
    
    # Load seeds
    with open(seeds) as f:
        seed_dois = json.load(f)
    
    # Create config
    config = PipelineConfig(
        seed_dois=seed_dois,
        max_depth=max_depth,
        verbose=verbose,
    )
    
    # Build graph
    orchestrator = PipelineOrchestrator(config)
    graph_data = orchestrator.build_graph(seed_dois)
    
    # Save
    from data_pipeline.export.pickle_export import PickleExporter
    PickleExporter.export(graph_data, Path(output))
    
    click.echo(f"✅ Graph saved to {output}")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--gpu/--no-gpu", default=True, help="Use GPU")
@click.option("--verbose", is_flag=True, help="Verbose logging")
def layout(input_file, gpu, verbose):
    """Compute 2D layout for graph."""
    
    from data_pipeline.export.pickle_export import PickleExporter
    
    # Load graph
    graph_data = PickleExporter.load(Path(input_file))
    
    # Create config
    config = PipelineConfig(verbose=verbose)
    config.layout.use_gpu = gpu
    
    # Compute layout
    orchestrator = PipelineOrchestrator(config)
    orchestrator.compute_layout(graph_data)
    
    # Save
    PickleExporter.export(graph_data, Path(input_file))
    
    click.echo("✅ Layout complete")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--verbose", is_flag=True, help="Verbose logging")
def cluster(input_file, verbose):
    """Cluster papers in graph."""
    
    from data_pipeline.export.pickle_export import PickleExporter
    
    # Load graph
    graph_data = PickleExporter.load(Path(input_file))
    
    # Create config
    config = PipelineConfig(verbose=verbose)
    
    # Cluster
    orchestrator = PipelineOrchestrator(config)
    orchestrator.compute_clusters(graph_data)
    
    # Save
    PickleExporter.export(graph_data, Path(input_file))
    
    click.echo(f"✅ Found {graph_data.num_clusters()} clusters")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--batch-size", type=int, default=8, help="LLM batch size")
@click.option("--verbose", is_flag=True, help="Verbose logging")
def label(input_file, batch_size, verbose):
    """Generate cluster labels with LLM."""
    
    from data_pipeline.export.pickle_export import PickleExporter
    
    # Load graph
    graph_data = PickleExporter.load(Path(input_file))
    
    # Create config
    config = PipelineConfig(verbose=verbose)
    config.labeling.batch_size = batch_size
    
    # Label
    orchestrator = PipelineOrchestrator(config)
    orchestrator.label_clusters(graph_data)
    
    # Save
    PickleExporter.export(graph_data, Path(input_file))
    
    click.echo("✅ Labeling complete")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--db-url", envvar="DATABASE_URL", required=True, help="PostgreSQL URL")
@click.option("--verbose", is_flag=True, help="Verbose logging")
def export(input_file, db_url, verbose):
    """Export graph to PostgreSQL."""
    
    from data_pipeline.export.pickle_export import PickleExporter
    
    # Load graph
    graph_data = PickleExporter.load(Path(input_file))
    
    # Create config
    config = PipelineConfig(verbose=verbose)
    config.export.database_url = db_url
    
    # Export
    orchestrator = PipelineOrchestrator(config)
    orchestrator.export_to_postgres(graph_data)
    
    click.echo("✅ Export complete")


if __name__ == "__main__":
    cli()

