#!/usr/bin/env python
# -*- coding: utf-8 -*-


# Copyright (c) 2016, 2019, 2020 Francesco Martini
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


import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as msgbox
from collections import OrderedDict
import inspect
import sys
import os
import regex as re

from cssselect.xpath import SelectorError
from lxml import etree, cssselect
import cssutils

import customcssutils


SCRIPT_DIR = os.path.normpath(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))


# As from https://pythonhosted.org/cssselect/#supported-selectors
NEVER_MATCH = (":hover",
               ":active",
               ":focus",
               ":target",
               ":visited")


class PrefsDialog(tk.Toplevel):
    """
    Dialog to set and save preferences about css formatting.
    """

    def __init__(self, parent=None, bk=None, prefs=None):
        if prefs:
            self.prefs = prefs
        else:
            self.prefs = get_prefs(bk)
        super().__init__(parent)
        self.transient(parent)
        self.title("Preferences")
        self.resizable(width=tk.TRUE, height=tk.TRUE)
        self.geometry('+100+100')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.mainframe = ttk.Frame(self, padding="12 12 12 12") # padding values's order: "W N E S"
        self.mainframe.grid(column=0, row=0, sticky="nwes")

        self.indent = tk.StringVar()
        self.labelIndent = ttk.Label(self.mainframe, text="Indent:")
        self.labelIndent.grid(row=0, column=0, sticky="we")
        self.comboIndent = ttk.Combobox(self.mainframe, textvariable=self.indent,
                                       values=('No indentation', '1 space', '2 spaces',
                                               '3 spaces', '4 spaces', '1 tab'))
        self.comboIndent.grid(row=0, column=1, sticky="we")
        self.comboIndent.state(['readonly'])

        self.indentLastBrace = tk.BooleanVar()
        self.checkIndentLastBrace = ttk.Checkbutton(self.mainframe, text="Indent rules's last brace",
                                                   variable=self.indentLastBrace,
                                                   onvalue=True, offvalue=False)
        self.checkIndentLastBrace.grid(row=1, column=0, columnspan=5, sticky=tk.W)

        self.keepEmptyRules = tk.BooleanVar()
        self.checkKeepEmptyRules = ttk.Checkbutton(self.mainframe, text="Keep empty rules (e.g. "+\
                                                  "\"p { }\")", variable=self.keepEmptyRules,
                                                  onvalue=True, offvalue=False)
        self.checkKeepEmptyRules.grid(row=2, column=0, columnspan=5, sticky=tk.W)

        self.omitSemicolon = tk.BooleanVar()
        self.checkOmitSemicolon = ttk.Checkbutton(self.mainframe, text="Omit semicolon after rules's "+\
                                                 "last declaration (e.g. \"p { font-size: 1.2em; "+\
                                                 "text-indent: .5em }\")", variable=self.omitSemicolon,
                                                 onvalue=True, offvalue=False)
        self.checkOmitSemicolon.grid(row=3, column=0, columnspan=5, sticky=tk.W)

        self.omitLeadingZero = tk.BooleanVar()
        self.checkOmitZeroes = ttk.Checkbutton(self.mainframe, text="Omit leading zero (e.g. \".5em\" vs \"0.5em\")",
                                              variable=self.omitLeadingZero, onvalue=True,
                                              offvalue=False)
        self.checkOmitZeroes.grid(row=4, column=0, columnspan=5, sticky=tk.W)

        self.formatUnknownAtRules = tk.BooleanVar()
        self.checkFormatUnknown = ttk.Checkbutton(self.mainframe, text="Use settings to reformat css "+\
                                                 "inside not recognized @rules, too (not completely safe)",
                                                 variable=self.formatUnknownAtRules, onvalue=True,
                                                 offvalue=False)
        self.checkFormatUnknown.grid(row=5, column=0, columnspan=5, sticky=tk.W)

        self.linesAfterRules = tk.BooleanVar()
        self.checkLinesAfterRules = ttk.Checkbutton(self.mainframe, text="Add a blank line after every rule",
                                                        variable=self.linesAfterRules, onvalue=True,
                                                        offvalue=False)
        self.checkLinesAfterRules.grid(row=6, column=0, columnspan=5, sticky=tk.W)

        self.get_initial_values()

        cont_button = ttk.Button(self.mainframe, text='Save and continue',
                   command=lambda: self.save_and_go(bk))
        cont_button.grid(row=7, column=3, sticky=tk.E)
        canc_button = ttk.Button(self.mainframe, text='Cancel',
                   command=self.destroy)
        canc_button.grid(row=7, column=4, sticky="we")
        cont_button.bind('<Return>', lambda event: self.save_and_go(bk))
        cont_button.bind('<KP_Enter>', lambda event: self.save_and_go(bk))
        canc_button.bind('<Return>', lambda event: self.destroy())
        canc_button.bind('<KP_Enter>', lambda event: self.destroy())

        self.mainframe.columnconfigure(0, weight=0)
        self.mainframe.columnconfigure(1, weight=0)
        self.mainframe.columnconfigure(2, weight=1)
        self.mainframe.columnconfigure(3, weight=0)
        self.mainframe.columnconfigure(4, weight=0)
        cont_button.focus_set()
        
        self.grab_set()

    def get_initial_values(self):
        if self.prefs['indent'] == "\t":
            self.comboIndent.set('1 tab')
        else:
            self.comboIndent.current(newindex=len(self.prefs['indent']))
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
        if self.prefs['formatUnknownAtRules']:
            self.formatUnknownAtRules.set(1)
        else:
            self.formatUnknownAtRules.set(0)
        if self.prefs['linesAfterRules']:
            self.linesAfterRules.set(1)
        else:
            self.linesAfterRules.set(0)

    def save_and_go(self, bk):
        if self.indent.get() == '1 tab':
            self.prefs['indent'] = '\t'
        else:
            self.prefs['indent'] = self.comboIndent.current() * ' '
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
        self.prefs['formatUnknownAtRules'] = True \
                if self.formatUnknownAtRules.get() == 1 \
                else False
        self.prefs['linesAfterRules'] = 1 * '\n' \
                if self.linesAfterRules.get() == 1 \
                else 0 * '\n'
        self.destroy()


class InfoDialog(tk.Tk):
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
        self.resizable(width=tk.TRUE, height=tk.TRUE)
        self.geometry('+100+100')
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        try:
            icon = tk.PhotoImage(file=os.path.join(SCRIPT_DIR, 'plugin.png'))
            self.iconphoto(True, icon)
        except Exception:
            pass
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.mainframe = ttk.Frame(self, padding="12 12 12 12")  # padding values's order: "W N E S"
        self.mainframe.grid(column=0, row=0, sticky="nwes")

        self.msg = tk.StringVar()
        self.labelInfo = ttk.Label(self.mainframe,
                                   textvariable=self.msg, wraplength=600)
        self.labelInfo.grid(row=0, column=0, columnspan=4, sticky="we", pady=5)

        self.parseAllXMLFiles = tk.BooleanVar()
        self.checkParseAllXMLFiles = ttk.Checkbutton(self.mainframe,
                                                     text='Parse every xml file, not only xhtml.',
                                                     variable=self.parseAllXMLFiles,
                                                     onvalue=True,
                                                     offvalue=False,
                                                     style="myCheckbutton.TCheckbutton")
        self.checkParseAllXMLFiles.grid(row=1, column=0, columnspan=4, sticky="we")
        
        pref_button = ttk.Button(self.mainframe, text='Set preferences',
                                 command=lambda: self.prefs_dlg(bk, prefs))
        pref_button.grid(row=2, column=0, sticky="we")
        cont_button = ttk.Button(self.mainframe, text='Continue',
                                 command=lambda: self.proceed(bk, prefs))
        cont_button.grid(row=2, column=2, sticky="we")
        canc_button = ttk.Button(self.mainframe, text='Cancel', command=self.quit)
        canc_button.grid(row=2, column=3, sticky="we")
        pref_button.bind('<Return>', lambda event: self.prefs_dlg(bk, prefs))
        pref_button.bind('<KP_Enter>', lambda event: self.prefs_dlg(bk, prefs))
        cont_button.bind('<Return>', lambda event: self.proceed(bk, prefs))
        cont_button.bind('<KP_Enter>', lambda event: self.proceed(bk, prefs))
        canc_button.bind('<Return>', lambda event: self.quit())
        canc_button.bind('<KP_Enter>', lambda event: self.quit())

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
        PrefsDialog(self, bk, prefs)

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
        set_css_output_prefs(bk, prefs)
        bk.savePrefs(prefs)
        InfoDialog.stop_plugin = False
        self.destroy()


class SelectorsDialog(tk.Tk):
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
        style.configure('TCheckbutton', background='white', wraplength=290)
        self.title('Remove unused Selectors')
        self.resizable(width=tk.TRUE, height=tk.TRUE)
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        try:
            icon = tk.PhotoImage(file=os.path.join(SCRIPT_DIR, 'plugin.png'))
            self.iconphoto(True, icon)
        except Exception:
            pass
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.mainframe = ttk.Frame(self, padding="12 12 12 12") # padding values's order: "W N E S"
        self.mainframe.grid(column=0, row=0, sticky="nsew")
        self.mainframe.bind('<Configure>',
                            lambda event: self.update_wraplength(event, style))
        self.upperframe = ttk.Frame(self.mainframe, padding="0", relief=tk.SUNKEN, borderwidth=1)
        self.upperframe.grid(column=0, row=0, sticky="nsew")
        self.lowerframe = ttk.Frame(self.mainframe, padding="0 8 0 0")
        self.lowerframe.grid(column=0, row=1, sticky="nsew")

        if orphaned_selectors:
            self.geometry('360x420+100+100')
            self.scrollList = ttk.Scrollbar(self.upperframe, orient=tk.VERTICAL)
            self.text = tk.Text(self.upperframe, yscrollcommand=self.scrollList.set,
                             borderwidth=0, pady=0) # width=40, height=20,
            self.scrollList.grid(row=0, column=3, sticky="nsew")
            self.scrollList['command'] = self.text.yview
            self.text.grid(row=0, column=0, columnspan=3, sticky="nsew")
            self.bind_to_mousewheel(self.text)

            orphaned = SelectorsDialog.orphaned_dict

            self.toggleAll = tk.BooleanVar()
            self.toggleAllStr = tk.StringVar()
            self.toggleAllStr.set('Unselect all')
            self.checkToggleAll = ttk.Checkbutton(self.text,
                                                  textvariable=self.toggleAllStr,
                                                  variable=self.toggleAll,
                                                  onvalue=True, offvalue=False,
                                                  command=self.toggle_all,
                                                  cursor="arrow")
            self.add_bindtag(self.checkToggleAll, self.text)
            self.text.window_create('end', window=self.checkToggleAll)
            self.text.insert('end', '\n\n')
            self.toggleAll.set(True)

            self.toggle_selectors_list = []
            for index, selector_tuple in enumerate(orphaned_selectors):
                css_filename = href_to_basename(bk.id_to_href(selector_tuple[0]))
                sel_and_css = '{} ({})'.format(selector_tuple[2].selectorText, css_filename)
                selector_key = selector_tuple[2].selectorText+"_"+str(index)
                orphaned[selector_key] = [selector_tuple, tk.BooleanVar()]
                sel_checkbutton = ttk.Checkbutton(self.text,
                                                  text=sel_and_css,
                                                  variable=orphaned[selector_key][1],
                                                  onvalue=True, offvalue=False,
                                                  cursor="arrow")
                self.add_bindtag(sel_checkbutton, self.text)
                self.text.window_create('end', window=sel_checkbutton)
                self.text.insert('end', '\n')
                orphaned[selector_key][1].set(True)
                self.toggle_selectors_list.append(orphaned[selector_key][1])
            self.text.config(state=tk.DISABLED)
        else:
            self.geometry('+100+100')
            self.labelInfo = ttk.Label(self.upperframe,
                                       text="I didn't find any unused selector.")
            self.labelInfo.grid(row=0, column=0, sticky="we", pady=5)

        cont_button = ttk.Button(self.lowerframe,
                                 text='Continue',
                                 command=self.proceed)
        cont_button.grid(row=0, column=1, sticky="we")
        canc_button = ttk.Button(self.lowerframe,
                                 text='Cancel',
                                 command=self.quit)
        canc_button.grid(row=0, column=2, sticky="we")
        cont_button.bind('<Return>', lambda event: self.proceed())
        cont_button.bind('<KP_Enter>', lambda event: self.proceed())
        canc_button.bind('<Return>', lambda event: self.quit())
        canc_button.bind('<KP_Enter>', lambda event: self.quit())

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

    def update_wraplength(self, event, style):
        style.configure('TCheckbutton',
                        wraplength=event.width-(50+self.scrollList.winfo_reqwidth()))

    def add_bindtag(self, widget, other):
        bindtags = list(widget.bindtags())
        bindtags.insert(1, str(other))  # self.winfo_pathname(other.winfo_id()))
        widget.bindtags(tuple(bindtags))

    def bind_to_mousewheel(self, widget):
        if sys.platform.startswith("linux"):
            widget.bind("<4>", lambda event: self.scroll_on_mousewheel(event, widget))
            widget.bind("<5>", lambda event: self.scroll_on_mousewheel(event, widget))
        else:
            widget.bind("<MouseWheel>", lambda event: self.scroll_on_mousewheel(event, widget))

    def scroll_on_mousewheel(self, event, widget):
        if event.num == 5 or event.delta < 0:
            move = 1
        else:
            move = -1
        widget.yview_scroll(move, tk.UNITS)


class ErrorDlg(tk.Tk):

    def __init__(self, filename):
        super().__init__()
        self.withdraw()
        msgbox.showerror('Error while parsing {}'.format(filename), sys.exc_info()[1])
        self.destroy()


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
    # of selectors text (e.g. spaces around combinators are always added,
    # sequences of whitespace characters are always reduced to one U+0020).
    selector_ns = ''
    # https://www.w3.org/TR/css-syntax-3/#input-preprocessing
    # states that \r, \f and \r\n  must be replaced by \n
    # before tokenization.
    for token in re.split(r'(?<!\\(?:[a-fA-F0-9]{1,6})?)([ \n\t]:not\(|[ \n\t])',
                          selector_text):
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
    cssutils.ser.prefs.linesAfterRules = prefs['linesAfterRules']
    cssutils.ser.prefs.formatUnknownAtRules = prefs['formatUnknownAtRules']

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
    prefs.defaults['linesAfterRules'] = 1 * '\n'
    prefs.defaults['formatUnknownAtRules'] = False

    # Update pref names to make them uniform with new css-parser pref names
    if prefs.get('blankLinesAfterRules'):
        prefs['linesAfterRules'] = prefs['blankLinesAfterRules']
        del prefs['blankLinesAfterRules']
    if prefs.get('formatUnknownRules'):
        prefs['formatUnknownAtRules'] = prefs['formatUnknownRules']
        del prefs['formatUnknownRules']

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
    # set custom serializer if Sigil version is < 0.9.18 (0.9.18 and higher have the new css-parser module)
    if bk.launcher_version() < 20190826:
        cssutils.setSerializer(customcssutils.MyCSSSerializer())
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

    parsed_markup = {}
    for file_id, href, mime in bk.manifest_iter():
        if mime == 'application/xhtml+xml':
            is_xhtml = True
        elif parseAllXMLFiles and re.search(r'[/+]xml\b', mime):
            is_xhtml = False
        else:
            continue
        parsed_markup[file_id] = {
            'is_xhtml': is_xhtml,
            'html': etree.HTML(bk.readfile(file_id).encode('utf-8'))
        }
        try:
            parsed_markup[file_id]['xml']: etree.XML(bk.readfile(file_id).encode('utf-8'), xml_parser)
        except etree.XMLSyntaxError:
            form = ErrorDlg(href_to_basename(href))
            form.mainloop()
            return 1

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
                    for file_id, etrees in parsed_markup.items():
                        if selector_exists(etrees['html'], selector_ns, namespaces_dict, etrees['is_xhtml']):
                            maintain_selector = True
                            break
                        if etrees.get('xml') and selector_exists(etrees['xml'], selector_ns, namespaces_dict, etrees['is_xhtml']):
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
