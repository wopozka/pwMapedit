import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import misc_functions

TEST_RETURN_ICON_DEFINITION = ((['Type=0x15', 'SubType=0x00', 'Marine=Y', 'string1=0x04,Map', 'string2=0x15,Mapa',
                                 'dayxpm="24 24 14 1",',
                                 '"       c None",',
                                 '".      c #000000",',
                                 '"+      c #FFFFFF",',
                                 '"@      c #999999",',
                                 '"$      c #8E99A2",',
                                 '"&      c #666666",',
                                 '"*      c #003399",',
                                 '"=      c #0047AD",',
                                 '"-      c #0066CC",',
                                 '";      c #006AD0",',
                                 '">      c #007FE5",',
                                 '",      c #0099FF",',
                                 '"\'      c #FF0000",',
                                 '")      c #0069CF",',
                                 '"                        ",',
                                 '"                        ",',
                                 '"                        ",',
                                 '"      ++++++++++++      ",',
                                 '"      +@@@@@@$$@@+      ",',
                                 '"      +&*=---;>,@+      ",',
                                 '"      +&*=---;>,@+      ",',
                                 '"      +&*\'\'\'\'\'\',@+      ",',
                                 '"      +&*\'\'\'\'\'\',@+      ",',
                                 '"      +&*=---)>,@+      ",',
                                 '"      +&*=---)>,@+      ",',
                                 '"      +&*=---)>,@+      ",',
                                 '"      +&*=---)>,@+      ",',
                                 '"      +&*=---)>,@+      ",',
                                 '"      +&*=---)>,@+      ",',
                                 '"      +&*=---->,@+      ",}'],
                                ('0x1500', '/* XPM */\n static const unsigned char * day_xpm[] = {\n"24 24 14 1",\n"       c None",\n".      c #000000",\n"+      c #FFFFFF",\n"@      c #999999",\n"$      c #8E99A2",\n"&      c #666666",\n"*      c #003399",\n"=      c #0047AD",\n"-      c #0066CC",\n";      c #006AD0",\n">      c #007FE5",\n",      c #0099FF",\n"\'      c #FF0000",\n")      c #0069CF",\n"                        ",\n"                        ",\n"                        ",\n"      ++++++++++++      ",\n"      +@@@@@@$$@@+      ",\n"      +&*=---;>,@+      ",\n"      +&*=---;>,@+      ",\n"      +&*\'\'\'\'\'\',@+      ",\n"      +&*\'\'\'\'\'\',@+      ",\n"      +&*=---)>,@+      ",\n"      +&*=---)>,@+      ",\n"      +&*=---)>,@+      ",\n"      +&*=---)>,@+      ",\n"      +&*=---)>,@+      ",\n"      +&*=---)>,@+      ",\n"      +&*=---->,@+      ",}\n')),
                               )

@pytest.mark.parametrize('target, answer', TEST_RETURN_ICON_DEFINITION)
def test_return_icon_definiton(target, answer):
    assert misc_functions.return_icon_definition(target) == answer
