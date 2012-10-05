# Test wheel's vendorized pkg_resources

def test_pkg_resources():
    from wheel import pkg_resources
    import wheel.pkg_resources._markerlib 