"""
Sequential text parser
Allow to extract structured text using text patterns and a state machine.
"""
import re

from scrapely.extractors import text as _text, htmlregion
from scrapely.htmlpage import HtmlPage, HtmlTag

def raw_to_text(txt):
    return _text(htmlregion(txt))

def _match_key(candidate, compiled_keys_map):
    if isinstance(candidate, basestring):
        for key, regex in compiled_keys_map.items():
            m = regex.search(candidate)
            if m:
                return key, m.groups()[0] if m.groups() else None
    return candidate, None

def sequential_parse(data, sections, encoding="utf-8", debug=False):
    """
    - sections keys are state ids. If a text (a regex), and matches the current data fragment, will switch to that state.
      If regex contains a group, extraction starts before the jump. using the group value as first extracted text.
      Otherwise extraction starts after the jump.
      numeric state ids are useful for avoiding unexpected matches (to ensure that state is reached only by manual jump)
    - section values are binary tuples. first element is the field name switched to by the state. Can be None in order to
      avoid any further extraction until state is changed.
    - second element is jump state id.
                * If None, conserves state until an automatic (text matching)
                  state switch is performed.
                * If 0, stops completelly the extraction and return whatever was extracted at moment.
                * If not exists among the defined states, stops extraction of the current item and starts a new one
                * Otherwise, will perform an immediate jump to the indicated
                  state after the first data was extracted for the current state.

    >>> data = u"<b>hello header<b>hello data<b><!--comment--><b>hello data 2<b>bye header<b>bye data<b>"
    >>> sections = {"hello header": ("hello_field", None)}
    >>> item = sequential_parse(data, sections)[0]
    >>> item.keys()
    ['hello_field']
    >>> item["hello_field"]
    [u'hello data', u'hello data 2', u'bye header', u'bye data']

    >>> sections = {"hello header": ("hello_field", None), "bye header": ("bye_field", None)}
    >>> item = sequential_parse(data, sections)[0]
    >>> sorted(item.keys())
    ['bye_field', 'hello_field']
    >>> item['bye_field']
    [u'bye data']
    >>> item['hello_field']
    [u'hello data', u'hello data 2']

    using a state id that can match text leads to unexpected results
    >>> sections = {"hello header": ("hello_field", "hello data 2"), "hello data 2":("hello_field_2", None), "bye header": ("bye_field", None)}
    >>> item = sequential_parse(data, sections)[0]
    >>> sorted(item.keys())
    ['bye_field', 'hello_field']
    >>> item['bye_field']
    [u'bye data']
    >>> item['hello_field']
    [u'hello data']

    but using number as state id, will avoid undesired matches
    >>> sections = {"hello header": ("hello_field", "1"), "1":("hello_field_2", None), "bye header": ("bye_field", None)}
    >>> item = sequential_parse(data, sections)[0]
    >>> sorted(item.keys())
    ['bye_field', 'hello_field', 'hello_field_2']
    >>> item['bye_field']
    [u'bye data']
    >>> item['hello_field']
    [u'hello data']
    >>> item['hello_field_2']
    [u'hello data 2']

    using a not existing state id as jump target will finish current subitem and create a new one after the first extraction
    >>> sections = {"hello header": ("hello_field", 1), "bye header": ("bye_field", None)}
    >>> item, item2 = sequential_parse(data, sections)
    >>> sorted(item.keys())
    ['hello_field']
    >>> item['hello_field']
    [u'hello data']
    >>> sorted(item2.keys())
    ['bye_field']
    >>> item2['bye_field']
    [u'bye data']

    another example:
    >>> sections = {"hello (header)": ("hello_field", 1), "bye header": ("bye_field", None)}
    >>> item, item2 = sequential_parse(data, sections)
    >>> sorted(item.keys())
    ['hello_field']
    >>> item['hello_field']
    [u'header']
    >>> sorted(item2.keys())
    ['bye_field']
    >>> item2['bye_field']
    [u'bye data']

    except if the jump is 0, when it will completelly stop extraction
    >>> sections = {"hello header": ("hello_field", 0), "bye header": ("bye_field", None)}
    >>> result = sequential_parse(data, sections)
    >>> len(result)
    1
    >>> item = result[0]
    >>> sorted(item.keys())
    ['hello_field']
    >>> item['hello_field']
    [u'hello data']

    or target field is None. In this case, creation of new item is immediate
    >>> sections = {"hello header": ("hello_field", None), "hello data 2": (None, 1), "bye header": ("bye_field", None)}
    >>> item, item2 = sequential_parse(data, sections)
    >>> sorted(item.keys())
    ['hello_field']
    >>> item['hello_field']
    [u'hello data']
    >>> sorted(item2.keys())
    ['bye_field']
    >>> item2['bye_field']
    [u'bye data']


    When a state with field name None is reached, extraction will be skipped until next state switch
    >>> sections = {"hello header": ("hello_field", None), "bye header": (None, None)}
    >>> item = sequential_parse(data, sections)[0]
    >>> item.keys()
    ['hello_field']
    >>> item["hello_field"]
    [u'hello data', u'hello data 2']
   
    The initial state is None, which by default is setted to (None, None), so will not start to extract nothing until
    first text match is found.
    >>> sections = {None: ("hello_field", None), "bye header": (None, None)}
    >>> item = sequential_parse(data, sections)[0]
    >>> item.keys()
    ['hello_field']
    >>> item["hello_field"]
    [u'hello header', u'hello data', u'hello data 2']

    Support of regex keys
    >>> sections = {"hello (header)": ("hello_field", None), "bye header": (None, None)}
    >>> item = sequential_parse(data, sections)[0]
    >>> item.keys()
    ['hello_field']
    >>> item["hello_field"]
    [u'header', u'hello data', u'hello data 2']

    >>> 
    """

    def _set_field(item, field, value):
        if not field in item:
            item[field] = []
        item[field].append(raw_to_text(value))

    page = HtmlPage(body=data, encoding=encoding)
    
    sections = sections.copy()
    if None not in sections:
        sections.update({None: (None, None)})

    compiled_keys = dict((k, re.compile(k, re.I)) for k in sections.keys() if isinstance(k, basestring))

    def _switch(jump):
        return sections[jump]

    subitems = []
    item_data = {}
    current_field, jump = _switch(None)
    for e in page.parsed_body:
        text = page.body[e.start:e.end].strip()
        if not isinstance(e, HtmlTag) and e.is_text_content and text:
            key, append = _match_key(text, compiled_keys)
            if key in sections:
                current_field, jump = _switch(key)
                if debug:
                    print "%s --> %s" % (key, jump)
                # print "'%s' '%s' '%s' '%s'" % (key, current_field, jump, append)
                if append:
                    _set_field(item_data, current_field, append)
                    if jump is not None:
                        jump, _ = _match_key(jump, compiled_keys)
                        if jump in sections:
                            current_field, jump = _switch(jump)
                        else:
                            if item_data:
                                subitems.append(item_data)
                            if jump == 0:
                                return subitems
                            item_data = {}
                            current_field, jump = _switch(None)
                elif current_field is None and jump not in sections:
                    if item_data:
                        subitems.append(item_data)
                    if jump == 0:
                        return subitems
                    item_data = {}
                    current_field, jump = _switch(None)

            elif current_field is not None:
                _set_field(item_data, current_field, text)
                if jump is not None:
                    jump, _ = _match_key(jump, compiled_keys)
                    if jump in sections:
                        current_field, jump = _switch(jump)
                    else:
                        if item_data:
                            subitems.append(item_data)
                        if jump == 0:
                            return subitems
                        item_data = {}
                        current_field, jump = _switch(None)
    else:
        if item_data:
            subitems.append(item_data)

    return subitems


