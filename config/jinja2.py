from jinja2 import Environment
from django.urls import reverse as django_reverse
from django.contrib.staticfiles.storage import staticfiles_storage
from django.contrib.messages import get_messages


def url(name, *args, **kwargs):
    """Jinja2-friendly wrapper around django.urls.reverse."""
    return django_reverse(name, args=args, kwargs=kwargs)


def environment(**options):
    env = Environment(**options)
    env.globals.update(
        {
            "url": url,
            "static": staticfiles_storage.url,
            "get_messages": get_messages,
        }
    )
    return env
