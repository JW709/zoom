"""
    home app

    the users home desktop
"""

import zoom


def app(request):
    """Return a page containing a list of available apps"""
    skip = 'home', 'logout'
    content = zoom.html.ol(
        repr(a) for a in sorted(request.site.apps, key=lambda a: a.title)
        if a.name not in skip and request.user.can_run(a)
    )
    return zoom.page(content, title="Apps")
