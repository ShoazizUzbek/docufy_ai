import uuid
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from documents.processing import vector_store

TEST_COLLECTION = f'test_docufy_chunks_{uuid.uuid4().hex[:8]}'


def _fake_embed(texts):
    """Deterministic 1024-dim vectors: mostly zero, with one dimension
    keyed off a hash of the text so different texts land far apart."""
    vectors = []
    for text in texts:
        vector = [0.0] * 1024
        vector[hash(text) % 1024] = 1.0
        vectors.append(vector)
    return vectors


class FakeChunk:
    def __init__(self, id, index, text, page_number=1, section_heading='', hierarchy_path=''):
        self.id = id
        self.index = index
        self.text = text
        self.page_number = page_number
        self.section_heading = section_heading
        self.hierarchy_path = hierarchy_path


class FakeDocument:
    def __init__(self, id, organization_id, original_filename='doc.txt'):
        self.id = id
        self.organization_id = organization_id
        self.original_filename = original_filename


@override_settings(QDRANT_COLLECTION_NAME=TEST_COLLECTION)
@patch('documents.processing.vector_store.embed_texts', side_effect=_fake_embed)
class VectorStoreTests(SimpleTestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        try:
            vector_store.get_client().delete_collection(TEST_COLLECTION)
        except Exception:
            pass

    def test_ensure_collection_creates_with_correct_vector_config(self, mock_embed):
        vector_store.ensure_collection()
        info = vector_store.get_client().get_collection(TEST_COLLECTION)
        self.assertEqual(info.config.params.vectors.size, 1024)

    def test_upsert_and_search_round_trip(self, mock_embed):
        org_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        document = FakeDocument(id=doc_id, organization_id=org_id)
        chunk = FakeChunk(id=uuid.uuid4(), index=0, text='The tenant shall pay rent monthly.', page_number=2, section_heading='Article 1', hierarchy_path='Chapter 1 > Article 1')

        vector_store.upsert_chunks(document, [chunk])

        query_vector = _fake_embed([chunk.text])[0]
        results = vector_store.search(query_vector, org_id, limit=5)

        self.assertEqual(len(results), 1)
        point = results[0]
        self.assertEqual(point.payload['document_id'], str(doc_id))
        self.assertEqual(point.payload['page_number'], 2)
        self.assertEqual(point.payload['section_heading'], 'Article 1')
        self.assertEqual(point.payload['hierarchy_path'], 'Chapter 1 > Article 1')
        self.assertEqual(point.payload['text'], chunk.text)

    def test_search_is_scoped_to_organization(self, mock_embed):
        org_a, org_b = uuid.uuid4(), uuid.uuid4()
        text = 'A very distinctive clause about indemnification.'

        doc_a = FakeDocument(id=uuid.uuid4(), organization_id=org_a)
        chunk_a = FakeChunk(id=uuid.uuid4(), index=0, text=text)
        vector_store.upsert_chunks(doc_a, [chunk_a])

        doc_b = FakeDocument(id=uuid.uuid4(), organization_id=org_b)
        chunk_b = FakeChunk(id=uuid.uuid4(), index=0, text=text)
        vector_store.upsert_chunks(doc_b, [chunk_b])

        query_vector = _fake_embed([text])[0]
        results_for_a = vector_store.search(query_vector, org_a, limit=10)

        self.assertEqual({p.payload['document_id'] for p in results_for_a}, {str(doc_a.id)})

    def test_search_can_be_scoped_to_one_document(self, mock_embed):
        org_id = uuid.uuid4()
        text = 'A shared distinctive phrase about termination rights.'

        doc_a = FakeDocument(id=uuid.uuid4(), organization_id=org_id)
        vector_store.upsert_chunks(doc_a, [FakeChunk(id=uuid.uuid4(), index=0, text=text)])

        doc_b = FakeDocument(id=uuid.uuid4(), organization_id=org_id)
        vector_store.upsert_chunks(doc_b, [FakeChunk(id=uuid.uuid4(), index=0, text=text)])

        query_vector = _fake_embed([text])[0]

        unscoped = vector_store.search(query_vector, org_id, limit=10)
        self.assertEqual(len(unscoped), 2)

        scoped_to_b = vector_store.search(query_vector, org_id, limit=10, document_id=doc_b.id)
        self.assertEqual({p.payload['document_id'] for p in scoped_to_b}, {str(doc_b.id)})

    def test_delete_document_vectors_removes_only_that_document(self, mock_embed):
        org_id = uuid.uuid4()
        doc_keep = FakeDocument(id=uuid.uuid4(), organization_id=org_id)
        doc_delete = FakeDocument(id=uuid.uuid4(), organization_id=org_id)

        vector_store.upsert_chunks(doc_keep, [FakeChunk(id=uuid.uuid4(), index=0, text='Keep this chunk around.')])
        vector_store.upsert_chunks(doc_delete, [FakeChunk(id=uuid.uuid4(), index=0, text='Delete this chunk please.')])

        vector_store.delete_document_vectors(doc_delete.id)

        client = vector_store.get_client()
        remaining, _ = client.scroll(collection_name=TEST_COLLECTION, limit=100, with_payload=True)
        remaining_doc_ids = {p.payload['document_id'] for p in remaining}
        self.assertIn(str(doc_keep.id), remaining_doc_ids)
        self.assertNotIn(str(doc_delete.id), remaining_doc_ids)

    def test_upsert_with_no_chunks_is_a_no_op(self, mock_embed):
        document = FakeDocument(id=uuid.uuid4(), organization_id=uuid.uuid4())
        vector_store.upsert_chunks(document, [])
        mock_embed.assert_not_called()
