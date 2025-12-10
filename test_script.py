import unittest
import os
import pandas as pd
from run_monthly_analysis import load_gpu_prices, process_university

class TestGPUsPerStudent(unittest.TestCase):

    def setUp(self):
        # Create dummy files if needed, or just test logic with mocks
        self.mock_prices = {
            "h100_pcie": 30000,
            "a100_80gb": 15000,
            "h100_sxm": 35000
        }
        
        self.mock_prompt = "Hello {{UNIVERSITY_NAME}}"

    def test_load_gpu_prices(self):
        # This tests the logic, assuming the file exists or fallback is used
        prices = load_gpu_prices()
        self.assertIsInstance(prices, dict)
        self.assertIn("h100_pcie", prices)

    def test_process_university_mock(self):
        # Ensure it handles mock data correctly
        # We need to ensure we don't actually hit the API (which the script does if key is missing)
        # The script defaults to mock if no key, so this is safe to run in test env without key
        
        # Temporarily unset key just in case
        old_key = os.environ.get("GEMINI_API_KEY")
        if old_key:
            del os.environ["GEMINI_API_KEY"]
            
        try:
            result = process_university("Test University", self.mock_prices, self.mock_prompt)
            
            self.assertIsNotNone(result)
            self.assertEqual(result['University'], "Test University")
            self.assertIn("Gpus_Per_Student", result)
            self.assertTrue(result['Weighted_Student_Count'] > 0)
            
        finally:
            if old_key:
                os.environ["GEMINI_API_KEY"] = old_key

if __name__ == '__main__':
    unittest.main()
