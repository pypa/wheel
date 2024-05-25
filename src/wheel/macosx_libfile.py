from warnings import warn

from ._macosx_libfile import (
    calculate_macosx_platform_tag as calculate_macosx_platform_tag,
)

warn(
    f"The {__package__}.{__name__} module has been deprecated and will be removed in a "
    f"future release of 'wheel'. Please use the appropriate APIs from 'packaging' "
    f"instead.",
    DeprecationWarning,
    stacklevel=1,
)
