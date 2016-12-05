# sigilPlugin_cssRemoveUnusedSelectors
Remove unused selectors and rules from stylesheets

This plugin uses [cssutils](https://pypi.python.org/pypi/cssutils) to parse the stylesheets of an epub and [lxml](https://pypi.python.org/pypi/lxml/3.5.0)/[csselect](https://pypi.python.org/pypi/cssselect/0.9.1) to check if css selectors match at least one element in xhtml files of that epub.

(Cssutils, lxml and cssselect are all bundled in Sigil installers).

All css selectors without corresponding elements in xhtml files are proposed to the user for deletion.

If css parser encounters errors, it raises a warning and the user can choose to proceed or to stop the plugin. In any case, for safety, the specific stylesheets that caused the errors will be left untouched (cssutils implements many but not all of the CSS3 features, e.g. @media rules nested inside other @media rules).

To make the survey in xhtml files, css selectors are converted in XPath by lxml/cssselect. Some of the selectors (those who contain ":hover", ":active", ":focus", ":target", ":visited") will never match anything, so the plugin lets them be. Same thing for selectors that are not yet implemented (*:first-of-type, *:last-of-type, *:nth-of-type, *:nth-last-of-type, *:only-of-type - they work only if an element type is specified). For reference: https://pythonhosted.org/cssselect/#supported-selectors.

Part of the code in customCssutils.py is derived from the package cssutils.
cssutils is published under the GNU Lesser General Public License version 3,
copyright 2005 - 2013 Christof Hoeke.