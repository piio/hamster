# -*- python -*-
VERSION = '2.0'
APPNAME = 'hamster-time-tracker'
top = '.'
out = 'build'

import os
from waflib import Logs, Utils


def configure(conf):
    conf.load('gnu_dirs')  # for DATADIR
    conf.load('python')
    conf.check_python_version(minver=(3,4,0))

    conf.load('intltool')
    conf.load('dbus')

    conf.define('ENABLE_NLS', 1)
    conf.define('HAVE_BIND_TEXTDOMAIN_CODESET', 1)

    conf.define('VERSION', VERSION)
    conf.define('GETTEXT_PACKAGE', "hamster-time-tracker")
    conf.define('PACKAGE', "hamster-time-tracker")
    conf.define('PYEXECDIR', conf.env["PYTHONDIR"]) # i don't know the difference

    # SYSCONFDIR default should not be /usr/etc, but /etc
    # TODO: should not be necessary any longer, with the --gconf-dir option
    if conf.env.SYSCONFDIR == '/usr/etc':
        conf.env.SYSCONFDIR = '/etc'

    conf.define('prefix', conf.env["PREFIX"]) # to keep compatibility for now

    # gconf_dir is defined in options
    conf.env.schemas_destination = '{}/schemas'.format(conf.options.gconf_dir)

    if conf.options.doc_commands.lower() != "none":
        conf.recurse("help")


def options(opt):
    opt.add_option('--gconf-dir', action='store', default='/etc/gconf', dest='gconf_dir', help='gconf base directory [default: /etc/gconf]')
    opt.add_option('--docs', action='store', default='build install', dest='doc_commands', help='documentation commands [default: "build install", other valid options: "build", "install", "none"]')


def build(bld):
    from waflib import Utils
    
    bld.install_files('${LIBDIR}/hamster-time-tracker',
                      """src/hamster-service
                         src/hamster-windows-service
                      """,
                      chmod=Utils.O755)
    
    bld.install_as('${BINDIR}/hamster', "src/hamster-cli", chmod=Utils.O755)


    bld.install_files('${PREFIX}/share/bash-completion/completion',
                      'src/hamster.bash')


    bld(features='py',
        source=bld.path.ant_glob('src/**/*.py'),
        install_from='src')

    # set correct flags in defs.py
    bld(features="subst",
        source="src/hamster/defs.py.in",
        target="src/hamster/defs.py",
        install_path="${PYTHONDIR}/hamster"
        )

    bld(features="subst",
        source= "org.gnome.hamster.service.in",
        target= "org.gnome.hamster.service",
        install_path="${DATADIR}/dbus-1/services",
        )

    bld(features="subst",
        source= "org.gnome.hamster.Windows.service.in",
        target= "org.gnome.hamster.Windows.service",
        install_path="${DATADIR}/dbus-1/services",
        )
    
    bld.install_files(bld.env.schemas_destination,
                      "data/hamster-time-tracker.schemas")

    #bld.add_subdirs("po help data")
    bld.recurse("po data")


    def manage_gconf_schemas(ctx, action):
        """Install or uninstall hamster gconf schemas.

        Requires the stored hamster-time-tracker.schemas
        (usually in /etc/gconf/schemas/) to be present.

        Hence install should be a post-fun,
        and uninstall a pre-fun.
        """

        assert action in ("install", "uninstall")
        if ctx.cmd == action:
            schemas_file = "{}/hamster-time-tracker.schemas".format(ctx.env.schemas_destination)
            cmd = 'GCONF_CONFIG_SOURCE=$(gconftool-2 --get-default-source) gconftool-2 --makefile-{}-rule {} 1> /dev/null'.format(action, schemas_file)
            err = ctx.exec_command(cmd)
            if err:
                Logs.warn('The following  command failed:\n{}'.format(cmd))
            else:
                Logs.pprint('YELLOW', 'Successfully {}ed gconf schemas'.format(action))


    def update_icon_cache(ctx):
        """Update the gtk icon cache."""
        if ctx.cmd == "install":
            # adapted from the previous waf gnome.py
            icon_dir = os.path.join(ctx.env.DATADIR, 'icons/hicolor')
            cmd = 'gtk-update-icon-cache -q -f -t {}'.format(icon_dir)
            err = ctx.exec_command(cmd)
            if err:
                Logs.warn('The following  command failed:\n{}'.format(cmd))
            else:
                Logs.pprint('YELLOW', 'Successfully updated GTK icon cache')


    bld.add_post_fun(lambda bld: manage_gconf_schemas(bld, "install"))
    bld.add_post_fun(update_icon_cache)
    bld.add_pre_fun(lambda bld: manage_gconf_schemas(bld, "uninstall"))
