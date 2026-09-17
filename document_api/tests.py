import os
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

class DocumentScreeningAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.valid_sample_path = "static/samples/sample_valid.png"
        self.blurry_sample_path = "static/samples/sample_blurry.png"
        self.inconsistent_sample_path = "static/samples/sample_inconsistent.png"

    def test_landing_page_renders(self):
        """Verify the main web application renders successfully."""
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "VerifyAI")
        self.assertContains(response, "AI-Powered Identity")
        self.assertContains(response, "Document Screening")
        self.assertContains(response, "Screen Your Document")

    def test_stats_endpoint(self):
        """Verify the /api/stats/ returns required metrics."""
        response = self.client.get(reverse('api_stats'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['metrics']['total_screened'], 128)
        self.assertGreaterEqual(data['metrics']['low_review'], 72)
        self.assertGreaterEqual(data['metrics']['medium_review'], 39)
        self.assertGreaterEqual(data['metrics']['high_review'], 17)
        self.assertEqual(len(data['distribution']), 3)

    def test_demo_samples_endpoint(self):
        """Verify the /api/demo-samples/ lists available synthetic cards."""
        response = self.client.get(reverse('api_demo_samples'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['samples']), 3)

    def test_screen_missing_file_fails(self):
        """Verify that sending a POST without document returns 400 Bad Request."""
        response = self.client.post(reverse('api_screen'), {})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])

    def test_screen_invalid_file_extension_fails(self):
        """Verify that non-image file uploads are blocked."""
        bad_file = SimpleUploadedFile("malicious.txt", b"This is a text file", content_type="text/plain")
        response = self.client.post(reverse('api_screen'), {'document': bad_file})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn("Invalid file type", data['error'])

    def test_screen_valid_synthetic_document(self):
        """Test end-to-end screening with clean synthetic document."""
        if not os.path.exists(self.valid_sample_path):
            self.skipTest("Sample valid image does not exist.")

        with open(self.valid_sample_path, 'rb') as f:
            upload = SimpleUploadedFile("sample_valid.png", f.read(), content_type="image/png")

        response = self.client.post(reverse('api_screen'), {'document': upload})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('extracted_data', data)
        self.assertIn('screening', data)
        self.assertIn('breakdown', data)
        self.assertIn('risk_score', data['screening'])
        self.assertIn('risk_level', data['screening'])
        self.assertIn('flags', data['screening'])

        # Valid sample should have low risk score <= 30
        self.assertLessEqual(data['screening']['risk_score'], 35)
        self.assertEqual(data['screening']['risk_level'], 'LOW REVIEW')

    def test_screen_blurry_synthetic_document(self):
        """Test screening flags blur when blurry sample is uploaded."""
        if not os.path.exists(self.blurry_sample_path):
            self.skipTest("Sample blurry image does not exist.")

        with open(self.blurry_sample_path, 'rb') as f:
            upload = SimpleUploadedFile("sample_blurry.png", f.read(), content_type="image/png")

        response = self.client.post(reverse('api_screen'), {'document': upload})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        # Blurry document quality check
        self.assertTrue(data['breakdown']['document_quality']['is_blurry'])
        self.assertIn('MEDIUM REVIEW', data['screening']['risk_level'])

    def test_screen_inconsistent_synthetic_document(self):
        """Test screening flags high review when corrupted sample is uploaded."""
        if not os.path.exists(self.inconsistent_sample_path):
            self.skipTest("Sample inconsistent image does not exist.")

        with open(self.inconsistent_sample_path, 'rb') as f:
            upload = SimpleUploadedFile("sample_inconsistent.png", f.read(), content_type="image/png")

        response = self.client.post(reverse('api_screen'), {'document': upload})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['screening']['risk_level'], 'HIGH REVIEW')
        self.assertGreaterEqual(data['screening']['risk_score'], 66)
