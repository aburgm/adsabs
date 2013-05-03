'''
Created on Sep 19, 2012

@author: jluker
'''
import re

from flask import g, current_app as app
from urllib import urlencode
from copy import deepcopy
from simplejson import loads
from config import config
from .response import SolrResponse
from solr import SolrException

class SolrRequest(object):
    
    def __init__(self, q, **kwargs):
        self.q = q
        self.params = SolrParams(q=q, **kwargs)
        
    def set_params(self, **kwargs):
        self.params.update(**kwargs)
        return self
        
    def set_format(self, fmt):
        self.params.wt = fmt
        return self
        
    def set_rows(self, rows):
        self.params.rows = rows
        return self
        
    def set_start(self, start):
        self.params.start = start
        return self
        
    def set_fields(self, fields):
        if isinstance(fields, list):
            self.params.fl = ','.join(fields)
        elif isinstance(fields, basestring):
            self.params.fl = fields
        else:
            raise Exception("fields must be expressed as a list or comma-separated string")
        return self
        
    def get_fields(self):
        if self.params.has_key('fl'):
            return self.params.fl.split(',')
        return []
        
    def set_sort(self, sort_field, direction="desc"):
        self.params.sort = "%s %s" % (sort_field, direction)
        return self
        
    def add_sort(self, sort_field, direction="desc"):
        if not self.params.has_key('sort'):
            self.set_sort(sort_field, direction)
        else:
            self.params.sort += ',%s %s' % (sort_field, direction)
        return self
        
    def get_sort(self):
        sort = []
        if self.params.has_key('sort'):
            return [tuple(x.split()) for x in self.params.sort.split(',')]
    
    def set_hlq(self, hlq):
        self.params['hl.q'] = hlq
        return self
        
    def add_filter(self, filter_):
        if config.SOLR_FILTER_QUERY_PARSER:
            filter_ = "{!%s}%s" % (config.SOLR_FILTER_QUERY_PARSER, filter_)
        self.params.append('fq', filter_)
        return self
        
    def get_filters(self, exclude_defaults=False):
        filters = self.params.get('fq', [])
        if exclude_defaults:
            default_params = dict(config.SOLR_MISC_DEFAULT_PARAMS)
            filters = filter(lambda x: x not in default_params.get('fq', []), filters)
        return filters
        
    def add_facet(self, field, limit=None, mincount=None, output_key=None, prefix=None):
        self.params['facet'] = "true"
        self.params.setdefault('facet.field', [])
        if output_key:
            self.params.append('facet.field', "{!ex=dt key=%s}%s" % (output_key, field))
        else:
            self.params.append('facet.field', field)
        if limit:
            self.params['f.%s.facet.limit' % field] = limit
        if mincount:
            self.params['f.%s.facet.mincount' % field] = mincount
        if prefix:
            self.params['f.%s.facet.prefix' % field] = prefix
        return self
            
    def add_facet_query(self, query):
        self.params['facet'] = "true"
        self.params.setdefault('facet.query', [])
        self.params.append('facet.query', query)
        return self
    
    def get_facet_queries(self):
        facet_queries = []
        if self.facets_on():
            for fq in self.params.get('facet.query', []):
                facet_queries.append(fq)
        return facet_queries
        
    def facets_on(self):
        return self.params.facet and True or False
    
    def add_facet_prefix(self, field, prefix):
        self.params['f.%s.facet.prefix' % field] = prefix
    
    def get_facets(self):
        facets = []
        if self.facets_on():
            for fl in self.params.get('facet.field', []):
                if fl.startswith('{!ex=dt'):
                    m = re.search("key=(\w+)}(\w+)", fl)
                    output_key, fl = m.groups()
                else:
                    output_key = None
                limit = self.params.get('f.%s.facet.limit' % fl, None)
                mincount = self.params.get('f.%s.facet.mincount' % fl, None)
                prefix = self.params.get('f.%s.facet.prefix' % fl, None)
                facets.append((fl, limit, mincount, output_key, prefix))
        return facets
    
    def add_highlight(self, fields, count=None, fragsize=None):
        self.params['hl'] = "true"
        if isinstance(fields, basestring):
            fields = [fields]
        for field in fields:
            if not self.params.has_key('hl.fl'):
                self.params['hl.fl'] = field
            elif field not in self.params['hl.fl'].split(','):
                self.params['hl.fl'] += ',' + field
            if count:
                self.params['f.%s.hl.snippets' % field] = count
            if fragsize:
                self.params['f.%s.hl.fragsize' % field] = fragsize
        return self
            
    def highlights_on(self):
        return self.params.hl and True or False
    
    def get_highlights(self):
        highlights = []
        if self.highlights_on() and self.params.has_key('hl.fl'):
            for fl in self.params.get('hl.fl').split(','):
                count = self.params.get('f.%s.hl.snippets' % fl, None)
                fragsize = self.params.get('f.%s.hl.fragsize' % fl, None)
                highlights.append((fl, count, fragsize))
        return highlights
    
    def get_response(self):
        try:
            json = g.solr.select.raw(**self.params)
        except SolrException as se:
            app.logger.error("SolrException error. Request url: %s" % self.get_raw_request_url())
            json =  se.body
        except:
            app.logger.error("Something blew up when querying solr. Request url: %s" % self.get_raw_request_url())
            raise
        
        data = loads(json)
        return SolrResponse(data, self)
    
    def get_raw_request_url(self):
        qstring = []
        to_str = lambda s: s.encode('utf-8') if isinstance(s, unicode) else s
        for key, value in self.params.items():
#            key = key.replace(self.arg_separator, '.')
            if isinstance(value, (list, tuple)):
                qstring.extend([(key, to_str(v)) for v in value])
            else:
                qstring.append((key, to_str(value)))
        qstring = urlencode(qstring, doseq=True)
        return "%s/select?%s" % (g.solr.url, qstring)
    
        
class SolrParams(dict):
    
    def __init__(self, *args, **kwargs):
        # set default values
        default_params = dict(
                    config.SOLR_MISC_DEFAULT_PARAMS,
                    wt=config.SOLR_DEFAULT_FORMAT
                    )
        self.update(**deepcopy(default_params))
        self.update(*args, **kwargs)

    def __getattr__(self, key):
        if not self.has_key(key):
            return None
        return dict.__getitem__(self, key)

    def __setattr__(self, key, val):
        dict.__setitem__(self, key, val)

    def __repr__(self):
        dictrepr = dict.__repr__(self)
        return '%s(%s)' % (type(self).__name__, dictrepr)

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).iteritems():
            self[k] = v
            
    def append(self, key, val):
        self.setdefault(key, [])
        if val not in self[key]:
            self[key].append(val)
                                