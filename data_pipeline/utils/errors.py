"""Custom exceptions for the pipeline."""


class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class APIError(PipelineError):
    """Error fetching data from external API."""
    pass


class LayoutError(PipelineError):
    """Error computing graph layout."""
    pass


class ClusteringError(PipelineError):
    """Error during clustering."""
    pass


class EmbeddingError(PipelineError):
    """Error generating embeddings."""
    pass


class LabelingError(PipelineError):
    """Error generating labels with LLM."""
    pass


class ExportError(PipelineError):
    """Error exporting data."""
    pass


class ConfigError(PipelineError):
    """Configuration error."""
    pass

