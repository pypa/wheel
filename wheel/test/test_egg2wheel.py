import os.path

from wheel import egg2wheel


def test_egg_re():
    """Make sure egg_info_re matches."""
    egg_names_path = os.path.join(os.path.dirname(__file__), 'eggnames.txt')
    with open(egg_names_path) as egg_names:
        for line in egg_names:
            line = line.strip()
            if line:
                assert egg2wheel.egg_info_re.match(line), line
