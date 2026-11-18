import unittest
from server import validate_parameters,LIMITS

class EyeControls(unittest.TestCase):
    def test_gaze_clamps_without_altering_mouth_or_blink(self):
        value=validate_parameters({'ParamEyeBallX':9,'ParamEyeBallY':-9,'ParamMouthOpenY':.7,'ParamEyeLOpen':.25})
        self.assertEqual(value,{'ParamEyeBallX':1,'ParamEyeBallY':-1,'ParamMouthOpenY':.7,'ParamEyeLOpen':.25})
        self.assertEqual(LIMITS['ParamEyeBallX'][2],0)
        self.assertEqual(LIMITS['ParamEyeBallY'][2],0)
