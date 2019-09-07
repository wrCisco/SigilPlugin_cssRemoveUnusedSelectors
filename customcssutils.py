#!/usr/bin/env python3
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
#
# Part of the code in this file is derived from the package cssutils.
# cssutils is published under the GNU Lesser General Public License version 3,
# copyright 2005 - 2013 Christof Hoeke


from cssutils.stylesheets.mediaquery import MediaQuery
import cssutils

# Add support for Amazon's proprietary media types
MediaQuery.MEDIA_TYPES.extend(('amzn-mobi', 'amzn-kf8'))


class MyCSSSerializer(cssutils.CSSSerializer):

    def __init__(self):
        super().__init__()
        self.prefs.linesAfterRules = 0 * '\n'
        self.prefs.formatUnknownAtRules = False

    def do_CSSStyleSheet(self, stylesheet):
        """serializes a complete CSSStyleSheet"""
        useduris = stylesheet._getUsedURIs()
        out = []
        for rule in stylesheet.cssRules:
            if self.prefs.keepUsedNamespaceRulesOnly and\
               rule.NAMESPACE_RULE == rule.type and\
               rule.namespaceURI not in useduris and (
                    rule.prefix or None not in useduris):
                continue

            cssText = rule.cssText
            if cssText:
                out.append(cssText+self.prefs.linesAfterRules)
        text = self._linenumnbers(self.prefs.lineSeparator.join(out))

        # get encoding of sheet, defaults to UTF-8
        try:
            encoding = stylesheet.cssRules[0].encoding
        except (IndexError, AttributeError):
            encoding = 'UTF-8'

        # TODO: py3 return b str but tests use unicode?
        return text.encode(encoding, 'escapecss')

    def do_CSSFontFaceRule(self, rule):
        """
        serializes CSSFontFaceRule

        style
            CSSStyleDeclaration

        + CSSComments
        """
        styleText = self.do_css_CSSStyleDeclaration(rule.style)

        if styleText and rule.wellformed:
            out = cssutils.serialize.Out(self)
            out.append(self._atkeyword(rule))
            for item in rule.seq:
                # assume comments {
                out.append(item.value, item.type)
            out.append('{')
            out.append('%s' % (styleText),
                       indent=1)
            out.append('%s}' % (self.prefs.lineSeparator))
            return out.value()
        else:
            return ''

    def do_CSSPageRule(self, rule):
        """
        serializes CSSPageRule

        selectorText
            string
        style
            CSSStyleDeclaration
        cssRules
            CSSRuleList of MarginRule objects

        + CSSComments
        """
        # rules
        rules = ''
        rulesout = []
        for r in rule.cssRules:
            rtext = r.cssText
            if rtext:
                rulesout.append(rtext)
                rulesout.append(self.prefs.lineSeparator)

        rulesText = ''.join(rulesout)#.strip()

        # omit semicolon only if no MarginRules
        styleText = self.do_css_CSSStyleDeclaration(rule.style,
                                                    omit=not rulesText)

        if (styleText or rulesText) and rule.wellformed:
            out = cssutils.serialize.Out(self)
            out.append(self._atkeyword(rule))
            out.append(rule.selectorText)
            out.append('{')

            if styleText:
                if not rulesText:
                    out.append('%s' % styleText, indent=1)
                    out.append('%s' % self.prefs.lineSeparator)
                else:
                    out.append(styleText, type_='styletext', indent=1, space=False)

            if rulesText:
                out.append(rulesText, indent=1)
            #?
            self._level -= 1
            out.append('}')
            self._level += 1

            return out.value()
        else:
            return ''

    def do_CSSUnknownRule(self, rule):
        if not self.prefs.formatUnknownAtRules:
            if rule.wellformed and self.prefs.keepUnknownAtRules:
                return rule.atkeyword + ''.join(x.value for x in rule.seq)
            else:
                return ''
        else:
            return super().do_CSSUnknownRule(rule)
