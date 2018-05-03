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
import lib.niceprint as niceprint
import lib.UPLDRConstants as UPLDRConstantsClass
# -----------------------------------------------------------------------------


class TestNicePrintMethods(unittest.TestCase):

    def test_niceprint(self):
        """ test_niceprint

        Arguments astr, fname='uploadr'
        Print a message with the format:
            [2017.11.19 01:53:57]:[PID       ][PRINT   ]:[uploadr] Some Message
        """
        # with captured_stdout() as astr:
        #     print "hello"
        # assert astr.getvalue() == "hello\n", 'not ok'
        NP = niceprint.niceprint()

        with test.support.captured_stdout() as astr:
            NP.niceprint('hello')

        print(astr.getvalue())
        print('type:{}'.format(type(astr)))
        npre = '\[[0-9. :]+\].+hello$'
        self.assertRegexpMatches(astr.getvalue(), npre)


class TestMethods(unittest.TestCase):

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

    def test_run(self):
        """ test_run
        
            Unit tests for UPLDRConstantsClass.Run formula
            
        """        
        print(eval(time.strftime('int("%j")+int("%H")*100'
                                 '+int("%M")*10+int("%S")')))
        
        self.assertTrue(
            1 <= eval(
                time.strftime('int("%j")+int("%H")*100'
                              '+int("%M")*10+int("%S")')) <= 3415)
        for j in range(1, 366 + 1):
            for h_hour in range(24):
                for m_min in range(60):
                    for s_secs in range(60):
                        self.assertTrue(1 <=
                                        j+h_hour*100+m_min*10+s_secs <= 3415)

    def test_unicode(self):
        NP = niceprint.niceprint()
        for i in range(1, 500):
            if sys.version_info < (3, ):
                if i < 127:
                    self.assertFalse(NP.isThisStringUnicode(chr(i)))
                    self.assertTrue(NP.isThisStringUnicode(
                        unicode(chr(i).decode('utf-8'))))  # noqa
            else:
                self.assertFalse(NP.isThisStringUnicode(chr(i)))


class TestUPLDRConstantsMethods(unittest.TestCase):
    """ TestUPLDRConstantsMethods
    """
    def test_media_count(self):
        """ test_media_count
        """
        UPLDRConstants = UPLDRConstantsClass.UPLDRConstants()

        for j in range(1, 20):
            UPLDRConstants.media_count= j
            self.assertEqual(UPLDRConstants.media_count, j)


if __name__ == '__main__':
    # unittest.main()

    suite = unittest.TestLoader().loadTestsFromTestCase(TestMethods)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestNicePrintMethods)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(
        TestUPLDRConstantsMethods)
    unittest.TextTestRunner(verbosity=2).run(suite)
