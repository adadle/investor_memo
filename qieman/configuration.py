# coding = utf-8
"""
read configs to object conf
"""

import os
from backports.configparser import ConfigParser


class Configuration(ConfigParser):

    def __init__(self, *args, **kwargs):
        super(Configuration, self).__init__(*args, **kwargs)
        default_config, default_conf_path = self._read_default_config_file(self._get_default_conf_file())

        if default_config:
            super(Configuration, self).read_string(default_config)

    def _get_default_conf_file(self):
        import os
        current_dir = os.path.dirname(__file__)
        conf_file = os.path.join(current_dir, 'config.cfg')

        if os.getenv('IS_PROD'):
            conf_file = os.environ['HOME'] + '/.fire/craw_config.cfg'
        return conf_file

    def _read_default_config_file(self, file_name):
        with open(file_name, encoding='utf-8') as file_handle:
            return file_handle.read(), file_name


def render_config(template):
    """
    to render configs for some variables
    :param template:
    :return:
    """
    rendered_vars = {k: v for x in [locals(), globals()] for k, v in x.items()}
    return template.format(**rendered_vars)


conf = Configuration()
