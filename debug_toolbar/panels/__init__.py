from django.template.defaultfilters import slugify
from debug_toolbar.middleware import DebugToolbarMiddleware


class DebugPanel(object):
    """
    Base class for debug panels.
    """
    # name = Base
    has_content = False # If content returns something, set to true in subclass
    
    # We'll maintain a local context instance so we can expose our template
    # context variables to panels which need them:
    context = {}
    
    # Panel methods
    def __init__(self, context={}):
        self.context.update(context)
        self.toolbar = DebugToolbarMiddleware.get_current()
        self.slug = slugify(self.name)
    
    def dom_id(self):
        return 'djDebug%sPanel' % (self.name.replace(' ', ''))
    
    def nav_title(self):
        """Title showing in toolbar"""
        raise NotImplementedError
    
    def nav_subtitle(self):
        """Subtitle showing until title in toolbar"""
        return ''
    
    def title(self):
        """Title showing in panel"""
        raise NotImplementedError
    
    def url(self):
        raise NotImplementedError
    
    def content(self):
        raise NotImplementedError
    
    def record_stats(self, stats):
        self.toolbar.stats[self.slug].update(stats)
    
    def get_stats(self):
        return self.toolbar.stats[self.slug]
    
    # Standard middleware methods
    def process_request(self, request):
        pass
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        pass
    
    def process_response(self, request, response):
        pass
