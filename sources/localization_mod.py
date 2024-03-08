from gettext import gettext, translation
from sources.config_mod import config_read_helper


def select_language(domain: str) -> gettext:
    try:
        current_lang = config_read_helper("Language", "current")
        if current_lang == "English":
            language = translation(domain, localedir='.//data//locales', languages=['en'])
            language.install()
            _ = language.gettext
        else:
            _ = gettext
    except Exception as e:
        _ = gettext
    return _
