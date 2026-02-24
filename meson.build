project('gnome-sift',
  version: '0.1.0',
  meson_version: '>= 0.62.0',
)

i18n = import('i18n')
gnome = import('gnome')
python = import('python')

project_id = 'com.github.frephs.Sift'

subdir('data')
subdir('gnome_sift')

# Post-install script
meson.add_install_script('build-aux/meson_post_install.py')
