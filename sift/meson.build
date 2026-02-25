python_sources = [
  '__init__.py',
  'config.py',
  'file_card.py',
  'file_manager.py',
  'main.py',
  'shortcuts.py',
  'window.py',
]

install_data(python_sources,
  install_dir: join_paths(python.find_installation('python3').get_install_dir(), 'sift')
)

# Install CSS
install_data('style.css',
  install_dir: join_paths(python.find_installation('python3').get_install_dir(), 'sift')
)

# Entry point script
conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('pkgdatadir', join_paths(get_option('prefix'), get_option('datadir'), meson.project_name()))
conf.set('pythondir', python.find_installation('python3').get_install_dir())

configure_file(
  input: 'sift.in',
  output: 'sift',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)
