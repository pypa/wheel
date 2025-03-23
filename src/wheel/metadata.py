from warnings import warn

warn(
    f"The {__name__:r} package has been made private and should no longer be imported. "
    f"Please either copy the code or find an alternative library to import it from, as "
    f"this warning will be removed in a future version of 'wheel'.",
    DeprecationWarning,
    stacklevel=1,
)
