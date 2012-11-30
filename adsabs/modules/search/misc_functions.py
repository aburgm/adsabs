'''
Created on Nov 30, 2012

@author: dimilia
'''

from config import config

def build_basicquery_components(form):
    """
    Takes in input a validated basic form and returns a dictionary containing 
    all the components needed to run a SOLR query
    """
    search_components = {
            'q' : None,
            'filters': [],
            'sort': None,
    }
    #one box query
    search_components['q'] = form.q.data
    #databases
    if form.db_key.data in ('ASTRONOMY', 'PHYSICS',):
        search_components['filters'].append('database:%s' % form.db_key.data)
    #sorting
    if form.sort_type.data in config.SOLR_SORT_OPTIONS.keys():
        search_components['sort'] = form.sort_type.data
    #second order operators wrap the query
    elif form.sort_type.data in config.SEARCH_SECOND_ORDER_OPERATORS_OPTIONS:
        search_components['q'] = u'%s(%s)' % (form.sort_type.data, search_components['q'])
    #date range
    if form.year_from.data or form.year_to.data:
        mindate = '*'
        maxdate = '*'
        if form.year_from.data:
            if form.month_from.data:
                mindate = u'%s%s00' % (form.year_from.data, unicode(form.month_from.data).zfill(2))
            else:
                mindate = u'%s%s00' % (form.year_from.data, u'00')
        if form.year_to.data:
            if form.month_to.data:
                maxdate = u'%s%s00' % (form.year_to.data, unicode(form.month_to.data).zfill(2))
            else:
                maxdate = u'%s%s00' % (form.year_to.data, u'00')
        search_components['filters'].append(u'pubdate_sort:[%s TO %s]' % (mindate, maxdate))
    #refereed
    if form.refereed.data:
        search_components['filters'].append(u'property:REFEREED')
    #articles only
    if form.article.data:
        search_components['filters'].append(u'-property:NONARTICLE')
    #journal abbreviation
    if form.journal_abbr.data:
        journal_abbr_string = ''
        for bibstem in form.journal_abbr.data.split(','):
            journal_abbr_string += u'bibstem:%s OR ' % bibstem.strip()
        search_components['filters'].append(journal_abbr_string[:-4])   
    return search_components