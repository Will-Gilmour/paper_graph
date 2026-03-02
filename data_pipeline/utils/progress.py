"""Progress bar utilities."""

from typing import Iterable, Optional
from tqdm import tqdm


def progress_bar(
    iterable: Optional[Iterable] = None,
    total: Optional[int] = None,
    desc: Optional[str] = None,
    unit: str = "it",
    **kwargs
) -> tqdm:
    """
    Create a progress bar using tqdm.
    
    Args:
        iterable: Iterable to wrap
        total: Total number of iterations
        desc: Description prefix
        unit: Unit name
        **kwargs: Additional arguments for tqdm
    
    Returns:
        tqdm progress bar
    """
    return tqdm(
        iterable=iterable,
        total=total,
        desc=desc,
        unit=unit,
        ncols=80,
        **kwargs
    )

