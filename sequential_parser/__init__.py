"""
Sequential html text parser
Allow to extract html structured text using text patterns and a state machine.

Source: https://github.com/kalessin/sequential-parser

"""
from __future__ import print_function

__version__ = '0.2'

import re

from scrapely.extractors import text as _text, htmlregion
from scrapely.htmlpage import HtmlPage, HtmlTag

def raw_to_text(txt):
    return _text(htmlregion(txt))

def _match_state(text, compiled_keys_map):
    """
    Check whether the given text matches some of the state ids
    Returns back the complete text, and the substring to be appended to data extracted
    """
    if isinstance(text, basestring):
        for key, regex in compiled_keys_map.items():
            m = regex.search(text)
            if m:
                return key, m.groups()[0] if m.groups() else None
    return text, None

def sequential_parse(data, sections, tag_callback=None, encoding="utf-8", re_flags=0, debug=False):
    """
    - sections keys are state ids. If a text (a regex), and matches the current data fragment, will switch to that state.
      If regex contains a group, extraction starts before the jump. using the group value as first extracted text.
      Otherwise extraction starts after the jump.
      numeric state ids are useful for avoiding unexpected matches (to ensure that state is reached only by target from another state)
    - sections values are binary tuples. first element is the field name switched to by the state. Can be None in order to
      avoid any further extraction until next state change.
    - second element is target state id.
                * If None, conserves state until an automatic (text matching)
                  state switch is performed.
                * If 0, stops completelly the extraction and return whatever was extracted at moment.
                * If not exists among the defined states, stops extraction of the current item and starts a new one
                * Otherwise, will perform an immediate jump to the indicated
                  state after the first data was extracted for the current state.

    - tag_callback - a function which receives as argument an scrapely.htmlpage.HtmlTag instance and the current item_data, and returns a tuple
      (field_name, target), in the same fashion as sections values are defined. This function, in case of being passed, allow to set machine
      state as function of tag elements being found in the source. If returns None, no state change is performed. It also allows to fill the
      current item with extra data.

    - re_flags - flags passed to regular expression compiler

    >>> data = u"<b>hello header<b>hello data<b><!--comment--><p alt='altdata'>hello data 2<br>bye header<b>bye data<b>"
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

    and if a state with field name None is reached, extraction will be skipped until next state switch
    >>> sections = {"hello header": (None, "1"), "1":("hello_field_2", None), "bye header": ("bye_field", None)}
    >>> item = sequential_parse(data, sections)[0]
    >>> sorted(item.keys())
    ['bye_field', 'hello_field_2']
    >>> item['bye_field']
    [u'bye data']
    >>> item['hello_field_2']
    [u'hello data 2']

    A simple example with field name None
    >>> sections = {"hello header": ("hello_field", None), "bye header": (None, None)}
    >>> item = sequential_parse(data, sections)[0]
    >>> item.keys()
    ['hello_field']
    >>> item["hello_field"]
    [u'hello data', u'hello data 2']

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

    or target field is None. In this case, creation of new item is immediate (because target state does not exist)
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

    The initial state is None, which by default is setted to (None, None), so will not start to extract nothing until
    first text match is found. This default behavior can be overriden by adding an explicit None state.
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

    We can instruct the state machine to change state according to tags being found, using tag_callback argument. Example:
    >>> sections = {"hello header": ("hello_field", None), "bye header": ("bye_field", None)}
    
    >>> item = sequential_parse(data, sections, lambda e, _: (None, None) if e.tag == 'p' else None)[0]
    >>> sorted(item.keys())
    ['bye_field', 'hello_field']
    >>> item['bye_field']
    [u'bye data']
    >>> item['hello_field']
    [u'hello data']

    Another example:
    >>> items = sequential_parse(data, sections, lambda e, _: (None, 1) if e.tag == 'br' else None)
    >>> items[0].keys()
    ['hello_field']
    >>> items[0]['hello_field']
    [u'hello data', u'hello data 2']
    >>> items[1].keys()
    ['bye_field']
    >>> items[1]['bye_field']
    [u'bye data']

    Or we can also use tag_callback function to append data to the current item data:
    >>> def tag_callback(element, data):
    ...     if element.tag == 'p':
    ...         if 'alt' in element.attributes:
    ...             data['extrafield'] = [element.attributes['alt']]
    ...         return None, None
    >>> item = sequential_parse(data, sections, tag_callback)[0]
    >>> sorted(item.keys())
    ['bye_field', 'extrafield', 'hello_field']
    >>> item['bye_field']
    [u'bye data']
    >>> item['hello_field']
    [u'hello data']
    >>> item['extrafield']
    [u'altdata']

    """

    def _set_field(item, field, value):
        if not field in item:
            item[field] = []
        item[field].append(raw_to_text(value))

    page = HtmlPage(body=data, encoding=encoding)
    
    sections = sections.copy()
    if None not in sections:
        sections.update({None: (None, None)})

    compiled_keys = dict((k, re.compile(k, re_flags)) for k in sections.keys() if isinstance(k, basestring))

    def _switch(jump):
        return sections[jump]

    subitems = []
    item_data = {}
    current_field, jump = _switch(None)

    def _new_item(item_data, current_field, jump):
        if item_data:
            subitems.append(item_data)
        item_data = {}
        if jump == 0:
            return True, item_data, current_field, jump
        current_field, jump = _switch(None)
        return False, item_data, current_field, jump

    for e in page.parsed_body:
        text = page.body[e.start:e.end].strip()
        if isinstance(e, HtmlTag):
            if tag_callback is not None:
                result = tag_callback(e, item_data)
                if result is not None:
                    current_field, jump = result
                if jump not in sections:
                    ret, item_data, current_field, jump = _new_item(item_data, current_field, jump)
                    if ret:
                        return subitems
        elif e.is_text_content and text:
            key, append = _match_state(text, compiled_keys)
            if key in sections:
                current_field, jump = _switch(key)
                if debug:
                    print("%s --> %s (%s)" % (key, jump, current_field))
                if append:
                    _set_field(item_data, current_field, append)
                    if jump is not None:
                        jump, _ = _match_state(jump, compiled_keys)
                        if jump in sections:
                            current_field, jump = _switch(jump)
                        else:
                            ret, item_data, current_field, jump = _new_item(item_data, current_field, jump)
                            if ret:
                                return subitems
                elif current_field is None and jump not in sections:
                    ret, item_data, current_field, jump = _new_item(item_data, current_field, jump)
                    if ret:
                        return subitems

            elif current_field is not None:
                _set_field(item_data, current_field, text)
                if jump is not None:
                    jump, _ = _match_state(jump, compiled_keys)
                    if jump in sections:
                        current_field, jump = _switch(jump)
                    else:
                        ret, item_data, current_field, jump = _new_item(item_data, current_field, jump)
                        if ret:
                            return subitems
            else:
                current_field, jump = _switch(jump)

    else:
        if item_data:
            subitems.append(item_data)

    return subitems


