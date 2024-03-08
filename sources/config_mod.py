from os import getcwd
from configparser import ConfigParser


def config_read_helper(section: str, option: str) -> str:
    result = ""
    config = ConfigParser()
    config.read(getcwd() + "//data//config//settings.ini")
    result = config.get(section, option)
    return result