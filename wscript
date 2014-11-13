APPNAME = 'wheel'
WHEEL_TAG = 'py2.py3-none-any'
VERSION = '0.24.0'

top = '.'
out = 'build'

from waflib import Utils

def options(opt):
    opt.load('python')

def configure(ctx):
    ctx.load('python')
    ctx.check_python_version()

def build(bld):
    bld(features='py',
        source=bld.path.ant_glob('wheel/**/*.py', excl="wheel/test"),
        install_from='.')

    # build the wheel:

    DIST_INFO = '%s-%s.dist-info' % (APPNAME, VERSION)

    node = bld.path.get_bld().make_node(DIST_INFO)
    if not os.path.exists(node.abspath()):
        os.mkdir(node.abspath())

    metadata = node.make_node('METADATA')

    import codecs, string
    README = codecs.open('README.txt', encoding='utf8').read()
    CHANGES = codecs.open('CHANGES.txt', encoding='utf8').read()
    METADATA = codecs.open('METADATA.in', encoding='utf8').read()
    METADATA = string.Template(METADATA).substitute(
            VERSION=VERSION,
            DESCRIPTION='\n\n'.join((README, CHANGES))
            )

    bld(source='METADATA.in',
        target=metadata,
        rule=lambda tsk: Utils.writef(tsk.outputs[0].abspath(), METADATA))

    wheel = node.make_node('WHEEL')

    WHEEL="""Wheel-Version: 1.0
Generator: waf (0.0.1)
Root-Is-Purelib: true
Tag: py2-none-any
Tag: py3-none-any
"""
    bld(target=wheel,
       rule=lambda tsk: Utils.writef(tsk.outputs[0].abspath(), WHEEL))

    # globs don't work, since here the files may not exist:
    bld.install_files('${PYTHONDIR}/'+DIST_INFO, [DIST_INFO+'/WHEEL', DIST_INFO+'/METADATA'])

    # only if entry_points.txt exists:
    bld.install_files('${PYTHONDIR}/'+DIST_INFO, ['entry_points.txt'])

import shutil, os, base64

def urlsafe_b64encode(data):
    """urlsafe_b64encode without padding"""
    return base64.urlsafe_b64encode(data).rstrip(b'=')

from waflib import Scripting
class WheelDist(Scripting.Dist):
    def manifest(self):
        """
        Add the wheel manifest.
        """
        import hashlib
        files = self.get_files()
        lines = []
        for f in files:
            print("File: %s" % f.relpath())
            size = os.stat(f.abspath()).st_size
            digest = hashlib.sha256(open(f.abspath(), 'rb').read()).digest()
            digest = "sha256="+(urlsafe_b64encode(digest).decode('ascii'))
            lines.append("%s,%s,%s" % (f.path_from(self.base_path).replace(',', ',,'), digest, size))

        record_path = '%s-%s.dist-info/RECORD' % (APPNAME, VERSION)
        lines.append(record_path+',,')
        RECORD = '\n'.join(lines)

        import zipfile
        zip = zipfile.ZipFile(self.get_arch_name(), 'a')
        zip.writestr(record_path, RECORD, zipfile.ZIP_DEFLATED)
        zip.close()

from waflib import Build
class package_cls(Build.InstallContext):
    cmd = 'package'
    fun = 'build'

    def init_dirs(self, *k, **kw):
        super(package_cls, self).init_dirs(*k, **kw)
        self.tmp = self.bldnode.make_node('package_tmp_dir')
        try:
            shutil.rmtree(self.tmp.abspath())
        except:
            pass
        if os.path.exists(self.tmp.abspath()):
            self.fatal('Could not remove the temporary directory %r' % self.tmp)
        self.tmp.mkdir()
        self.options.destdir = self.tmp.abspath()

    def execute(self, *k, **kw):
        back = self.options.destdir
        try:
            super(package_cls, self).execute(*k, **kw)
        finally:
            self.options.destdir = back

        files = self.tmp.ant_glob('**', excl=" **/*.pyc **/*.pyo")

        # we could mess with multiple inheritance but this is probably unnecessary
        ctx = WheelDist()
        ctx.algo = 'zip'
        ctx.arch_name = '%s-%s-%s.whl' % (APPNAME, VERSION, WHEEL_TAG)
        ctx.files = files
        ctx.tar_prefix = ''
        ctx.base_path = self.tmp
        ctx.base_name = ''
        ctx.archive()

        # add manifest...
        ctx.manifest()

        shutil.rmtree(self.tmp.abspath())

