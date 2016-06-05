#!/usr/bin/env python

# The MIT License (MIT)
#
# Copyright (c) 2016 Francesco Martini
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from tkinter import *
from tkinter import ttk
from cssselect.xpath import SelectorError
from lxml import etree, cssselect
from collections import OrderedDict
import cssutils
import sys

# As from https://pythonhosted.org/cssselect/#supported-selectors
NEVER_MATCH = (":hover",
               ":active",
               ":focus",
               ":target",
               ":visited")

parameters = {}
orphaned_dict = OrderedDict()

class InfoDialog(Tk):
    """
    Dialog to show errors on css parsing and let the user decide if she
    wants to continue or stop the plugin.
    """

    global parameters
    parameters['stop'] = True

    def __init__(self):
        super().__init__()
        self.title('Some problem with css parsing...')
        self.resizable(width=TRUE, height=TRUE)
        self.geometry('+100+100')
        self.mainframe = ttk.Frame(self, padding="12 12 12 12") # padding values's order: "W N E S"
        self.mainframe.grid(column=0, row=0, sticky=(N,W,E,S))

        self.msg = StringVar()
        self.labelInfo = ttk.Label(self.mainframe,
                                   textvariable=self.msg)
        self.labelInfo.grid(row=0, column=0, sticky=(W,E), pady=5)

        ttk.Button(self.mainframe, text='Continue',
                   command=self.proceed).grid(row=1, column=1, sticky=E)
        ttk.Button(self.mainframe, text='Cancel',
                   command=self.quit).grid(row=1, column=2, sticky=E)

    def parseErrors(self, css_to_jump=None, css_to_parse=None):
        par_msg = ''
        if css_to_jump:
            for file, err in css_to_jump.items():
                par_msg += "I couldn't parse {} due to\n{}\n".format(file, err)
        if css_to_parse:
            files_to_parse = ", ".join(css_to_parse)
            par_msg += "\nParse will be done on {}".format(files_to_parse)
        self.msg.set(par_msg)

    def proceed(self):
        parameters['stop'] = False
        self.destroy()


class SelectorsDialog(Tk):
    """
    Dialog to show the list of css "orphaned" selectors (those without
    corresponding tags in xhtml files) and let the user choose the ones
    to delete.
    """
    global parameters, orphaned_dict
    parameters['stop'] = True

    def __init__(self, bk, orphaned_selectors=None):
        super().__init__()
        self.title('Remove unused Selectors')
        self.resizable(width=TRUE, height=TRUE)
        self.geometry('+100+100')
        self.mainframe = ttk.Frame(self, padding="12 12 12 12") # padding values's order: "W N E S"
        self.mainframe.grid(column=0, row=0, sticky=(N,W,E,S))

        if orphaned_selectors:
            self.scrollList = Scrollbar(self.mainframe, orient=VERTICAL)
            self.text = Text(self.mainframe, width=40, height=20,
                                yscrollcommand=self.scrollList.set)
            self.scrollList.grid(row=0, column=3, sticky=(N,E,S,W))
            self.scrollList['command'] = self.text.yview
            self.text.grid(row=0, column=0, columnspan=3, sticky=(W,E))

            for index, sel_tuple in enumerate(orphaned_selectors):
                css_filename = href_to_basename(bk.id_to_href(sel_tuple[0]))
                sel_and_css = sel_tuple[2].selectorText+" ({})".format(css_filename)
                sel_key = sel_tuple[2].selectorText+"_"+str(index)
                orphaned_dict[sel_key] = [sel_tuple, BooleanVar()]
                orphaned_dict[sel_key].append(ttk.Checkbutton(self.mainframe,
                                                              text=sel_and_css,
                                                              variable=orphaned_dict[sel_key][1],
                                                              onvalue=True, offvalue=False))
                self.text.window_create("end", window=orphaned_dict[sel_key][2])
                self.text.insert("end", "\n")
                orphaned_dict[sel_key][1].set(True)
            self.text.config(state=DISABLED)
        else:
            self.labelInfo = ttk.Label(self.mainframe,
                                       text="I didn't find any unused selector.")
            self.labelInfo.grid(row=0, column=0, sticky=(W,E), pady=5)

        ttk.Button(self.mainframe, text='Continue',
                   command=self.proceed).grid(row=len(orphaned_selectors) or 1, column=1, sticky=(W,E))
        ttk.Button(self.mainframe, text='Cancel',
                   command=self.quit).grid(row=len(orphaned_selectors) or 1, column=2, sticky=(W,E))

    def proceed(self):
        parameters['stop'] = False
        self.destroy()


def styleRules(css):
    """
    Yields all style rules in a css, both at top level and nested inside
    an @media rule (other nesting schemes are not supported).
    """
    for rule in css.cssRules:
        if rule.typeString == "STYLE_RULE":
            yield rule
        if rule.typeString == "MEDIA_RULE":
            for m_rule in rule.cssRules:
                if m_rule.typeString == "STYLE_RULE":
                    yield m_rule


def cssNamespaces(css):
    """
    Returns a dictionary of namespace rules in css.
    """
    namespaces = {}
    for rule in css.cssRules:
        if rule.typeString == "NAMESPACE_RULE":
            namespaces[rule.prefix] = rule.namespaceURI
    return namespaces


def selectorExists(parsed_xhtml, selector, namespaces_dict):
    """
    Converts selector's text in XPath and make a search in xhtml file.
    Returns True if it finds a correspondence or the translation of the
    selector to XPath is not yet implemented by cssselect, False otherwise.
    """
    try:
        if cssselect.CSSSelector(
                selector.selectorText,
                translator="xhtml",
                namespaces=namespaces_dict
                )(parsed_xhtml):
            return True
    except SelectorError:
        return True
    return False


def ignoreSelectors(selector_text):
    """
    Jump over the selectors that can't match anything
    (pseudo-classes like :hover and the like).
    """
    for pseudo_class in NEVER_MATCH:
        if pseudo_class in selector_text:
            return True
    return False


def preParseCss(bk, parser):
    """
    For safety reason, every exception raised during the css parsing
    will cause the css to be left untouched.
    """
    css_to_jump = {}
    css_to_parse = []
    for css_id, css_href in bk.css_iter():
        css_string = bk.readfile(css_id).decode()
        try:
            parser.parseString(css_string)
        except Exception as E: # cssutils.xml.dom.HierarchyRequestErr as E:
            css_to_jump[css_id] = E
        else:
            css_to_parse.append(css_id)
    return css_to_jump, css_to_parse


def setCssOutputPrefs():
    """
    As from https://pythonhosted.org/cssutils/docs/serialize.html
    TODO: a GUI to let the user choose
    """
    cssutils.ser.prefs.indent = 2 * ' '
    cssutils.ser.prefs.indentClosingBrace = False
    cssutils.ser.prefs.keepEmptyRules = True
    cssutils.ser.prefs.omitLastSemicolon = False


def href_to_basename(href, ow=None):
    """
    From the bookcontainer's API. There's a typo until Sigil 0.9.5.
    """
    if href is not None:
        return href.split('/')[-1]
    return ow


def run(bk):
    setCssOutputPrefs()
    parser = cssutils.CSSParser(raiseExceptions=True)
    css_to_jump, css_to_parse = preParseCss(bk, parser)

    if css_to_jump:
        form = InfoDialog()
        form.parseErrors(css_to_jump, css_to_parse)
        form.mainloop()
        if parameters['stop']:
            return -1

    # Parse files to create the list of "orphaned selectors"
    orphaned_selectors = []
    for css_id, css_href in bk.css_iter():
        if css_id not in css_to_jump.keys():
            css_string = bk.readfile(css_id).decode()
            parsed_css = parser.parseString(css_string)
            namespaces_dict = cssNamespaces(parsed_css)
            for rule in styleRules(parsed_css):
                for selector_index, selector in enumerate(rule.selectorList):
                    maintain_selector = False
                    if ignoreSelectors(selector.selectorText):
                        continue
                    for xhtml_id, xhtml_href in bk.text_iter():
                        xml_parser = etree.XMLParser(resolve_entities=False)
                        if selectorExists(etree.XML(bk.readfile(xhtml_id).encode('utf-8'),
                                                    xml_parser),
                                          selector, namespaces_dict):
                            maintain_selector = True
                            break
                        if selectorExists(etree.HTML(bk.readfile(xhtml_id).encode('utf-8')),
                                          selector, namespaces_dict):
                            maintain_selector = True
                            break
                    if not maintain_selector:
                        orphaned_selectors.append((css_id, rule,
                                                   rule.selectorList[selector_index],
                                                   selector_index,
                                                   parsed_css))

    # Show the list of selectors to the user.
    form = SelectorsDialog(bk, orphaned_selectors)
    form.mainloop()
    if parameters['stop']:
        return -1

    # Delete selectors chosen by the user.
    old_rule, counter = None, 0
    for x in orphaned_dict.values():
        if x[1].get() == 1:
            if x[0][1] == old_rule:
                counter += 1
            else:
                counter = 0
            del x[0][1].selectorList[x[0][3]-counter]
            old_rule = x[0][1]
            bk.writefile(x[0][0], x[0][4].cssText)
    return 0


def main():
    print("I reached main when I should not have\n")
    return -1


if __name__ == '__main__':
    sys.exit(main())
