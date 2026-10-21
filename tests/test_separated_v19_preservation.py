"""Structural body separation may not silently repaint accepted facial assets."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_separated_v19_preservation import verify

class SeparatedArtworkPreservation(unittest.TestCase):
    def test_old_art_and_face_are_exact_and_new_body_parts_exist(self):
        report=verify()
        self.assertEqual(report['status'],'PASS')
        self.assertGreater(report['preserved_original_files'],300)
        self.assertGreaterEqual(report['ordered_body_layers'],5)

if __name__=='__main__':unittest.main()
