#!/usr/bin/env python3

import os
import subprocess

install_prefix = os.environ.get('MESON_INSTALL_PREFIX', '/usr/local')
datadir = os.path.join(install_prefix, 'share')

# Update icon cache
if not os.environ.get('DESTDIR'):
    print('Updating icon cache...')
    subprocess.call(['gtk4-update-icon-cache', '-qtf', os.path.join(datadir, 'icons', 'hicolor')])

    print('Updating desktop database...')
    subprocess.call(['update-desktop-database', '-q', os.path.join(datadir, 'applications')])

    # If we had schemas, we would update them here
    # print('Compiling GSettings schemas...')
    # subprocess.call(['glib-compile-schemas', os.path.join(datadir, 'glib-2.0', 'schemas')])
