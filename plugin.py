#!/usr/bin/env python
# -*- coding: utf-8 -*-


# Copyright (c) 2016 Francesco Martini
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from collections import OrderedDict
from tkinter import *
from tkinter import ttk
import sys
import re

from cssselect.xpath import SelectorError
from lxml import etree, cssselect
import cssutils

import customCssutils


# As from https://pythonhosted.org/cssselect/#supported-selectors
NEVER_MATCH = (":hover",
               ":active",
               ":focus",
               ":target",
               ":visited")


class PrefsDialog(object):
    """
    Dialog to set and save preferences about css formatting.
    """

    def __init__(self, parent=None, bk=None, prefs=None):
        if prefs:
            self.prefs = prefs
        else:
            self.prefs = get_prefs(bk)
        top = Toplevel(parent)
        top.title("Preferences")
        top.resizable(width=TRUE, height=TRUE)
        top.geometry('+100+100')
        top.columnconfigure(0, weight=1)
        top.rowconfigure(0, weight=1)
        top.mainframe = ttk.Frame(top, padding="12 12 12 12") # padding values's order: "W N E S"
        top.mainframe.grid(column=0, row=0, sticky=(N,W,E,S))

        self.indent = StringVar()
        top.labelIndent = ttk.Label(top.mainframe, text="Indent:")
        top.labelIndent.grid(row=0, column=0, sticky=(W,E))
        top.comboIndent = ttk.Combobox(top.mainframe, textvariable=self.indent,
                                       values=('No indentation', '1 space', '2 spaces',
                                               '3 spaces', '4 spaces', '1 tab'))
        top.comboIndent.grid(row=0, column=1, sticky=(W,E))
        top.comboIndent.state(['readonly'])

        self.indentLastBrace = BooleanVar()
        top.checkIndentLastBrace = ttk.Checkbutton(top.mainframe, text="Indent rules's last brace",
                                                   variable=self.indentLastBrace,
                                                   onvalue=True, offvalue=False)
        top.checkIndentLastBrace.grid(row=1, column=0, columnspan=5, sticky=W)

        self.keepEmptyRules = BooleanVar()
        top.checkKeepEmptyRules = ttk.Checkbutton(top.mainframe, text="Keep empty rules (e.g. "+\
                                                  "\"p { }\")", variable=self.keepEmptyRules,
                                                  onvalue=True, offvalue=False)
        top.checkKeepEmptyRules.grid(row=2, column=0, columnspan=5, sticky=W)

        self.omitSemicolon = BooleanVar()
        top.checkOmitSemicolon = ttk.Checkbutton(top.mainframe, text="Omit semicolon after rules's "+\
                                                 "last declaration (e.g. \"p { font-size: 1.2em; "+\
                                                 "text-indent: .5em }\")", variable=self.omitSemicolon,
                                                 onvalue=True, offvalue=False)
        top.checkOmitSemicolon.grid(row=3, column=0, columnspan=5, sticky=W)

        self.omitLeadingZero = BooleanVar()
        top.checkOmitZeroes = ttk.Checkbutton(top.mainframe, text="Omit leading zero (e.g. \".5em\" vs \"0.5em\")",
                                              variable=self.omitLeadingZero, onvalue=True,
                                              offvalue=False)
        top.checkOmitZeroes.grid(row=4, column=0, columnspan=5, sticky=W)

        self.formatUnknownRules = BooleanVar()
        top.checkFormatUnknown = ttk.Checkbutton(top.mainframe, text="Use settings to reformat css "+\
                                                 "inside not recognized @rules, too (not completely safe)",
                                                 variable=self.formatUnknownRules, onvalue=True,
                                                 offvalue=False)
        top.checkFormatUnknown.grid(row=5, column=0, columnspan=5, sticky=W)

        self.blankLinesAfterRules = BooleanVar()
        top.checkBlankLinesAfterRules = ttk.Checkbutton(top.mainframe, text="Add a blank line after every rule",
                                                        variable=self.blankLinesAfterRules, onvalue=True,
                                                        offvalue=False)
        top.checkBlankLinesAfterRules.grid(row=6, column=0, columnspan=5, sticky=W)

        self.get_initial_values(top)

        cont_button = ttk.Button(top.mainframe, text='Save and continue',
                   command=lambda: self.save_and_go(top, bk))
        cont_button.grid(row=7, column=3, sticky=E)
        canc_button = ttk.Button(top.mainframe, text='Cancel',
                   command=top.destroy)
        canc_button.grid(row=7, column=4, sticky=(W,E))
        cont_button.bind('<Return>', lambda event: self.save_and_go(top, bk))
        canc_button.bind('<Return>', lambda event: top.destroy())

        top.mainframe.columnconfigure(0, weight=0)
        top.mainframe.columnconfigure(1, weight=0)
        top.mainframe.columnconfigure(2, weight=1)
        top.mainframe.columnconfigure(3, weight=0)
        top.mainframe.columnconfigure(4, weight=0)
        cont_button.focus_set()
        
        top.grab_set()

    def get_initial_values(self, top):
        if self.prefs['indent'] == "\t":
            top.comboIndent.set('1 tab')
        else:
            top.comboIndent.current(newindex=len(self.prefs['indent']))
        if self.prefs['indentClosingBrace']:
            self.indentLastBrace.set(1)
        else:
            self.indentLastBrace.set(0)
        if self.prefs['keepEmptyRules']:
            self.keepEmptyRules.set(1)
        else:
            self.keepEmptyRules.set(0)
        if self.prefs['omitLastSemicolon']:
            self.omitSemicolon.set(1)
        else:
            self.omitSemicolon.set(0)
        if self.prefs['omitLeadingZero']:
            self.omitLeadingZero.set(1)
        else:
            self.omitLeadingZero.set(0)
        if self.prefs['formatUnknownRules']:
            self.formatUnknownRules.set(1)
        else:
            self.formatUnknownRules.set(0)
        if self.prefs['blankLinesAfterRules']:
            self.blankLinesAfterRules.set(1)
        else:
            self.blankLinesAfterRules.set(0)

    def save_and_go(self, top, bk):
        if self.indent.get() == '1 tab':
            self.prefs['indent'] = '\t'
        else:
            self.prefs['indent'] = top.comboIndent.current() * ' '
        self.prefs['indentClosingBrace'] = True \
                if self.indentLastBrace.get() == 1 \
                else False
        self.prefs['keepEmptyRules'] = True \
                if self.keepEmptyRules.get() == 1 \
                else False
        self.prefs['omitLastSemicolon'] = True \
                if self.omitSemicolon.get() == 1 \
                else False
        self.prefs['omitLeadingZero'] = True \
                if self.omitLeadingZero.get() == 1 \
                else False
        self.prefs['formatUnknownRules'] = True \
                if self.formatUnknownRules.get() == 1 \
                else False
        self.prefs['blankLinesAfterRules'] = 1 * '\n' \
                if self.blankLinesAfterRules.get() == 1 \
                else 0 * '\n'
        set_css_output_prefs(bk, self.prefs)
        top.destroy()


class InfoDialog(Tk):
    """
    Dialog to show errors on css parsing and let the user decide if she
    wants to continue or stop the plugin.
    """

    stop_plugin = True

    def __init__(self, bk, prefs):
        super().__init__()
        style = ttk.Style()
        style.configure('myCheckbutton.TCheckbutton', padding="0 0 0 5")
        self.title('Preparing to parse...')
        self.resizable(width=TRUE, height=TRUE)
        self.geometry('+100+100')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.mainframe = ttk.Frame(self, padding="12 12 12 12")  # padding values's order: "W N E S"
        self.mainframe.grid(column=0, row=0, sticky=(N,W,E,S))

        self.msg = StringVar()
        self.labelInfo = ttk.Label(self.mainframe,
                                   textvariable=self.msg, wraplength=600)
        self.labelInfo.grid(row=0, column=0, columnspan=4, sticky=(W,E), pady=5)

        self.parseAllXMLFiles = BooleanVar()
        self.checkParseAllXMLFiles = ttk.Checkbutton(self.mainframe,
                                                     text='Parse every xml file, not only xhtml.',
                                                     variable=self.parseAllXMLFiles,
                                                     onvalue=True,
                                                     offvalue=False,
                                                     style="myCheckbutton.TCheckbutton")
        self.checkParseAllXMLFiles.grid(row=1, column=0, columnspan=4, sticky=(W,E))
        
        pref_button = ttk.Button(self.mainframe, text='Set preferences',
                                 command=lambda: self.prefs_dlg(bk, prefs))
        pref_button.grid(row=2, column=0, sticky=(W,E))
        cont_button = ttk.Button(self.mainframe, text='Continue',
                                 command=lambda: self.proceed(bk, prefs))
        cont_button.grid(row=2, column=2, sticky=(W,E))
        canc_button = ttk.Button(self.mainframe, text='Cancel', command=self.quit)
        canc_button.grid(row=2, column=3, sticky=(W,E))
        pref_button.bind('<Return>', lambda event: self.prefs_dlg(bk, prefs))
        cont_button.bind('<Return>', lambda event: self.proceed(bk, prefs))
        canc_button.bind('<Return>', lambda event: self.quit())

        self.mainframe.columnconfigure(0, weight=0)
        self.mainframe.columnconfigure(1, weight=1)
        self.mainframe.columnconfigure(2, weight=0)
        self.mainframe.columnconfigure(3, weight=0)
        cont_button.focus_set()

        self.get_initial_values(prefs)

    def parse_errors(self, bk, css_to_skip=None, css_to_parse=None, css_warnings=None):
        par_msg = ""
        if css_to_skip:
            for file_, err in css_to_skip.items():
                filename = href_to_basename(bk.id_to_href(file_))
                par_msg += "I couldn't parse {} due to\n{}\n\n".format(filename, err)
        if css_warnings:
            for file_, warn in css_warnings.items():
                filename = href_to_basename(bk.id_to_href(file_))
                par_msg += ("Warning: Found unknown @rule in {} at line {}: {}. "
                            "Text of unknown rules might not be preserved.\n\n".format(
                                                    filename, warn[1], warn[0]))
        if css_to_parse:
            files_to_parse = ", ".join(css_to_parse)
            par_msg += "Analysis will be done on {}".format(files_to_parse)
        if not par_msg:
            par_msg = "No css found."
        self.msg.set(par_msg)

    def prefs_dlg(self, bk, prefs):
        self.set_pref = PrefsDialog(self, bk, prefs)

    def get_initial_values(self, prefs):
        if prefs['parseAllXMLFiles']:
            self.parseAllXMLFiles.set(1)
        else:
            self.parseAllXMLFiles.set(0)

    def proceed(self, bk, prefs):
        if self.parseAllXMLFiles.get() == 1:
            prefs['parseAllXMLFiles'] = True
        else:
            prefs['parseAllXMLFiles'] = False
        try:
            self.set_pref
        except AttributeError:
            set_css_output_prefs(bk, prefs, False)
        bk.savePrefs(prefs)
        InfoDialog.stop_plugin = False
        self.destroy()


class SelectorsDialog(Tk):
    """
    Dialog to show the list of css "orphaned" selectors (those without
    corresponding tags in xhtml files) and let the user choose the ones
    to delete.
    """
    
    orphaned_dict = OrderedDict()
    stop_plugin = True

    def __init__(self, bk, orphaned_selectors=None):
        super().__init__()
        style = ttk.Style()
        style.configure('TCheckbutton', background='white', wraplength=300)
        self.title('Remove unused Selectors')
        self.resizable(width=TRUE, height=TRUE)
        self.geometry('360x420+100+100')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.mainframe = ttk.Frame(self, padding="12 12 12 12") # padding values's order: "W N E S"
        self.mainframe.grid(column=0, row=0, sticky=(N,W,E,S))
        self.mainframe.bind('<Configure>',
                            lambda event: self.update_wraplength(event, style))
        self.upperframe = ttk.Frame(self.mainframe, padding="0 0 0 4")
        self.upperframe.grid(column=0, row=0, sticky=(N,W,E,S))
        self.lowerframe = ttk.Frame(self.mainframe, padding="4 0 0 0")
        self.lowerframe.grid(column=0, row=1, sticky=(N,W,E,S))

        if orphaned_selectors:
            self.scrollList = Scrollbar(self.upperframe, orient=VERTICAL)
            self.text = Text(self.upperframe, yscrollcommand=self.scrollList.set) # width=40, height=20,
            self.scrollList.grid(row=0, column=3, sticky=(N,E,S,W))
            self.scrollList['command'] = self.text.yview
            self.text.grid(row=0, column=0, columnspan=3, sticky=(N,S,W,E))

            orphaned = SelectorsDialog.orphaned_dict

            self.toggleAll = BooleanVar()
            self.toggleAllStr = StringVar()
            self.toggleAllStr.set('Unselect all')
            self.checkToggleAll = ttk.Checkbutton(self.upperframe,
                                                  textvariable=self.toggleAllStr,
                                                  variable=self.toggleAll,
                                                  onvalue=True, offvalue=False,
                                                  command=self.toggle_all)
            self.text.window_create('end', window=self.checkToggleAll)
            self.text.insert('end', '\n\n')
            self.toggleAll.set(True)

            self.toggle_selectors_list = []
            for index, selector_tuple in enumerate(orphaned_selectors):
                css_filename = href_to_basename(bk.id_to_href(selector_tuple[0]))
                sel_and_css = '{} ({})'.format(selector_tuple[2].selectorText, css_filename)
                selector_key = selector_tuple[2].selectorText+"_"+str(index)
                orphaned[selector_key] = [selector_tuple, BooleanVar()]
                sel_checkbutton = ttk.Checkbutton(self.upperframe,
                                                  text=sel_and_css,
                                                  variable=orphaned[selector_key][1],
                                                  onvalue=True, offvalue=False)
                self.text.window_create('end', window=sel_checkbutton)
                self.text.insert('end', '\n')
                orphaned[selector_key][1].set(True)
                self.toggle_selectors_list.append(orphaned[selector_key][1])
            self.text.config(state=DISABLED)
        else:
            self.labelInfo = ttk.Label(self.upperframe,
                                       text="I didn't find any unused selector.")
            self.labelInfo.grid(row=0, column=0, sticky=(W,E), pady=5)

        cont_button = ttk.Button(self.lowerframe,
                                 text='Continue',
                                 command=self.proceed)
        cont_button.grid(row=0, column=1, sticky=(W,E))
        canc_button = ttk.Button(self.lowerframe,
                                 text='Cancel',
                                 command=self.quit)
        canc_button.grid(row=0, column=2, sticky=(W,E))
        cont_button.bind('<Return>', lambda event: self.proceed())
        canc_button.bind('<Return>', lambda event: self.quit())

        self.mainframe.columnconfigure(0, weight=1)
        self.mainframe.rowconfigure(0, weight=1)
        self.upperframe.columnconfigure(0, weight=1)
        self.upperframe.rowconfigure(0, weight=1)
        self.lowerframe.columnconfigure(0, weight=1)
        self.lowerframe.rowconfigure(0, weight=0)
        cont_button.focus_set()

    def proceed(self):
        SelectorsDialog.stop_plugin = False
        self.destroy()

    def toggle_all(self):
        if self.toggleAll.get() == 1:
            self.toggleAllStr.set('Unselect all')
            for toggle_var in self.toggle_selectors_list:
                toggle_var.set(1)
        else:
            self.toggleAllStr.set('Select all')
            for toggle_var in self.toggle_selectors_list:
                toggle_var.set(0)

    @staticmethod
    def update_wraplength(event, style):
        style.configure('TCheckbutton', wraplength=event.width-60)


# Sigil 0.9.7 broke compatibility in reading css and js files.
def read_css(bk, css):
    try:
        return bk.readfile(css).decode()
    except AttributeError:
        return bk.readfile(css)


def style_rules(rules_collector):
    """
    Yields style rules in a css, both at top level and nested inside
    @media rules (unlimited nesting levels: sooner or later cssutils
    will support it).
    """
    for rule in rules_collector:
        if rule.typeString == "STYLE_RULE":
            yield rule
        elif rule.typeString == "MEDIA_RULE":
            for nested_rule in style_rules(rule):
                yield nested_rule


def css_namespaces(css):
    """
    Returns a dictionary of namespace rules in css.
    If there is a default/unprefixed namespace (which isn't
    translatable to XPath), adds an arbitrary prefix to it.
    """
    namespaces = dict(css.namespaces)
    default_prefix = ""
    if namespaces.get("", None):
        while True:
            default_prefix += "a"
            try:
                namespaces[default_prefix]
            except KeyError:
                namespaces[default_prefix] = namespaces[""]
                break
        namespaces.pop("")
    return namespaces, default_prefix


def selector_exists(parsed_code, selector, namespaces_dict, is_xhtml):
    """
    Converts selector's text to XPath and make a search in xhtml file.
    Returns True if it finds a correspondence or the translation of the
    selector to XPath is not yet implemented by cssselect, False otherwise.
    """

    translator = 'xhtml' if is_xhtml else 'xml'
    try:
        if cssselect.CSSSelector(
                selector,
                translator=translator,
                namespaces=namespaces_dict
                )(parsed_code):
            return True
    except SelectorError:
        return True
    return False


def ignore_selectors(selector_text):
    """
    Skip the selectors that can't match anything
    (pseudo-classes like :hover and the like).
    """
    for pseudo_class in NEVER_MATCH:
        if pseudo_class in selector_text:
            return True
    return False


def add_default_prefix(prefix, selector_text):
    """
    Adds prefix to all unprefixed type selector tokens (tag names)
    in selector_text. Returns prefixed selector.
    """
    # Note: regex here are valid thanks to cssutils's normalization
    # of selectors text (e.g. optional whitespace after escape sequences
    # is removed).
    selector_ns = ''
    # https://www.w3.org/TR/css-syntax-3/#input-preprocessing
    # states that \r, \f and \r\n  must be replaced by \n
    # before tokenization.
    for token in re.split(r'(?<!\\)([ \n\t])', selector_text):
        if (re.match(r'-?(?:[A-Za-z_]|\\[^\n]|[^\u0000-\u007F])', token)
                and not re.search(r'(?<!\\)\|', token)):
            selector_ns += '{}|{}'.format(prefix, token)
        else:
            selector_ns += token
    return selector_ns


def clean_generic_prefixes(selector_text):
    """
    Removes '|' (no namespace) and '*|' (every namespace)
    at the beginning of type and attribute selector tokens.
    If there is at least one '*|' in selector_text, all prefixes
    will be deleted from the selector. This isn't the formally
    correct solution, but it's safe to use in combination with
    html parser which is namespace agnostic.
    """
    # Note: regex here are valid thanks to cssutils's normalization
    # of selectors text (e.g. optional whitespace between
    # '[' and qualified name of the attribute is removed).
    selector = ''
    if re.search(r'(?<!\\)(?:^| )\*\|', selector_text):
        for token in re.split(r'(?<!\\)([ \n\t]|\[)', selector_text):
            selector += re.sub(r'^.*?\|', '', token)
    else:
        for token in re.split(r'(?<!\\)([ \n\t]|\[)', selector_text):
            selector += re.sub(r'^\|', '', token)
    return selector


def pre_parse_css(bk, parser):
    """
    For safety reason, every exception raised during css parsing
    will cause the css to be left untouched.
    """
    css_to_skip = {}
    css_warnings = {}
    css_to_parse = []
    for css_id, css_href in bk.css_iter():
        css_string = read_css(bk, css_id)
        try:
            parsed = parser.parseString(css_string)
        except Exception as E: # cssutils.xml.dom.HierarchyRequestErr as E:
            css_to_skip[css_id] = E
        else:
            # 0 means UNKNOWN_RULE, as from cssutils.css.cssrule.CSSRule
            for unknown_rule in parsed.cssRules.rulesOfType(0):
                line = css_string[:css_string.find(unknown_rule.atkeyword)].count('\n')+1
                css_warnings[css_id] = (unknown_rule.atkeyword, line)
                break
            css_to_parse.append(css_id)
    return css_to_skip, css_to_parse, css_warnings


def set_css_output_prefs(bk, prefs, save_on_file=True):
    """
    As from https://pythonhosted.org/cssutils/docs/serialize.html
    """
    cssutils.ser.prefs.indent = prefs['indent']
    cssutils.ser.prefs.indentClosingBrace = prefs['indentClosingBrace']
    cssutils.ser.prefs.keepEmptyRules = prefs['keepEmptyRules']
    cssutils.ser.prefs.omitLastSemicolon = prefs['omitLastSemicolon']
    cssutils.ser.prefs.omitLeadingZero = prefs['omitLeadingZero']

    # custom prefs, not in cssutils
    cssutils.ser.prefs.blankLinesAfterRules = prefs['blankLinesAfterRules']
    cssutils.ser.prefs.formatUnknownRules = prefs['formatUnknownRules']

    if save_on_file:
        bk.savePrefs(prefs)


def get_prefs(bk):
    prefs = bk.getPrefs()

    # CSS output prefs
    prefs.defaults['indent'] = "\t"  # 2 * ' '
    prefs.defaults['indentClosingBrace'] = False
    prefs.defaults['keepEmptyRules'] = True
    prefs.defaults['omitLastSemicolon'] = False
    prefs.defaults['omitLeadingZero'] = False
    prefs.defaults['blankLinesAfterRules'] = 1 * '\n'
    prefs.defaults['formatUnknownRules'] = False

    # Other prefs
    prefs.defaults['parseAllXMLFiles'] = True

    return prefs


def href_to_basename(href, ow=None):
    """
    From the bookcontainer's API. There's a typo until Sigil 0.9.5.
    """
    if href is not None:
        return href.split('/')[-1]
    return ow


def run(bk):
    cssutils.setSerializer(customCssutils.MyCSSSerializer())
    prefs = get_prefs(bk)
    xml_parser = etree.XMLParser(resolve_entities=False)
    css_parser = cssutils.CSSParser(raiseExceptions=True, validate=False)
    css_to_skip, css_to_parse, css_warnings = pre_parse_css(bk, css_parser)

    form = InfoDialog(bk, prefs)
    form.parse_errors(bk, css_to_skip, css_to_parse, css_warnings)
    form.mainloop()
    if InfoDialog.stop_plugin:
        return -1

    parseAllXMLFiles = prefs['parseAllXMLFiles']

    # Parse files to create the list of "orphaned selectors"
    orphaned_selectors = []
    for css_id, css_href in bk.css_iter():
        if css_id not in css_to_skip.keys():
            css_string = read_css(bk, css_id)
            parsed_css = css_parser.parseString(css_string)
            namespaces_dict, default_prefix = css_namespaces(parsed_css)
            for rule in style_rules(parsed_css):
                for selector_index, selector in enumerate(rule.selectorList):
                    maintain_selector = False
                    if ignore_selectors(selector.selectorText):
                        continue
                    # If css specifies a default namespace, the default prefix
                    # must be added to every unprefixed type selector.
                    if default_prefix:
                        selector_ns = add_default_prefix(default_prefix,
                                                         selector.selectorText)
                    else:
                        selector_ns = selector.selectorText
                    selector_ns = clean_generic_prefixes(selector_ns)
                    for file_id, href, mime in bk.manifest_iter():
                        if mime == 'application/xhtml+xml':
                            is_xhtml = True
                        elif parseAllXMLFiles and re.search(r'[/+]xml\b', mime):
                            is_xhtml = False
                        else:
                            continue
                        if selector_exists(etree.HTML(bk.readfile(file_id).encode('utf-8')),
                                           selector_ns, namespaces_dict, is_xhtml):
                            maintain_selector = True
                            break
                        if selector_exists(etree.XML(bk.readfile(file_id).encode('utf-8'),
                                                     xml_parser),
                                           selector_ns, namespaces_dict, is_xhtml):
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
    if SelectorsDialog.stop_plugin:
        return -1

    # Delete selectors chosen by the user.
    css_to_change = {}
    old_rule, counter = None, 0
    for sel_data, to_delete in SelectorsDialog.orphaned_dict.values():
        if to_delete.get() == 1:
            if sel_data[1] == old_rule:
                counter += 1
            else:
                counter = 0
            del sel_data[1].selectorList[sel_data[3]-counter]
            old_rule = sel_data[1]
            css_to_change[sel_data[0]] = sel_data[4].cssText
    for css_id, css_text in css_to_change.items():
        bk.writefile(css_id, css_text)
    return 0


def main():
    print("I reached main when I should not have\n")
    return -1


if __name__ == '__main__':
    sys.exit(main())
