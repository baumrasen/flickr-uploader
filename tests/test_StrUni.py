# content of test_StrUni.py

import sys
from ..lib import niceprint as niceprint
import time

def test_Unicode():
    for i in range(1,500):
        if sys.version_info < (3, ):
            if i < 127:
                assert StrUni.isThisStringUnicode(chr(i)) == False
                assert StrUni.isThisStringUnicode(
                                       unicode(chr(i).decode('utf-8'))) == True
        else:
            assert StrUni.isThisStringUnicode(chr(i)) == False
            
        
def test_RUN():
    assert (1 <=
            eval(time.strftime('int("%j")+int("%H")*100+int("%M")'))
            <= 2725) == True
    # for j in range(1,366+1):
    #     for h in range(24):
    #         for m in range(60):
    #             # print('{}.{:0>2d}.{:0>2d}'.format(j, h, m))
    #             # xRun = eval(('int("{}")+int("{:0>2d}")*100+int("{:0>2d}")'.format(j, h, m)))
    #             # Run = eval(time.strftime('int("%j")+int("%H")*100+int("%M")'))
    #             # print Run, xRun
    #             assert (1 <= eval(('int("{}")+int("{:0>2d}")*100+int("{:0>2d}")'.format(j, h, m))) <= 2725) == True
    #             assert (1 <= eval(time.strftime('int("%j")+int("%H")*100+int("%M")')) <= 2725) == True

