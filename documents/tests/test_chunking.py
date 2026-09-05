from django.test import SimpleTestCase

from documents.processing.blocks import RawBlock, assign_hierarchy, detect_heading_by_text
from documents.processing.chunking import chunk_blocks
from documents.processing.tokens import estimate_tokens


class EstimateTokensTests(SimpleTestCase):
    def test_counts_whitespace_separated_words(self):
        self.assertEqual(estimate_tokens('one two three'), 3)

    def test_empty_string_is_zero(self):
        self.assertEqual(estimate_tokens('   '), 0)


class DetectHeadingByTextTests(SimpleTestCase):
    def test_chapter_keyword_is_level_1_heading(self):
        is_heading, level = detect_heading_by_text('Chapter 2: Obligations')
        self.assertTrue(is_heading)
        self.assertEqual(level, 1)

    def test_article_keyword_is_level_2_heading(self):
        is_heading, level = detect_heading_by_text('Article 14')
        self.assertTrue(is_heading)
        self.assertEqual(level, 2)

    def test_all_caps_short_line_is_heading(self):
        is_heading, _ = detect_heading_by_text('DEFINITIONS')
        self.assertTrue(is_heading)

    def test_ordinary_paragraph_is_not_heading(self):
        is_heading, _ = detect_heading_by_text('The parties agree to the following terms and conditions.')
        self.assertFalse(is_heading)

    def test_long_line_is_never_a_heading(self):
        is_heading, _ = detect_heading_by_text('Chapter ' + 'x' * 200)
        self.assertFalse(is_heading)


class AssignHierarchyTests(SimpleTestCase):
    def test_builds_hierarchy_path_from_nested_headings(self):
        blocks = [
            RawBlock(text='Chapter 2', page_number=1, is_heading=True, heading_level=1),
            RawBlock(text='Article 14', page_number=1, is_heading=True, heading_level=2),
            RawBlock(text='The tenant shall pay rent monthly.', page_number=1),
        ]
        enriched = assign_hierarchy(blocks)

        paragraph = enriched[-1]
        self.assertEqual(paragraph.hierarchy_path, 'Chapter 2 > Article 14')
        self.assertEqual(paragraph.section_heading, 'Article 14')

    def test_sibling_heading_replaces_previous_at_same_level(self):
        blocks = [
            RawBlock(text='Chapter 1', page_number=1, is_heading=True, heading_level=1),
            RawBlock(text='Article 1', page_number=1, is_heading=True, heading_level=2),
            RawBlock(text='Chapter 2', page_number=2, is_heading=True, heading_level=1),
            RawBlock(text='Some clause.', page_number=2),
        ]
        enriched = assign_hierarchy(blocks)

        paragraph = enriched[-1]
        self.assertEqual(paragraph.hierarchy_path, 'Chapter 2')
        self.assertEqual(paragraph.section_heading, 'Chapter 2')

    def test_blocks_before_any_heading_have_empty_path(self):
        blocks = [RawBlock(text='Preamble text.', page_number=1)]
        enriched = assign_hierarchy(blocks)
        self.assertEqual(enriched[0].hierarchy_path, '')
        self.assertEqual(enriched[0].section_heading, '')


class ChunkBlocksTests(SimpleTestCase):
    def test_merges_short_paragraphs_up_to_min_tokens(self):
        blocks = [
            RawBlock(text='Chapter 1', page_number=1, is_heading=True, heading_level=1),
        ] + [
            RawBlock(text=f'Sentence number {i} in the paragraph.', page_number=1) for i in range(20)
        ]
        enriched = assign_hierarchy(blocks)
        chunks = chunk_blocks(enriched, min_tokens=20, max_tokens=40)

        self.assertGreater(len(chunks), 1)
        for chunk in chunks[:-1]:
            self.assertGreaterEqual(chunk['token_count'], 20)
            self.assertLessEqual(chunk['token_count'], 40)

    def test_never_merges_across_a_section_boundary(self):
        blocks = [
            RawBlock(text='Article 1', page_number=1, is_heading=True, heading_level=2),
            RawBlock(text='Short clause one.', page_number=1),
            RawBlock(text='Article 2', page_number=1, is_heading=True, heading_level=2),
            RawBlock(text='Short clause two.', page_number=1),
        ]
        enriched = assign_hierarchy(blocks)
        chunks = chunk_blocks(enriched, min_tokens=200, max_tokens=500)

        sections = {c['section_heading'] for c in chunks}
        self.assertEqual(sections, {'Article 1', 'Article 2'})

        article_two_chunk = next(c for c in chunks if c['section_heading'] == 'Article 2')
        self.assertNotIn('Short clause one', article_two_chunk['text'])

    def test_splits_a_single_oversized_paragraph(self):
        long_text = '. '.join(f'This is sentence {i}' for i in range(200)) + '.'
        blocks = [RawBlock(text=long_text, page_number=1)]
        enriched = assign_hierarchy(blocks)
        chunks = chunk_blocks(enriched, min_tokens=200, max_tokens=500)

        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(chunk['token_count'], 500)

    def test_chunks_are_sequentially_indexed(self):
        blocks = [RawBlock(text=f'Paragraph {i}.', page_number=1) for i in range(3)]
        enriched = assign_hierarchy(blocks)
        chunks = chunk_blocks(enriched, min_tokens=1, max_tokens=2)

        self.assertEqual([c['index'] for c in chunks], list(range(len(chunks))))

    def test_records_page_number_and_hierarchy_on_each_chunk(self):
        blocks = [
            RawBlock(text='Chapter 2', page_number=3, is_heading=True, heading_level=1),
            RawBlock(text='Paragraph text here.', page_number=3),
        ]
        enriched = assign_hierarchy(blocks)
        chunks = chunk_blocks(enriched, min_tokens=1, max_tokens=500)

        self.assertEqual(chunks[0]['page_number'], 3)
        self.assertEqual(chunks[0]['hierarchy_path'], 'Chapter 2')

    def test_empty_input_produces_no_chunks(self):
        self.assertEqual(chunk_blocks([]), [])
