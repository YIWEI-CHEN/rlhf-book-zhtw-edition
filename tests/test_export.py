import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import export_book as book


class ManuscriptTests(unittest.TestCase):
    def test_links_protect_code_math_and_existing_links(self):
        text = '引用 [111]，式 80；`[999]` $x[999]$ [原有](https://example.com)\n```\n[999]\n```'
        actual = book.link_prose(text, {111}, {80})
        self.assertIn('[[111]](#bib-111)', actual)
        self.assertIn('式 [80](#eq-80)', actual)
        self.assertIn('`[999]` $x[999]$', actual)
        self.assertIn('```\n[999]\n```', actual)
        self.assertIn('[原有](https://example.com)', actual)
        self.assertEqual(book.link_prose('[[111]](#bib-111)', {111}, set()), '[[111]](#bib-111)')

    def test_missing_targets_fail(self):
        with self.assertRaises(ValueError):
            book.link_prose('[999]', {111}, {80})
        with self.assertRaises(ValueError):
            book.link_prose('式 99', {111}, {80})

    def test_bibliography_unique_contiguous(self):
        self.assertEqual(book.read_bibliography('1. A\n2. B'), {1: 'A', 2: 'B'})
        for invalid in ('1. A\n1. B', '1. A\n3. C', ''):
            with self.assertRaises(ValueError):
                book.read_bibliography(invalid)

    def test_code_heading_is_not_chapter_heading(self):
        result = book.prepare_chapter('# 第 5 章\n```python\n# comment\n```', 'ch05', set(), set())
        self.assertIn('# comment', result)
        self.assertEqual(result.count('{#ch05}'), 1)

    def test_complete_chapter_six_has_one_title(self):
        result = book.prepare_chapter('# 第 6 章\nA\n# 第 6 章下\nB', 'ch06', set(), set())
        self.assertEqual(result.count('# 第 6 章'), 1)
        self.assertIn('B', result)
        with self.assertRaises(ValueError):
            book.prepare_chapter('# A\n# B', 'ch05', set(), set())

    def test_equation_anchor_and_figure_caption(self):
        result = book.prepare_chapter('# A\n\n$$x = y \\tag{80}$$\n\n![圖](figures/a.png)\n\n*圖 1：說明*', 'ch01', set(), {80})
        self.assertIn('#eq-80', result)
        self.assertIn('\\tag{80}', result)
        self.assertIn('![圖 1：說明](figures/a.png){#fig-1}', result)

    def test_bibliography_avoids_reserved_pandoc_ids(self):
        text = book.bibliography_markdown({1: 'Test. doi: 10.48550/arXiv.2601.20802.'})
        self.assertIn('#bib-1', text)
        self.assertNotIn('#ref-1', text)
        self.assertIn('<https://doi.org/10.48550/arXiv.2601.20802>.', text)

    def test_inventory_real_book(self):
        config = json.loads((book.ROOT / 'book.json').read_text(encoding='utf-8'))
        info = {'source_commit': 'test', 'working_tree_dirty': False, 'content_sha256': 'test', 'build_date': '2026-09-09'}
        manuscript, stats = book.prepare(config, info)
        self.assertEqual(stats['references'], 409)
        self.assertEqual(stats['equation_numbers'], list(range(1, 159)))
        self.assertEqual(len(stats['chapters']), 21)
        self.assertNotIn('ch06a', stats['chapters'])
        self.assertEqual(manuscript.count('{#ch06}'), 1)
        self.assertLess(manuscript.index('{#ch17}'), manuscript.index('{#bibliography}'))
        self.assertLess(manuscript.index('{#bibliography}'), manuscript.index('{#appa}'))
        self.assertLess(manuscript.index('{#appa}'), manuscript.index('{#appb}'))
        self.assertLess(manuscript.index('{#appb}'), manuscript.index('{#appc}'))
        self.assertIn('A. Ahmadian', manuscript)
        self.assertNotIn('{#license}', manuscript)
        self.assertNotIn('{#third-party-notices}', manuscript)

    def test_epub_equation_preserves_number_outside_math(self):
        node = {'t': 'Div', 'c': [['eq-80', ['equation'], [['data-number', '80']]],
                [{'t': 'Para', 'c': [{'t': 'Math', 'c': [{'t': 'DisplayMath'}, 'x \\tag{80}']}]}]]}
        book.epub_ast(node)
        math = next(n for n in book.iter_nodes(node) if n.get('t') == 'Math')
        self.assertEqual(math['c'][1], 'x')
        self.assertTrue(any(n.get('c') == '(80)' for n in book.iter_nodes(node)))

    def test_figure_alt_math_is_not_double_counted(self):
        math = {'t': 'Math', 'c': [{'t': 'InlineMath'}, 'x']}
        figure = [{'t': 'Para', 'c': [math]},
                  {'t': 'Image', 'c': [['', [], []], [math], ['figures/a.png', '']]}]
        self.assertEqual(sum(n.get('t') == 'Math' for n in book.iter_nodes(figure)), 2)
        self.assertEqual(sum(n.get('t') == 'Math' for n in book.iter_visible_nodes(figure)), 1)

    def test_multiline_math_reserves_full_height(self):
        size = {'width': 54, 'height': 20, 'baseline': -10}
        style = book.math_image_style(size, True)
        self.assertIn('width:27.0000em;height:10.0000em', style)
        self.assertIn('vertical-align:baseline', style)
        self.assertIn('vertical-align:-10.0000em', book.math_image_style(size, False))


if __name__ == '__main__':
    unittest.main()
