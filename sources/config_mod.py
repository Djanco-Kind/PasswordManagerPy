from os import getcwd
from configparser import ConfigParser


def config_read_helper(section: str, option: str) -> str:
    config = ConfigParser()
    config.read(getcwd() + "//data//config//settings.ini")
    result = config.get(section, option)
    return result


def config_set_helper(section: str, option: str, value: str):
    config = ConfigParser()
    config.read(getcwd() + "//data//config//settings.ini")
    config.set(section, option, value)
    with open(getcwd() + "//data//config//settings.ini", "w") as conffile:
        config.write(conffile)
