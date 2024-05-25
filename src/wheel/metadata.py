from warnings import warn

from ._metadata import convert_requirements as convert_requirements
from ._metadata import generate_requirements as generate_requirements
from ._metadata import pkginfo_to_metadata as pkginfo_to_metadata
from ._metadata import requires_to_requires_dist as requires_to_requires_dist

warn(
    f"The {__package__}.{__name__} module has been deprecated and will be removed in a "
    f"future release of 'wheel'. Please use the appropriate APIs from 'packaging' "
    f"instead.",
    DeprecationWarning,
    stacklevel=1,
)
