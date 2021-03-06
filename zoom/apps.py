"""
    zoom.apps

    handles requests by locating and calling a suitable app
"""

import configparser
import imp
import logging
import os
import sys

import zoom
from zoom.components import as_links
from zoom.database import Database
import zoom.html as html
from zoom.utils import existing


DEFAULT_SYSTEM_APPS = ['register', 'profile', 'login', 'logout']
DEFAULT_MAIN_APPS = ['home', 'admin', 'apps', 'info']
DEFAULT_SETTINGS = dict(
    title='',
    icon='cube',
    enabled=True,
    visible=True,
    theme='',
    description='',
    categories='',
    tags='',
    keywords='',
    in_development=False,
)


def load_module(module, filename):
    """Dynamically load a module"""
    logger = logging.getLogger(__name__)

    myhandler = \
        ImportError if sys.version_info < (3, 6) else ModuleNotFoundError

    try:
        pathname = os.path.realpath(filename)
        if os.path.exists(pathname):
            logger.debug('loading module %r', pathname)
            return imp.load_source(module, pathname)
        logger.warning('load_module file missing %r', pathname)
        return None
    except myhandler as err:
        msg = '%s while loading {!r} from {!r}' % myhandler.__name__
        cwd = os.getcwd()
        logger.error(msg.format((module, filename), cwd))
        logger.error('%s: %s', myhandler.__name__, err)
        raise


class App(object):
    """A Zoom application

    Looks for a method to satisfy the request.  If the method is
    not specified, it falls back to 'index'.  If there is no
    method on the app object to satisfy the method then it looks
    for a file in the app directory by that same name.  If it
    finds such a file it looks for the an entrypoint and if found
    it calls the entrypoint with the parameters the entrypoint
    expects.
    """

    def __init__(self):
        self.menu = []
        self.request = None

    def static(self, *args, **kwargs):
        return zoom.middleware.serve_response('static', *args)

    def process(self, *route, **data):
        """Process request parameters"""

        def if_callable(method):
            """test if callable and return it or None"""
            return callable(method) and method

        logger = logging.getLogger(__name__)

        isfile = os.path.isfile
        logger.debug('app called with route %r', route)

        if len(route) > 1:
            module = route[1]
            rest = route[2:]
        else:
            module = 'index'
            rest = route[1:]

        try:
            method = getattr(self, module)
        except AttributeError:
            method = None

        if method:
            result = method(*rest, **data)
            return result

        if len(route) > 1 and isfile('%s.py' % route[1]):
            module = route[1]
            rest = route[2:]
        else:
            module = 'index'
            rest = route[1:]

        filename = '{}.py'.format(module)
        if isfile(filename):
            logger.debug('file %s exists', filename)
            source = load_module(module, os.path.realpath(filename))
            main = if_callable(getattr(source, 'main', None))
            app = if_callable(getattr(source, 'app', None))
            view = if_callable(getattr(source, 'view', None))
            controller = if_callable(getattr(source, 'controller', None))
        else:
            main = app = view = None

        return (
            main and main(rest, self.request) or
            app and app(*rest, **data) or
            controller and controller(*rest, **data) or
            view and view(*rest, **data)
        )

    def __call__(self, request):
        self.request = request
        return self.process(*request.route, **request.data)


class AppProxy(object):
    """App Proxy

    Contains the various extra supporting parts of an app besides
    the actual functionality.  Apps themselves are simply callables
    that accept a request and return a response.  They can be implemented
    as simple functions or as something more substantial such as
    a subclass of the App class above.  That's entirely up to the
    app developer.  The AppProxy takes care of the other parts that
    an app needs, from it's location to it's icon to it's config files.
    """

    def __init__(self, name, filename, site):
        self.name = name
        self.filename = filename
        self.url = site.url + '/' + name
        self.abs_url = site.abs_url + '/' + name
        self.path = os.path.dirname(filename)
        self.site = site
        self.config_parser = configparser.ConfigParser()
        self.config = self.get_config(DEFAULT_SETTINGS)
        self.link = zoom.helpers.link_to(self.title, self.url)
        self.request = None
        self.packages = {}

        get = self.config.get
        self.visible = get('visible')
        self.enabled = get('enabled')
        self.author = get('author')
        self.version = get('version')
        self.theme = get('theme')
        self.icon = get('icon')
        self.as_icon = self.get_icon_view()
        self.in_development = get('in_development')

        self._method = None
        self._templates_paths = None

    @property
    def templates_paths(self):
        """Calculate Templates Paths"""
        join = os.path.join
        if self._templates_paths:
            return self._templates_paths
        site = self.site
        if self.theme:
            template_path = existing(join(site.themes_path, self.theme, 'templates'))
            theme_path = existing(join(site.themes_path, self.theme))
            paths = list(filter(bool, [
                template_path,
                theme_path,
            ]))
        else:
            paths = []
        self._templates_paths = paths
        return paths

    def get_icon_view(self):
        return """
        <div class="zoom-app-as-icon">
            <a href="{self.url}">
                <div class="zoom-app-icon">
                    <i class="fa fa-{self.icon}" aria-hidden="true"></i>
                </div>
                <div class="zoom-app-title">
                    {self.title}
                </div>
            </a>
        </div>
        """.format(self=self)

    @property
    def method(self):
        """Returns the app callable entry point"""
        if self._method is None:
            self.request.profiler.add('app loaded')
            self._method = getattr(load_module('app', self.filename), 'app')
            self.packages = zoom.packages.load(os.path.join(self.path, 'packages.json'))
        return self._method

    @property
    def title(self):
        """Returns the app title"""
        return self.config.get('title', self.name) or self.name.capitalize()

    @property
    def description(self):
        """Returns the app description"""
        return self.config.get('description') or \
            'The {} app.'.format(self.title)

    @property
    def keywords(self):
        """Returns the app keywords"""
        return self.config.get('keywords') or ', '.join(self.description.split())

    def run(self, request):
        """run the app"""
        logger = logging.getLogger(__name__)
        save_dir = os.getcwd()
        try:
            logger.debug('chdir to %r', self.path)
            os.chdir(self.path)
            self.request = request
            request.app = self
            app_callable = self.method
            response = app_callable(request)
            result = respond(response, request)
        finally:
            logger.debug('chdir back to %r', save_dir)
            os.chdir(save_dir)
        return result

    def run_background_jobs(self):
        pass

    def menu(self):
        """generate an app menu"""
        def by_name(name):
            """Returns a function that selects an item by name"""
            def selector(item):
                """Returns True if the item name matches"""
                return name == item.name
            return selector

        route = self.site.request.route
        logger = logging.getLogger(__name__)
        logger.debug('constructing menu')
        menu = getattr(self.method, 'menu', [])
        selected = (
            len(route) > 2 and route[0] == 'content' and route[2] or
            len(route) > 1 and route[1] or
            len(route) == 1 and route[0] != 'content' and 'index'
        )
        logger.debug('selected: %s', selected)
        result = as_links(menu, select=by_name(selected))
        return result

    def read_config(self, section, key, default=None):
        """read app config file values"""
        path = self.path
        join = os.path.join
        split = os.path.split

        local_config_file = join(path, 'config.ini')
        shared_config_file = join(split(path)[0], 'default.ini')
        system_config_file = join(split(path)[0], '..', '..', 'default.ini')

        config = self.config_parser
        try:
            config.read(local_config_file)
            return config.get(section, key)
        except:
            try:
                config.read(shared_config_file)
                return config.get(section, key)
            except:
                try:
                    config.read(system_config_file)
                    return config.get(section, key)
                except:
                    if default != None:
                        return default
                    else:
                        tpl = 'config setting [{}]{} not found in {} or {} or {}'
                        msg = tpl.format(section, key, local_config_file, shared_config_file, system_config_file)
                        raise Exception(msg)

    def get_config(self, default=None):
        """get the app config"""

        def as_dict(config):
            """
            Converts a ConfigParser object into a dictionary.
            """
            the_dict = {}
            for section in config.sections():
                for key, val in config.items(section):
                    the_dict[key] = val
            return the_dict

        def get_config(pathname):
            """read a config file"""
            self.config_parser.read(pathname)
            return as_dict(self.config_parser)

        path = self.path
        join = os.path.join
        split = os.path.split

        local_config_file = join(path, 'config.ini')
        shared_config_file = join(split(path)[0], 'default.ini')
        system_config_file = join(split(path)[0], '..', '..', 'default.ini')

        local_settings = get_config(local_config_file)
        shared_settings = get_config(shared_config_file)
        system_settings = get_config(system_config_file)

        result = {}
        result.update(default or {})
        result.update(system_settings)
        result.update(shared_settings)
        result.update(local_settings)
        return result

    def __str__(self):
        return self.link

    def __repr__(self):
        return str(self)


class NoApp(object):
    """default app used when no app is available

    This is mostly used so the helpers remain valid
    and return reasonable values when no app is available.
    """
    url = ''
    menu_items = []
    menu = ''
    name = 'none'
    theme = None


def respond(content, request):
    """construct a response"""

    html_response = zoom.response.HTMLResponse

    if content:
        if isinstance(content, zoom.response.Response):
            result = content

        elif isinstance(content, zoom.Component):
            result = html_response(content.render())

        elif hasattr(content, 'render') and content.render:
            result = content.render(request)

        elif isinstance(content, (list, set, tuple)):
            result = html_response(''.join(content))

        elif isinstance(content, str):
            result = html_response(content)

        else:
            result = html_response('OK')

        return result


def load_app(site, name):
    """get the location of an app by name"""
    apps_paths = site.apps_paths
    for path in apps_paths:
        app_path = os.path.abspath(
            os.path.join(site.path, path, name)
        )
        filename = os.path.join(app_path, 'app.py')
        if os.path.exists(filename):
            return AppProxy(name, filename, site)


def get_default_app_name(site, user):
    """get the default app for the currrent user"""
    if user.is_authenticated:
        default_app = site.config.get('apps', 'home', 'home')
    else:
        default_app = site.config.get('apps', 'index', 'content')
    return default_app


def handle(request):
    """handle a request"""

    def run_app(app):
        """Run an app"""
        request.app = app
        zoom.render.add_helpers(helpers(request))

        saved_database_debug_setting =  Database.debug
        try:
            Database.debug = request.site.monitor_app_database
            request.profiler.add('system ready')
            result = app.run(request)
            request.profiler.add('app finished')
        finally:
            Database.debug = saved_database_debug_setting
        return result

    logger = logging.getLogger(__name__)

    user = request.user
    app_name = request.route and request.route[0] or None
    logger.debug('app_name is: %r', app_name)
    app = app_name and load_app(request.site, app_name)

    if not app:
        logger.debug('app %r not found in site.apps_paths', app_name)
        logger.debug('site.apps_paths: %r', request.site.apps_paths)

    redirect_response = zoom.response.RedirectResponse

    if app and app.enabled and user.can_run(app):
        logger.debug('running requested app')
        return run_app(app)

    elif app and app.enabled and user.is_guest:
        logger.debug('redirecting to login')
        return redirect_response('/login')

    elif app and app.enabled:
        msg = (
            '%r has insufficient privileges to run app %s (%r), '
            'redirecting to default'
        )
        logger.warning(msg, user.username, app_name, app.path)
        return redirect_response('/')

    elif app:
        msg = 'app %s (%r) disabled, redirecting to default'
        logger.warning(msg, app_name, app.path)
        return redirect_response('/')

    else:
        if app_name:
            logger.debug('unable to run requested app %r', app_name)
        app_name = get_default_app_name(request.site, request.user)
        app = load_app(request.site, app_name)
        if app and app.enabled and user.can_run(app):
            return run_app(app)

        elif app and app.enabled:
            logger.debug('user %r cannot run %r', user.username, app_name)

        elif app:
            logger.debug('app %r is disabled', app_name)

        else:
            logger.debug('unable to load app %r', app_name)

    logger.debug('using NoApp()')
    request.app = NoApp()


def get_system_apps(request):
    """Returns a list containing the system apps.

    System apps are apps that appear in the system menu, which is usually found
    at the top left of a web site.  The system menu typically includes apps such
    as login, logout, profile and register.

    This list can be defined in the site.ini file in the [apps] section using the
    key `system`.  A example is provided in the default site.ini file.
    """
    get = request.site.config.get
    names = get('apps', 'system', '')
    names = names and [s.strip() for s in names.split(',')] or DEFAULT_SYSTEM_APPS
    user = request.user
    apps = filter(user.can_run, [
        load_app(request.site, name) for name in names
        ])
    return apps


def system_menu_items(request):
    """Returns the system menu."""
    return html.li([
        app.link for app in get_system_apps(request)
        if app.visible and app.name != request.app.name
    ])


def system_menu(request):
    """Returns the system menu."""
    if request.user.is_authenticated:
        path = os.path.dirname(__file__)
        filename = os.path.join(path, 'views', 'system_pulldown_menu.html')
        return zoom.tools.load_content(filename)
    else:
        return '<div class="system-menu"><ul>{}</ul></div>'.format(
            system_menu_items(request)
        )


def get_main_apps(request):
    """Returns a list of the main apps.

    Main apps are apps that appear in the main menu, which is usually found
    at the top of a web site's pages.  The system menu typically includes apps
    such as home, admin and the apps app.

    This list can be defined in the site.ini file in the [apps] section using the
    key `main`.  A example is provided in the default site.ini file.
    """
    get = request.site.config.get
    names = get('apps', 'main', '')
    names = names and [s.strip() for s in names.split(',')] or DEFAULT_MAIN_APPS
    user = request.user
    apps = filter(user.can_run, [
        load_app(request.site, name) for name in names
        ])
    return apps


def main_menu_items(request):
    """Returns the main menu."""

    def style(app):
        return app.name == current_app_name and 'class="active" ' or ''

    default_app_name = get_default_app_name(request.site, request.user)
    current_app_name = request.route and request.route[0] or default_app_name

    return html.li([
        app.name == default_app_name
        and '<a {}href="<dz:site_url>/">{}</a>'.format(
            style(app), app.title
        )
        or '<a {}href="<dz:site_url>{}">{}</a>'.format(
            style(app), app.url, app.title
        )
        for app in get_main_apps(request) if app.visible
    ])


def main_menu(request):
    """Returns the main menu."""
    return '<ul>%s</ul>' % main_menu_items(request)


def helpers(request):
    """return a dict of app helpers"""
    app = request.app
    return dict(
        app_title=app.title,
        app_url=request.app.url,
        app_menu=request.app.menu,
        app_name=request.app.name,
        app_class=zoom.utils.id_for(request.app.name.strip()),
        app_description=request.app.description,
        app_keywords=request.app.keywords,
        system_menu_items=system_menu_items(request),
        system_menu=system_menu(request),
        main_menu_items=main_menu_items(request),
        main_menu=main_menu(request),
        page_name=len(request.route) > 1 and request.route[1] or '',
    )


def handler(request, next_handler, *rest):
    """Dispatch request to an application"""
    logger = logging.getLogger(__name__)
    logger.debug('apps_handler')
    if '.' not in sys.path:
        logger.debug('adding "." to path')
        sys.path.insert(0, '.')
    response = handle(request)
    logger.debug('app responded with type %s' % type(response))
    return response or next_handler(request, *rest)
