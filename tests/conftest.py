import os.path
import sys

# katalog glowny projektu, zeby testy widzialy pwm_core i moduly GUI
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
