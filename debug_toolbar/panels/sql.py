import re

from django.conf import settings
from django.db.backends import BaseDatabaseWrapper
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ungettext_lazy as __

from debug_toolbar.utils.compat.db import connections
from debug_toolbar.middleware import DebugToolbarMiddleware
from debug_toolbar.panels import DebugPanel
from debug_toolbar.utils import sqlparse
from debug_toolbar.utils.tracking.db import CursorWrapper
from debug_toolbar.utils.tracking import replace_call

# Inject our tracking cursor
@replace_call(BaseDatabaseWrapper.cursor)
def cursor(func, self):
    result = func(self)

    djdt = DebugToolbarMiddleware.get_current()
    if not djdt:
        return result
    logger = djdt.get_panel(SQLDebugPanel)
    
    return CursorWrapper(result, self, logger=logger)

class SQLDebugPanel(DebugPanel):
    """
    Panel that displays information about the SQL queries run while processing
    the request.
    """
    name = 'SQL'
    has_content = True

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self._offset = dict((k, len(connections[k].queries)) for k in connections)
        self._sql_time = 0
        self._num_queries = 0
        self._queries = []
        self._databases = {}
    
    def record(self, alias, **kwargs):
        self._queries.append((alias, kwargs))
        if alias not in self._databases:
            self._databases[alias] = {
                'time_spent': kwargs['duration'],
                'num_queries': 1,
            }
        else:
            self._databases[alias]['time_spent'] += kwargs['duration']
            self._databases[alias]['num_queries'] += 1
        self._sql_time += kwargs['duration']
        self._num_queries += 1

    def nav_title(self):
        return _('SQL')

    def nav_subtitle(self):
        # TODO l10n: use ngettext
        return "%d %s in %.2fms" % (
            self._num_queries,
            (self._num_queries == 1) and 'query' or 'queries',
            self._sql_time
        )

    def title(self):
        count = len(self._databases)
        
        return __('SQL Queries from %(count)d connection', 'SQL Queries from %(count)d connections', count) % dict(
            count=count,
        )

    def url(self):
        return ''

    def content(self):
        if self._queries:
            width_ratio_tally = 0
            colors = [
                (256, 0, 0), # red
                (0, 256, 0), # blue
                (0, 0, 256), # green
            ]
            factor = int(256.0/(len(self._databases)*2.5))
            for n, db in enumerate(self._databases.itervalues()):
                rgb = [0, 0, 0]
                color = n % 3
                rgb[color] = 256 - n/3*factor
                nn = color
                # XXX: pretty sure this is horrible after so many aliases
                while rgb[color] < factor:
                    nc = min(256 - rgb[color], 256)
                    rgb[color] += nc
                    nn += 1
                    if nn > 2:
                        nn = 0
                    rgb[nn] = nc
                db['rgb_color'] = rgb
        
            for alias, query in self._queries:
                query['alias'] = alias
                query['sql'] = reformat_sql(query['sql'])
                query['rgb_color'] = self._databases[alias]['rgb_color']
                try:
                    query['width_ratio'] = (query['duration'] / self._sql_time) * 100
                except ZeroDivisionError:
                    query['width_ratio'] = 0
                query['start_offset'] = width_ratio_tally
                query['end_offset'] = query['width_ratio'] + query['start_offset']
                width_ratio_tally += query['width_ratio']
            
                stacktrace = []
                for frame in query['stacktrace']:
                    params = map(escape, frame[0].rsplit('/', 1) + list(frame[1:]))
                    stacktrace.append('<span class="path">{0}/</span><span class="file">{1}</span> in <span class="func">{3}</span>(<span class="lineno">{2}</span>)\n  <span class="code">{4}</span>"'.format(*params))
                query['stacktrace'] = mark_safe('\n'.join(stacktrace))
        
        context = self.context.copy()
        context.update({
            'databases': sorted(self._databases.items(), key=lambda x: -x[1]['time_spent']),
            'queries': [q for a, q in self._queries],
            'sql_time': self._sql_time,
            'is_mysql': settings.DATABASE_ENGINE == 'mysql',
        })

        return render_to_string('debug_toolbar/panels/sql.html', context)

class BoldKeywordFilter(sqlparse.filters.Filter):
    """sqlparse filter to bold SQL keywords"""
    def process(self, stack, stream):
        """Process the token stream"""
        for token_type, value in stream:
            is_keyword = token_type in sqlparse.tokens.Keyword
            if is_keyword:
                yield sqlparse.tokens.Text, '<strong>'
            yield token_type, escape(value)
            if is_keyword:
                yield sqlparse.tokens.Text, '</strong>'

def swap_fields(sql):
    return re.sub('SELECT</strong> (.*) <strong>FROM', 'SELECT</strong> <span class="djDebugCollapse">\g<1></span> <strong>FROM', sql)

def reformat_sql(sql):
    stack = sqlparse.engine.FilterStack()
    stack.preprocess.append(BoldKeywordFilter()) # add our custom filter
    stack.postprocess.append(sqlparse.filters.SerializerUnicode()) # tokens -> strings
    return swap_fields(''.join(stack.run(sql)))
