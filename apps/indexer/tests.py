import os
import tempfile
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient

User = get_user_model()


class IndexerTestCase(APITestCase):
    """Basic smoke tests for the indexer pipeline."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testindexer',
            email='indexer@example.com',
            password='TestPass123!',
        )
        self.client = APIClient()
        from rest_framework.authtoken.models import Token
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_tokenizer_basic(self):
        from apps.indexer.tokenizer import tokenize
        tokens = tokenize('The quick brown fox jumps over the lazy dog')
        # 'the', 'over' are stop-words and should be removed
        self.assertNotIn('the', tokens)
        self.assertNotIn('over', tokens)
        # Content words should remain (stemmed)
        self.assertTrue(len(tokens) > 0)

    def test_tokenizer_with_positions(self):
        from apps.indexer.tokenizer import tokenize_with_positions
        positions = tokenize_with_positions('hello world hello')
        stemmed_hello = list(positions.keys())[0] if positions else None
        self.assertIsNotNone(stemmed_hello)

    def test_index_stats_empty(self):
        from apps.indexer.services import IndexerService
        stats = IndexerService.get_index_stats(self.user)
        self.assertEqual(stats['total_entries'], 0)
        self.assertEqual(stats['indexed_documents'], 0)

    def test_extract_text_supports_txt(self):
        from apps.indexer.extractor import extract_text

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write('alpha beta gamma')
            tmp_path = tmp.name

        try:
            uploaded_file = SimpleNamespace(
                id=1,
                file_type='txt',
                file=SimpleNamespace(path=tmp_path),
            )
            extracted = extract_text(uploaded_file)
            self.assertIn('alpha beta gamma', extracted)
        finally:
            os.remove(tmp_path)

