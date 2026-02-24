desktop_conf = configuration_data()
desktop_conf.set('APP_ID', project_id)

configure_file(
  input: 'com.github.frephs.Sift.desktop.in',
  output: project_id + '.desktop',
  configuration: desktop_conf,
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

# Install icon
install_data(
  '../gnome_sift/resources/' + project_id + '.svg',
  install_dir: join_paths(get_option('datadir'), 'icons/hicolor/scalable/apps'),
  rename: project_id + '.svg'
)
