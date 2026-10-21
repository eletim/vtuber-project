"""Artwork and face fixes must not regress when body motion changes."""
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_motion_v18_preservation import verify

class HistoricalMotionArtworkPreservation(unittest.TestCase):
    def test_v18_preserved_accepted_v17_art_model_and_face_renderer_exactly(self):
        # v19 deliberately changes the body model and renderer to separate
        # clothing. This historical v18 assertion must not constrain that fix.
        result=verify(revision='0fbe1ea2c698d936588b8080daf766049c66e306')
        self.assertEqual(result['status'],'PASS')
        self.assertGreater(result['preserved_file_count'],300)
        self.assertFalse(result['new_psd_required'])

if __name__=='__main__':unittest.main()
