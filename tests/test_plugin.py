#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import os

try:
    import css_parser as cssutils
    new_parser = True
except ModuleNotFound:
    import cssutils
    new_parser = False

import plugin as p
import customcssutils


class TestPlugin(unittest.TestCase):

    def setUp(self):
        if not new_parser:
            cssutils.setSerializer(customcssutils.MyCSSSerializer())
        self.css = cssutils.parseFile(os.path.join(os.path.dirname(__file__),
                                                   'resources', 'base.css'))

    def test_css_namespaces(self):
        self.assertEqual(p.css_namespaces(self.css), ({}, ''))
        self.css.namespaces['svg'] = 'https://www.w3.org/2000/svg'
        self.assertEqual(p.css_namespaces(self.css),
                         ({'svg': 'https://www.w3.org/2000/svg'}, ''))
        self.css.namespaces[''] = 'https://www.w3.org/1999/xhtml'
        self.assertEqual(p.css_namespaces(self.css),
                         ({'svg': 'https://www.w3.org/2000/svg',
                           'a': 'https://www.w3.org/1999/xhtml'}, 'a'))

    def test_ignore_selectors(self):
        for pseudo_class in p.NEVER_MATCH:
            self.css.insertRule('{} {{}}'.format(pseudo_class))
        for i in range(0, len(self.css.cssRules) - len(p.NEVER_MATCH)):
            self.css.deleteRule(0)
        for rule in self.css:
            with self.subTest(rule=rule):
                self.assertTrue(p.ignore_selectors(rule.selectorText))

    def test_add_default_prefix(self):
        # Some selectors directly given to the tested function
        self.assertEqual(p.add_default_prefix('aa', 'p.ex1 > strong.ex2'),
                         'aa|p.ex1 > aa|strong.ex2')
        self.assertEqual(p.add_default_prefix('aa', '.ex1:nth-child(2n+1) > '
                                                    'svg|text.\ startingSpace \t:not(p) '
                                                    '.\:notANotSelector\(.\\201C quoted\\201D'),
                         '.ex1:nth-child(2n+1) > '
                         'svg|text.\ startingSpace \t:not(aa|p) '
                         '.\:notANotSelector\(.\\201C quoted\\201D')
        # And some mangled by cssutils
        self.css.namespaces['svg'] = 'https://www.w3.org/2000/svg'
        self.assertTrue('svg' in self.css.namespaces)
        self.css.add(cssutils.css.CSSStyleRule(selectorText='p+p.\\201C quoted\\201D \nspan',
                                               style=cssutils.css.CSSStyleDeclaration('')))
        self.assertEqual(p.add_default_prefix('aa', self.css.cssRules[-1].selectorText),
                         'aa|p + aa|p.“quoted” aa|span')
        self.css.add('.ex1:nth-child(2n+1) > svg|text.\ startingSpace \t:not(p) '
                     '.\:notANotSelector\(.\\201C quoted\\201D {}')
        self.assertEqual(p.add_default_prefix('aa', self.css.cssRules[-1].selectorText),
                         '.ex1:nth-child(2n+1) > svg|text.\ startingSpace :not(aa|p) '
                         '.\:notANotSelector\(.“quoted”')

    def test_clean_generic_prefixes(self):
        self.assertEqual(p.clean_generic_prefixes('|div svg|a'), 'div svg|a')
        self.assertEqual(p.clean_generic_prefixes('*|text xhtml|p'), 'text p')
        self.assertEqual(p.clean_generic_prefixes('html|canvas svg|text'), 'html|canvas svg|text')
