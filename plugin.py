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


from collections import OrderedDict
import inspect
import sys
import os
import regex as re

from cssselect.xpath import SelectorError
from lxml import etree, cssselect
try:
    import css_parser as cssutils
except ImportError:
    import cssutils

from plugin_utils import (
    PluginApplication, QtWidgets, QtCore, Qt, QtGui,
)
import customcssutils
from wrappingcheckbox import WrappingCheckBox


SCRIPT_DIR = os.path.normpath(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
PLUGIN_ICON = os.path.join(SCRIPT_DIR, 'plugin.png')

# As from https://cssselect.readthedocs.io/en/latest/#supported-selectors
NEVER_MATCH = (":hover",
               ":active",
               ":focus",
               ":target",
               ":visited")


class PrefsDialog(QtWidgets.QDialog):
    """
    Dialog to set and save preferences about css formatting.
    """
    def __init__(self, parent=None, bk=None, prefs=None):
        if prefs:
            self.prefs = prefs
        else:
            self.prefs = get_prefs(bk)
        super().__init__(parent)
        self.setWindowTitle('Preferences')

        self.labelIndent = QtWidgets.QLabel('Indent:')
        self.indent = QtWidgets.QComboBox()
        self.indent.addItems(
            (
                'No indentation',
                '1 space',
                '2 spaces',
                '3 spaces',
                '4 spaces',
                '1 tab',
            )
        )
        p = self.indent.sizePolicy()
        p.setHorizontalPolicy(QtWidgets.QSizePolicy.MinimumExpanding)
        self.indent.setSizePolicy(p)
        indentLayout = QtWidgets.QHBoxLayout()
        indentLayout.addWidget(self.labelIndent)
        indentLayout.addWidget(self.indent)
        self.indentLastBrace = QtWidgets.QCheckBox("Indent rules's last brace")
        self.keepEmptyRules = QtWidgets.QCheckBox('Keep empty rules (e.g. "p { }")')
        self.omitLastSemicolon = QtWidgets.QCheckBox(
            "Omit semicolon after rules's last declaration " +
            '(e.g. "p { font-size: 1.2em; text-indent: .5em }")'
        )
        self.omitLeadingZero = QtWidgets.QCheckBox(
            'Omit leading zero (e.g. ".5em" vs "0.5em")'
        )
        self.formatUnknownAtRules = QtWidgets.QCheckBox(
            "Use settings to reformat css inside not recognized " +
            "@rules, too (not completely safe)"
        )
        self.linesAfterRules = QtWidgets.QCheckBox("Add a blank line after every rule")

        self.get_initial_values()

        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel)
        cont_button = buttonBox.addButton("Save and Continue", QtWidgets.QDialogButtonBox.AcceptRole)
        buttonBox.accepted.connect(self.save_and_go)
        buttonBox.rejected.connect(self.reject)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addLayout(indentLayout)
        mainLayout.addWidget(self.indentLastBrace)
        mainLayout.addWidget(self.keepEmptyRules)
        mainLayout.addWidget(self.omitLastSemicolon)
        mainLayout.addWidget(self.omitLeadingZero)
        mainLayout.addWidget(self.formatUnknownAtRules)
        mainLayout.addWidget(self.linesAfterRules)
        mainLayout.addWidget(buttonBox)
        self.setLayout(mainLayout)

    def get_initial_values(self):
        if self.prefs['indent'] == "\t":
            self.indent.setCurrentText('1 tab')
        else:
            self.indent.setCurrentIndex(len(self.prefs['indent']))
        self.indentLastBrace.setChecked(self.prefs['indentClosingBrace'])
        self.keepEmptyRules.setChecked(self.prefs['keepEmptyRules'])
        self.omitLastSemicolon.setChecked(self.prefs['omitLastSemicolon'])
        self.omitLeadingZero.setChecked(self.prefs['omitLeadingZero'])
        self.formatUnknownAtRules.setChecked(self.prefs['formatUnknownAtRules'])
        self.linesAfterRules.setChecked(bool(self.prefs['linesAfterRules']))

    def save_and_go(self):
        if self.indent.currentText() == '1 tab':
            self.prefs['indent'] = '\t'
        else:
            self.prefs['indent'] = self.indent.currentIndex() * ' '
        self.prefs['indentClosingBrace'] = self.indentLastBrace.isChecked()
        self.prefs['keepEmptyRules'] = self.keepEmptyRules.isChecked()
        self.prefs['omitLastSemicolon'] = self.omitLastSemicolon.isChecked()
        self.prefs['omitLeadingZero'] = self.omitLeadingZero.isChecked()
        self.prefs['formatUnknownAtRules'] = self.formatUnknownAtRules.isChecked()
        self.prefs['linesAfterRules'] = '\n' if self.linesAfterRules.isChecked() else ''
        self.accept()


class InfoDialog(QtWidgets.QWidget):

    stop_plugin = True

    def __init__(self, bk, prefs, css_to_skip=None, css_to_parse=None, css_warnings=None):
        super().__init__()
        self.setWindowTitle('Preparing to parse...')

        self.labelInfo = QtWidgets.QLabel(
            self.parse_errors(bk, css_to_skip, css_to_parse, css_warnings)
        )
        self.labelInfo.setWordWrap(True)

        self.checkParseAllXMLFiles = QtWidgets.QCheckBox(
            'Parse every xml file, not only xhtml.'
        )

        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel
        )
        # ResetRole is mostly for cross-platform positioning:
        # there isn't a standard role exactly adequate for this button,
        # and the connected slot is entirely custom anyway
        pref_button = buttonBox.addButton(
            "Set preferences",
            QtWidgets.QDialogButtonBox.ResetRole
        )
        pref_button.clicked.connect(lambda: self.prefs_dlg(bk, prefs))
        buttonBox.accepted.connect(lambda: self.proceed(bk, prefs))
        buttonBox.rejected.connect(self.close)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.setContentsMargins(12, 12, 12, 12)
        mainLayout.setSpacing(5)
        mainLayout.addWidget(self.labelInfo)
        mainLayout.addWidget(self.checkParseAllXMLFiles)
        mainLayout.addWidget(buttonBox)

        self.setLayout(mainLayout)
        self.get_initial_values(prefs)
        self.show()

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
        return par_msg

    def prefs_dlg(self, bk, prefs):
        dlg = PrefsDialog(self, bk, prefs)
        dlg.exec()

    def get_initial_values(self, prefs):
        self.checkParseAllXMLFiles.setChecked(prefs['parseAllXMLFiles'])

    def proceed(self, bk, prefs):
        prefs['parseAllXMLFiles'] = self.checkParseAllXMLFiles.isChecked()
        set_css_output_prefs(bk, prefs)
        bk.savePrefs(prefs)
        InfoDialog.stop_plugin = False
        self.close()


class SelectorsDialog(QtWidgets.QWidget):
    """
    Dialog to show the list of css "orphaned" selectors (those without
    corresponding tags in xhtml files) and let the user choose the ones
    to delete.
    """

    orphaned_dict = OrderedDict()
    stop_plugin = True

    def __init__(self, bk, orphaned_selectors=None):
        super().__init__()
        self.setWindowTitle("Remove unused Selectors")
        self.setMinimumWidth(360)

        mainLayout = QtWidgets.QVBoxLayout(self)

        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scrollArea.setWidgetResizable(True)
        frameLayout = QtWidgets.QVBoxLayout()
        frameLayout.setSpacing(0)
        frameLayout.setContentsMargins(0, 0, 0, 0)
        frame = QtWidgets.QWidget()
        frame.setLayout(frameLayout)
        scrollArea.setWidget(frame)

        if orphaned_selectors:
            orphaned = SelectorsDialog.orphaned_dict

            labelInfo = QtWidgets.QLabel('Choose the selectors you want to delete')
            labelInfo.setWordWrap(True)
            mainLayout.addWidget(labelInfo)

            self.toggle_selectors_list = []
            self.toggleAll = WrappingCheckBox(
                'Select / Unselect all', margins=(8, 12, 8, 12), fillBackground=True
            )
            self.toggleAll.setChecked(True)
            self.toggleAll.stateChanged().connect(self.toggle_all)
            frameLayout.addWidget(self.toggleAll)

            separator = QtWidgets.QFrame()
            separator.setFrameShape(QtWidgets.QFrame.HLine)
            separator.setFrameShadow(QtWidgets.QFrame.Sunken)
            frameLayout.addWidget(separator)

            alternateBgColor = self.toggleAll.palette().color(QtGui.QPalette.AlternateBase)
            checkbox_margins = (8, 6, 8, 6)
            for index, selector_tuple in enumerate(orphaned_selectors):
                css_filename = href_to_basename(bk.id_to_href(selector_tuple[0]))
                sel_and_css = f'{selector_tuple[2].selectorText} ({css_filename})'
                selector_key = selector_tuple[2].selectorText+"_"+str(index)
                checkbox = WrappingCheckBox(
                    sel_and_css, margins=checkbox_margins, fillBackground=True
                )
                checkbox.setChecked(True)
                if index % 2 == 0:
                    palette = checkbox.palette()
                    palette.setColor(checkbox.backgroundRole(), alternateBgColor)
                    checkbox.setPalette(palette)
                orphaned[selector_key] = [selector_tuple, checkbox]
                self.toggle_selectors_list.append(checkbox)
                frameLayout.addWidget(checkbox)
        else:
            labelInfo = QtWidgets.QLabel("I didn't find any unused selector.")
            frameLayout.addWidget(labelInfo)

        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel
        )
        buttonBox.accepted.connect(self.proceed)
        buttonBox.rejected.connect(self.close)

        mainLayout.addWidget(scrollArea)
        mainLayout.addWidget(buttonBox)

        self.show()

    def proceed(self):
        for k in SelectorsDialog.orphaned_dict:
            SelectorsDialog.orphaned_dict[k][1] = SelectorsDialog.orphaned_dict[k][1].isChecked()
        SelectorsDialog.stop_plugin = False
        self.close()

    def toggle_all(self):
        checked = self.toggleAll.isChecked()
        for checkbox in self.toggle_selectors_list:
            checkbox.setChecked(checked)


class ErrorDlg(QtWidgets.QWidget):

    def __init__(self, filename):
        super().__init__()
        self.setWindowTitle('Error while parsing {}'.format(filename))

        icon = QtWidgets.QLabel()
        icon.setPixmap(
            self.style()
                .standardIcon(QtWidgets.QStyle.SP_MessageBoxCritical)
                .pixmap(QtCore.QSize(32, 32))
        )
        msg = QtWidgets.QLabel(f'Type: {sys.exc_info()[0]}\nMessage: {sys.exc_info()[1]}')
        msg.setMinimumWidth(300)
        msg.setWordWrap(True)
        msgLayout = QtWidgets.QHBoxLayout()
        msgLayout.addWidget(icon)
        msgLayout.addWidget(msg)
        msgLayout.setSpacing(20)

        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        buttonBox.accepted.connect(self.close)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(msgLayout)
        layout.addWidget(buttonBox)
        self.setLayout(layout)
        self.show()


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
    prefs.defaults['quiet'] = False

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
    app = PluginApplication([], bk, app_icon=PLUGIN_ICON)
    prefs = get_prefs(bk)
    xml_parser = etree.XMLParser(resolve_entities=False)
    css_parser = cssutils.CSSParser(raiseExceptions=True, validate=False)
    css_to_skip, css_to_parse, css_warnings = pre_parse_css(bk, css_parser)

    if not prefs['quiet'] or css_to_skip:
        dlg = InfoDialog(bk, prefs, css_to_skip, css_to_parse, css_warnings)
        app.exec()
        if InfoDialog.stop_plugin:
            return -1
    else:
        set_css_output_prefs(bk, prefs)

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
            parsed_markup[file_id]['xml'] = etree.XML(bk.readfile(file_id).encode('utf-8'), xml_parser)
        except etree.XMLSyntaxError:
            dlg = ErrorDlg(href_to_basename(href))
            app.exec()
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
                        if etrees.get('xml') is not None and selector_exists(etrees['xml'], selector_ns, namespaces_dict, etrees['is_xhtml']):
                            maintain_selector = True
                            break
                    if not maintain_selector:
                        orphaned_selectors.append(
                            (
                                css_id, rule,
                                rule.selectorList[selector_index],
                                selector_index,
                                parsed_css
                            )
                        )

    # Show the list of selectors to the user.
    if not prefs['quiet']:
        dlg = SelectorsDialog(bk, orphaned_selectors)
        app.exec()
        if SelectorsDialog.stop_plugin:
            return -1
    else:
        for i, selector in enumerate(orphaned_selectors):
            SelectorsDialog.orphaned_dict[i] = [selector, True]

    # Delete selectors chosen by the user.
    css_to_change = {}
    old_rule, counter = None, 0
    for sel_data, to_delete in SelectorsDialog.orphaned_dict.values():
        if to_delete:
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
