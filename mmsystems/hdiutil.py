import contextlib
import subprocess
import plistlib


def info():
    plist = subprocess.check_output(['hdiutil', 'info', '-plist'])
    return plistlib.readPlistFromString(plist)

def get_mounted():
    mounted = {}
    for image in info()['images']:
        mount_point = next((m for m in (e.get('mount-point') for e in image['system-entities']) if m), None)
        if mount_point:
            mounted[image['image-path']] = mount_point
    return mounted

def attach(image_path, random=False, browse=None):

    cmd = ['hdiutil', 'attach']

    if browse is not None:
        cmd.append('-browse' if browse else '-nobrowse')
    if random:
        cmd.extend(('-mountrandom', random if isinstance(random, basestring) else '/tmp'))

    cmd.append(image_path)
    out = subprocess.check_output(cmd)
    for line in out.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) == 3:
            return parts[2]

def assert_attached(image_path, **kwargs):

    mount_point = get_mounted().get(image_path)
    if mount_point:
        return mount_point, False

    return attach(image_path, **kwargs), True

def detach(something):
    subprocess.check_output(['hdiutil', 'detach', something])


@contextlib.contextmanager
def attached_context(image_path, **kwargs):
    mount, did_attach = assert_attached(image_path, **kwargs)
    try:
        yield mount
    finally:
        if did_attach:
            detach(mount)


if __name__ == '__main__':
    img = '/Volumes/CGroot/systems/software/Autodesk/Maya/2018/macos/Autodesk_Maya_2018_1_Update_EN_JP_ZH_Mac_OSX.dmg'
    with attached_context(img, random=True) as mount:
        print 'mounted at', mount
