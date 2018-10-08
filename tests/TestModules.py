"""
    by oPromessa, 2017
    Published on https://github.com/oPromessa/flickr-uploader/

    Helper class and functions for Unit Testing flickr-uploader app
"""

import sys
import time
import unittest
import test.support
# -----------------------------------------------------------------------------
import lib.NicePrint as NicePrint
import lib.Konstants as KonstantsClass
# -----------------------------------------------------------------------------


class TestNicePrintMethods(unittest.TestCase):
    """ TestNicePrintMethods

        Unit test class for module NicePrint
    """

    def test_niceprint(self):
        """ test_niceprint

        Arguments astr, fname='uploadr'
        Print a message with the format:
            [2017.11.19 01:53:57]:[PID       ][PRINT   ]:[uploadr] Some Message
        """
        # with captured_stdout() as astr:
        #     print "hello"
        # assert astr.getvalue() == "hello\n", 'not ok'
        npr = NicePrint.NicePrint()

        with test.support.captured_stdout() as astr:
            npr.niceprint('hello')

        print(astr.getvalue())
        print('type:{}'.format(type(astr)))
        npre = r'\[[0-9. :]+\].+hello$'
        self.assertRegexpMatches(astr.getvalue(), npre)

    def test_unicode(self):
        """ test_unicode
        """
        npr = NicePrint.NicePrint()
        for i in range(1, 500):
            if sys.version_info < (3, ):
                if i < 127:
                    self.assertFalse(npr.is_str_unicode(chr(i)))
                    self.assertTrue(npr.is_str_unicode(
                        unicode(chr(i).decode('utf-8'))))  # noqa
            else:
                self.assertFalse(npr.is_str_unicode(chr(i)))


class TestMethods(unittest.TestCase):
    """ TestMethods

        Unit test class for generic tests
    """

    def test_upper(self):
        """ test_upper

            Simple unit test example for reference: uppercase a string
        """

        self.assertEqual('foo'.upper(), 'FOO')

    def test_isupper(self):
        """ test_isupper

            Simple unit test example for reference: is string uppercase
        """
        self.assertTrue('FOO'.isupper())
        self.assertFalse('Foo'.isupper())

    def test_split(self):
        """ test_split

            Simple unit test example for reference: split a string
        """
        astr = 'hello world'
        self.assertEqual(astr.split(), ['hello', 'world'])
        # check that astr.split fails when the separator is not a string
        with self.assertRaises(TypeError):
            astr.split(2)


class TestKonstantsMethods(unittest.TestCase):
    """ TestKonstantsMethods
    """
    upldr_k = KonstantsClass.Konstants()

    def test_media_count(self):
        """ test_media_count
        """

        for j in range(1, 20):
            self.upldr_k.media_count = j
            self.assertEqual(self.upldr_k.media_count, j)

    def test_run(self):
        """ test_run

            Unit tests for KonstantsClass.Run formula

        """
        print(int(time.strftime('%j')) +
              int(time.strftime('%H'))*100 +
              int(time.strftime('%M'))*10 +
              int(time.strftime('%S')))

        self.assertTrue(1 <= self.upldr_k.Run <= 3415)

        for j in range(1, 366 + 1):
            for h_hour in range(24):
                for m_min in range(60):
                    for s_secs in range(60):
                        self.assertTrue(1 <=
                                        j+h_hour*100+m_min*10+s_secs <= 3415)

    def test_initvalues(self):
        """ test_media_count
        """
        self.assertIsInstance(self.upldr_k.base_dir, str)
        self.assertIsInstance(self.upldr_k.ini_file, str)
        self.assertIsInstance(self.upldr_k.etc_ini_file, str)
        self.assertIsInstance(self.upldr_k.no_delete_tag, str)

        self.assertIsInstance(self.upldr_k.upload_sleep, int)
        self.assertTrue(0 <= self.upldr_k.upload_sleep)


if __name__ == '__main__':
    # unittest.main()

    SUITE = unittest.TestLoader().loadTestsFromTestCase(TestMethods)
    unittest.TextTestRunner(verbosity=2).run(SUITE)

    SUITE = unittest.TestLoader().loadTestsFromTestCase(TestNicePrintMethods)
    unittest.TextTestRunner(verbosity=2).run(SUITE)

    SUITE = unittest.TestLoader().loadTestsFromTestCase(TestKonstantsMethods)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
