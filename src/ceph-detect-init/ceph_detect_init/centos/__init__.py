import itertools

distro = None
release = None
codename = None


# handle release strings like "7 (AltArch)"
def _rh_major_version(v):
    return int("".join(itertools.takewhile(str.isdigit, v)))


def choose_init():
    """Select a init system

    Returns the name of a init system (upstart, sysvinit ...).
    """
    if release and _rh_major_version(release) >= 7:
        return 'systemd'
    return 'sysvinit'
