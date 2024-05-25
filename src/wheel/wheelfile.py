from warnings import warn

from ._wheelfile import WHEEL_INFO_RE as WHEEL_INFO_RE
from ._wheelfile import WheelFile as WheelFile
from ._wheelfile import get_zipinfo_datetime as get_zipinfo_datetime

warn(
    f"The {__package__}.{__name__} module has been deprecated and will be removed in a "
    f"future release of 'wheel'. Please use the appropriate APIs from 'packaging' "
    f"instead.",
    DeprecationWarning,
    stacklevel=1,
)
