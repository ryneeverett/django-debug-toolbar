from debug_toolbar.middleware import DebugToolbarMiddleware
from debug_toolbar.panels.sql import SQLDebugPanel
from debug_toolbar.toolbar.loader import DebugToolbar
from debug_toolbar.utils.tracking import pre_dispatch, post_dispatch, callbacks

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase

from dingus import Dingus
import thread


class Settings(object):
    """Allows you to define settings that are required for this function to work"""

    NotDefined = object()

    def __init__(self, **overrides):
        self.overrides = overrides
        self._orig = {}

    def __enter__(self):
        for k, v in self.overrides.iteritems():
            self._orig[k] = getattr(settings, k, self.NotDefined)
            setattr(settings, k, v)

    def __exit__(self, exc_type, exc_value, traceback):
        for k, v in self._orig.iteritems():
            if v is self.NotDefined:
                delattr(settings, k)
            else:
                setattr(settings, k, v)
    
class BaseTestCase(TestCase):
    def setUp(self):
        request = Dingus('request')
        toolbar = DebugToolbar(request)

        DebugToolbarMiddleware.debug_toolbars[thread.get_ident()] = toolbar

        self.request = request
        self.toolbar = toolbar

class DebugToolbarTestCase(BaseTestCase):
    urls = 'debug_toolbar.tests.urls'
    
    def test_middleware(self):
        resp = self.client.get('/execute_sql/')
        self.assertEquals(resp.status_code, 200)

    def test_show_toolbar_DEBUG(self):
        request = self.request
        
        middleware = DebugToolbarMiddleware()
        
        with Settings(DEBUG=True):
            self.assertTrue(middleware._show_toolbar(request))

        with Settings(DEBUG=False):
            self.assertFalse(middleware._show_toolbar(request))

    def test_show_toolbar_TEST(self):
        request = self.request
        
        middleware = DebugToolbarMiddleware()
        
        with Settings(TEST=True):
            self.assertTrue(middleware._show_toolbar(request))

        with Settings(TEST=False):
            self.assertFalse(middleware._show_toolbar(request))

    def test_show_toolbar_INTERNAL_IPS(self):
        request = self.request
        
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        middleware = DebugToolbarMiddleware()
        
        with Settings(INTERNAL_IPS=['127.0.0.1']):
            self.assertTrue(middleware._show_toolbar(request))

        with Settings(INTERNAL_IPS=[]):
            self.assertFalse(middleware._show_toolbar(request))

    def test_request_urlconf_string(self):
        request = self.request
        
        request.urlconf = 'debug_toolbar.tests.urls'
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        middleware = DebugToolbarMiddleware()
        
        with Settings(DEBUG=True):
            middleware.process_request(request)
            
            self.assertFalse(isinstance(request.urlconf, basestring))
            
            self.assertTrue(hasattr(request.urlconf.urlpatterns[0], '_callback_str'))
            self.assertEquals(request.urlconf.urlpatterns[0]._callback_str, 'debug_toolbar.views.debug_media')
            self.assertEquals(request.urlconf.urlpatterns[-1].urlconf_name.__name__, 'debug_toolbar.tests.urls')

    def test_request_urlconf_string_per_request(self):
        request = self.request
        
        request.urlconf = 'debug_toolbar.tests.urls'
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        middleware = DebugToolbarMiddleware()
        
        with Settings(DEBUG=True):
            middleware.process_request(request)
            request.urlconf = 'debug_toolbar.urls'
            middleware.process_request(request)

            self.assertFalse(isinstance(request.urlconf, basestring))
            
            self.assertTrue(hasattr(request.urlconf.urlpatterns[0], '_callback_str'))
            self.assertEquals(request.urlconf.urlpatterns[0]._callback_str, 'debug_toolbar.views.debug_media')
            self.assertEquals(request.urlconf.urlpatterns[-1].urlconf_name.__name__, 'debug_toolbar.urls')

    def test_request_urlconf_module(self):
        request = self.request
        
        request.urlconf = __import__('debug_toolbar.tests.urls').tests.urls
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        middleware = DebugToolbarMiddleware()
        
        with Settings(DEBUG=True):
            middleware.process_request(request)
            
            self.assertFalse(isinstance(request.urlconf, basestring))
            
            self.assertTrue(hasattr(request.urlconf.urlpatterns[0], '_callback_str'))
            self.assertEquals(request.urlconf.urlpatterns[0]._callback_str, 'debug_toolbar.views.debug_media')
            self.assertEquals(request.urlconf.urlpatterns[-1].urlconf_name.__name__, 'debug_toolbar.tests.urls')

class SQLPanelTestCase(BaseTestCase):
    def test_recording(self):
        panel = self.toolbar.get_panel(SQLDebugPanel)
        self.assertEquals(len(panel._queries), 0)
        
        list(User.objects.all())
        
        # ensure query was logged
        self.assertEquals(len(panel._queries), 1)
        query = panel._queries[0]
        self.assertEquals(query[0], 'default')
        self.assertTrue('sql' in query[1])
        self.assertTrue('duration' in query[1])
        self.assertTrue('stacktrace' in query[1])

def module_func(*args, **kwargs):
    """Used by dispatch tests"""
    return 'blah'

class TrackingTestCase(BaseTestCase):
    @classmethod
    def class_method(cls, *args, **kwargs):
        return 'blah'

    def class_func(self, *args, **kwargs):
        """Used by dispatch tests"""
        return 'blah'
    
    def test_pre_hook(self):
        foo = {}
        
        @pre_dispatch(module_func)
        def test(**kwargs):
            foo.update(kwargs)
            
        self.assertTrue(hasattr(module_func, '__wrapped__'))
        self.assertEquals(len(callbacks['before']), 1)
        
        module_func('hi', foo='bar')
        
        self.assertTrue('sender' in foo, foo)
        # best we can do
        self.assertEquals(foo['sender'].__name__, 'module_func')
        self.assertTrue('start' in foo, foo)
        self.assertTrue(foo['start'] > 0)
        self.assertTrue('stop' not in foo, foo)
        self.assertTrue('args' in foo, foo)
        self.assertTrue(len(foo['args']), 1)
        self.assertEquals(foo['args'][0], 'hi')
        self.assertTrue('kwargs' in foo, foo)
        self.assertTrue(len(foo['kwargs']), 1)
        self.assertTrue('foo' in foo['kwargs'])
        self.assertEquals(foo['kwargs']['foo'], 'bar')
    
        callbacks['before'] = {}
    
        @pre_dispatch(TrackingTestCase.class_func)
        def test(**kwargs):
            foo.update(kwargs)
    
        self.assertTrue(hasattr(TrackingTestCase.class_func, '__wrapped__'))
        self.assertEquals(len(callbacks['before']), 1)

        self.class_func('hello', foo='bar')

        self.assertTrue('sender' in foo, foo)
        # best we can do
        self.assertEquals(foo['sender'].__name__, 'class_func')
        self.assertTrue('start' in foo, foo)
        self.assertTrue(foo['start'] > 0)
        self.assertTrue('stop' not in foo, foo)
        self.assertTrue('args' in foo, foo)
        self.assertTrue(len(foo['args']), 2)
        self.assertEquals(foo['args'][1], 'hello')
        self.assertTrue('kwargs' in foo, foo)
        self.assertTrue(len(foo['kwargs']), 1)
        self.assertTrue('foo' in foo['kwargs'])
        self.assertEquals(foo['kwargs']['foo'], 'bar')

        # callbacks['before'] = {}
        #     
        #         @pre_dispatch(TrackingTestCase.class_method)
        #         def test(**kwargs):
        #             foo.update(kwargs)
        #     
        #         self.assertTrue(hasattr(TrackingTestCase.class_method, '__wrapped__'))
        #         self.assertEquals(len(callbacks['before']), 1)
        # 
        #         TrackingTestCase.class_method()
        # 
        #         self.assertTrue('sender' in foo, foo)
        #         # best we can do
        #         self.assertEquals(foo['sender'].__name__, 'class_method')
        #         self.assertTrue('start' in foo, foo)
        #         self.assertTrue('stop' not in foo, foo)
        #         self.assertTrue('args' in foo, foo)

    def test_post_hook(self):
        foo = {}
        
        @post_dispatch(module_func)
        def test(**kwargs):
            foo.update(kwargs)
            
        self.assertTrue(hasattr(module_func, '__wrapped__'))
        self.assertEquals(len(callbacks['after']), 1)
        
        module_func('hi', foo='bar')
        
        self.assertTrue('sender' in foo, foo)
        # best we can do
        self.assertEquals(foo['sender'].__name__, 'module_func')
        self.assertTrue('start' in foo, foo)
        self.assertTrue(foo['start'] > 0)
        self.assertTrue('stop' in foo, foo)
        self.assertTrue(foo['stop'] > foo['start'])
        self.assertTrue('args' in foo, foo)
        self.assertTrue(len(foo['args']), 1)
        self.assertEquals(foo['args'][0], 'hi')
        self.assertTrue('kwargs' in foo, foo)
        self.assertTrue(len(foo['kwargs']), 1)
        self.assertTrue('foo' in foo['kwargs'])
        self.assertEquals(foo['kwargs']['foo'], 'bar')
    
        callbacks['after'] = {}
    
        @post_dispatch(TrackingTestCase.class_func)
        def test(**kwargs):
            foo.update(kwargs)
    
        self.assertTrue(hasattr(TrackingTestCase.class_func, '__wrapped__'))
        self.assertEquals(len(callbacks['after']), 1)

        self.class_func('hello', foo='bar')

        self.assertTrue('sender' in foo, foo)
        # best we can do
        self.assertEquals(foo['sender'].__name__, 'class_func')
        self.assertTrue('start' in foo, foo)
        self.assertTrue(foo['start'] > 0)
        self.assertTrue('stop' in foo, foo)
        self.assertTrue(foo['stop'] > foo['start'])
        self.assertTrue('args' in foo, foo)
        self.assertTrue(len(foo['args']), 2)
        self.assertEquals(foo['args'][1], 'hello')
        self.assertTrue('kwargs' in foo, foo)
        self.assertTrue(len(foo['kwargs']), 1)
        self.assertTrue('foo' in foo['kwargs'])
        self.assertEquals(foo['kwargs']['foo'], 'bar')