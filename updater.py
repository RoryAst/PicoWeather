import urequests
import uos
import machine
import secrets

# Files managed by OTA — secrets.py is intentionally excluded
MANAGED = ['main.py', 'updater.py', 'version.py']

BASE_URL = 'https://raw.githubusercontent.com/{}/{}/{}/'.format(
    secrets.GITHUB_USER, secrets.GITHUB_REPO, secrets.GITHUB_BRANCH
)


def _fetch(path):
    r = urequests.get(BASE_URL + path, timeout=15)
    text = r.text
    r.close()
    return text


def _parse_ver(v):
    return tuple(int(x) for x in v.strip().split('.'))


def _local_version():
    try:
        from version import VERSION
        return VERSION
    except ImportError:
        return '0.0.0'


def _cleanup():
    for fname in MANAGED:
        try:
            uos.remove(fname + '.new')
        except OSError:
            pass


def check():
    try:
        ver_src = _fetch('version.py')
        remote_ver = None
        for line in ver_src.split('\n'):
            if line.startswith('VERSION'):
                remote_ver = line.split("'")[1]
                break

        if remote_ver is None:
            print('OTA: could not parse remote version')
            return

        local_ver = _local_version()
        print('OTA: local={} remote={}'.format(local_ver, remote_ver))

        if _parse_ver(remote_ver) <= _parse_ver(local_ver):
            print('OTA: up to date')
            return

        print('OTA: downloading {}...'.format(remote_ver))
        _cleanup()

        for fname in MANAGED:
            print('OTA: fetching', fname)
            content = _fetch(fname)
            with open(fname + '.new', 'w') as f:
                f.write(content)

        # Point of no return — swap files in
        for fname in MANAGED:
            try:
                uos.remove(fname)
            except OSError:
                pass
            uos.rename(fname + '.new', fname)

        print('OTA: updated to {}, restarting'.format(remote_ver))
        machine.reset()

    except Exception as e:
        print('OTA: failed:', e)
        _cleanup()
