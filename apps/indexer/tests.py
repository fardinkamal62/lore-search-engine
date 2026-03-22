import os
import tempfile
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
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

    def test_prefix_trie_returns_ranked_prefix_matches(self):
        from apps.indexer.trie import PrefixTrie

        trie = PrefixTrie()
        trie.insert('Machine Learning Basics', weight=2.0)
        trie.insert('Machine Vision Notes', weight=3.0)
        trie.insert('Math Primer', weight=1.0)

        suggestions = trie.suggest('mach', limit=2)
        self.assertEqual(suggestions, ['Machine Vision Notes', 'Machine Learning Basics'])

    def test_autocomplete_service_uses_trie_prefix_matching(self):
        from apps.upload.models import UploadedFile
        from apps.indexer.models import DocumentPhrase
        from apps.indexer.services import AutocompleteService

        uploaded = UploadedFile.objects.create(
            file=SimpleUploadedFile('machine-learning-notes.txt', b'ml notes'),
            original_filename='machine-learning-notes.txt',
            file_type='txt',
            file_size=8,
            uploaded_by=self.user,
            status='processed',
        )
        DocumentPhrase.objects.create(
            document=uploaded,
            phrase='machine learning from first principles',
            position=0,
        )

        suggestions = AutocompleteService.get_suggestions(self.user, 'mach', limit=5)
        self.assertTrue(any(p.lower().startswith('machine') for p in suggestions))

    def test_autocomplete_endpoint_returns_phrase_objects(self):
        from apps.upload.models import UploadedFile

        UploadedFile.objects.create(
            file=SimpleUploadedFile('microservices-guide.txt', b'guide text'),
            original_filename='microservices-guide.txt',
            file_type='txt',
            file_size=10,
            uploaded_by=self.user,
            status='processed',
        )

        response = self.client.get('/api/autocomplete?q=mic')
        self.assertEqual(response.status_code, 200)
        self.assertIn('suggestions', response.json())
        if response.json()['suggestions']:
            self.assertIn('phrase', response.json()['suggestions'][0])

