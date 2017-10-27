#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import os

import cssutils

import plugin as p


class TestPlugin(unittest.TestCase):

    def setUp(self):
        self.css = cssutils.parseFile(os.path.join(os.path.dirname(__file__),
                                                   'docs', 'base.css'))

    def test_css_namespaces(self):
        self.assertEqual(p.css_namespaces(self.css), ({}, ''))
        self.css.namespaces['svg'] = 'https://www.w3.org/2000/svg'
        self.assertEqual(p.css_namespaces(self.css),
                         ({'svg': 'https://www.w3.org/2000/svg'}, ''))
        self.css.namespaces[''] = 'https://www.w3.org/1999/xhtml'
        self.assertEqual(p.css_namespaces(self.css),
                         ({'svg': 'https://www.w3.org/2000/svg',
                           'a': 'https://www.w3.org/1999/xhtml'}, 'a'))
