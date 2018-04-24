import argparse
import sys
import os
import subprocess

from mmsystems import hdiutil



def check_call(cmd, **kwargs):
    print '$', ' '.join(cmd)
    return subprocess.check_call(cmd, **kwargs)



def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true')
    parser.add_argument('-I', '--skip-install', action='store_true')
    parser.add_argument('-L', '--skip-license', action='store_true')
    parser.add_argument('-V', '--version', default='2018')
    args = parser.parse_args()

    if os.getuid():
        os.execvp('sudo', ['sudo',
            'bash', '-c', 'source /usr/local/vee/environments/markmedia/master/etc/bashrc; exec "$0" "$@"',
            sys.executable, __file__,
        ] + sys.argv[1:])

    if sys.platform == 'darwin':
        installer = MacOSInstaller()
    else:
        installer = LinuxInstaller()
    installer.run(**args.__dict__)


class BaseInstaller(object):

    def enter_context(self):
        pass

    def exit_context(self):
        pass

    @property
    def is_installed(self):
        raise NotImplementedError('is_installed')

    def install(self):
        raise NotImplementedError('install')

    def setup_license_env(self):

        data = {}
        env_path = os.path.join(self.maya_bin, 'License.env')
        if os.path.exists(env_path):
            for line in open(env_path, 'rb'):
                try:
                    key, value = line.strip().split('=', 1)
                except ValueError:
                    continue
                else:
                    data[key] = value

        data.setdefault('MAYA_LICENSE', 'unlimited')
        data.setdefault('MAYA_LICENSE_METHOD', 'network')

        with open(env_path, 'wb') as fh:
            for k, v in sorted(data.iteritems()):
                fh.write('{}={}\n'.format(k, v))

    def setup_flexnet(self):
        with open('/var/flexlm/Maya{}.lic'.format(self.version), 'wb') as fh:
            fh.write('SERVER autodesk.license.mm 0\n')
            fh.write('USE_SERVER\n')

    adlm_env = None

    def setup_adlmreg(self):
        
        adlmreg = os.path.join(self.adlm_bin, 'adlmreg')
        product_code = '657{}1'.format(chr(int(self.version) - 1944))

        check_call([
            adlmreg,
            '-i', 'N',
            product_code, product_code, '{}.0.0.F'.format(self.version),
            '666-69696969',
            self.pit_path,
        ])

    def assert_farmsoup(self, resource):
        farmsoup_line = '''WORKER_RESOURCES['{}'] = 'Inf' # mminstall-maya'''.format(resource)
        farmsoup_path = '/etc/farmsoup.py'
        farmsoup_done = os.path.exists(farmsoup_path) and farmsoup_line in open(farmsoup_path).read()
        if not farmsoup_done:
            check_call(['sudo', 'bash', '-c', 'echo "{}" >> {}'.format(farmsoup_line, farmsoup_path)])

    def setup_farmsoup(self):
        self.assert_farmsoup('maya')
        self.assert_farmsoup('maya{}'.format(self.version))
        if self.version in ('2018', ):
            self.assert_farmsoup('mtoa2018')

    def run(self, version, force=False, skip_install=False, skip_license=False, **_):
        self.version = version
        try:
            self.enter_context()
            if force or (not skip_install and not self.is_installed):
                self.install()
            if not skip_license:
                self.setup_license_env()
                self.setup_flexnet()
                self.setup_adlmreg()
            self.setup_farmsoup()
        finally:
            self.exit_context()


class MacOSInstaller(BaseInstaller):

    dmg_paths = {
        '2018': '/Volumes/CGroot/systems/software/Autodesk/Maya/2018/macos/Autodesk_Maya_2018_1_Update_EN_JP_ZH_Mac_OSX.dmg',
    }

    @property
    def dmg_path(self):
        return self.dmg_paths[self.version]

    did_mount = False

    def enter_context(self):
        self.mount, self.did_mount = hdiutil.assert_attached(self.dmg_path, random=True, browse=False)

    def exit_context(self):
        if self.did_mount:
            hdiutil.detach(self.mount)

    @property
    def pkg_root(self):
        return os.path.join(self.mount, 'Install Maya {}.app/Contents/Packages'.format(self.version))

    @property
    def is_installed(self):
        return os.path.exists('/Applications/Autodesk/maya2018/Maya.app')

    def install(self):

        for pkg_type in os.listdir(self.pkg_root):
            
            pkg_dir = os.path.join(self.pkg_root, pkg_type)
            if not os.path.isdir(pkg_dir):
                continue

            for pkg_name in os.listdir(pkg_dir):

                if not pkg_name.endswith('.pkg'):
                    continue
                if pkg_name in ('MtoA.pkg', ):
                    continue
                
                print '==>', pkg_name

                pkg_path = os.path.join(pkg_dir, pkg_name)
                check_call(['installer', '-verbose', '-target', '/', '-pkg', pkg_path])

        pkg_path = '/Volumes/CGroot/systems/software/SolidAngle/MtoA-3.0.0.2-darwin-2018.pkg'
        check_call(['installer', '-verbose', '-target', '/', '-pkg', pkg_path])


    @property
    def maya_bin(self):
        return '/Applications/Autodesk/maya{}/Maya.app/Contents/bin'.format(self.version)

    @property
    def adlm_bin(self):
        return os.path.join(self.mount, 'Install Maya {}.app/Contents/Resources'.format(self.version))

    @property
    def pit_path(self):
        return '/Library/Application Support/Autodesk/Adlm/PIT/{}/MayaConfig.pit'.format(self.version)

class LinuxInstaller(BaseInstaller):

    @property
    def pkg_root(self):
        return '/Volumes/CGroot/systems/software/Autodesk/Maya/{}/linux/maya'.format(self.version)

    @property
    def is_installed(self):
        return os.path.exists('/usr/autodesk/maya2018/bin/maya')

    def install(self):

        # Dependencies.
        check_call(['yum', 'install', '-y', 
            'libXp',
            'libpng12',
            'gamin',
            'xorg-x11-fonts-75dpi.noarch',
            'xorg-x11-fonts-100dpi.noarch',
            'xorg-x11-fonts-ISO8859-1-75dpi.noarch',
            'xorg-x11-fonts-ISO8859-1-100dpi.noarch',
        ])

        for pkg_name in os.listdir(self.pkg_root):

            if not pkg_name.endswith('.rpm'):
                continue
            if 'adlmflexnetserver' in pkg_name:
                continue

            check_call(['rpm', '-i', '--force', os.path.join(self.pkg_root, pkg_name)])

        check_call(['/Volumes/CGroot/systems/software/SolidAngle/MtoA-3.0.0.2-linux-{}.run'.format(self.version), 'silent'])

    @property
    def maya_bin(self):
        return '/usr/autodesk/maya{}/bin'.format(self.version)

    @property
    def adlm_bin(self):
        return self.pkg_root

    @property
    def adlm_env(self):
        env = os.environ.copy()
        env['LD_LIBRARY_PATH'] = '/opt/Autodesk/Adlm/R7/lib64'
        return env

    @property
    def pit_path(self):
        return '/var/opt/Autodesk/Adlm/Maya{}/MayaConfig.pit'.format(self.version)


if __name__ == '__main__':
    main()
