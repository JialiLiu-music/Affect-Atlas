"""Regression tests for real manuscript math in HTML, Markdown and DOCX."""
import re
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class ManuscriptMathTests(unittest.TestCase):
    def test_markdown_uses_github_math_delimiters(self):
        text = (ROOT / 'manuscript_en.md').read_text(encoding='utf-8')
        self.assertNotRegex(text, r'\\[\[\]()\]]')
        self.assertEqual(len(re.findall(r'^\$\$\s*$', text, re.M)), 20)
        self.assertEqual(re.findall(r'\\tag\{(\d+)\}', text), [str(n) for n in range(1, 11)])

    def test_formula_bodies_are_unchanged(self):
        import subprocess
        current = (ROOT / 'manuscript_en.md').read_text(encoding='utf-8')
        previous = subprocess.run(['git', 'show', '1f07ea8:manuscript_en.md'],
                                  cwd=ROOT, check=True, capture_output=True).stdout.decode('utf-8')
        canonical = previous.replace('\\[', '$$').replace('\\]', '$$').replace('\\(', '$').replace('\\)', '$')
        def formulas(text):
            return re.findall(r'\$\$(.*?)\$\$|(?<!\$)\$([^$\n]+)\$(?!\$)', text, re.S)
        self.assertEqual(formulas(current), formulas(canonical))

    def test_html_has_typeset_display_and_inline_math(self):
        text = (ROOT / 'manuscript_en.html').read_text(encoding='utf-8')
        self.assertGreaterEqual(len(re.findall(r'<math\b', text)), 40)
        self.assertEqual(len(re.findall(r'<math\b[^>]*display="block"', text)), 10)
        self.assertIn('<mfrac>', text)
        self.assertNotRegex(text, r'<pre>\s*(?:\\\[|\$\$)')
        self.assertNotIn('src="https://', text)

    def test_docx_contains_native_editable_equations(self):
        with zipfile.ZipFile(ROOT / 'manuscript_en.docx') as archive:
            tree = ET.fromstring(archive.read('word/document.xml'))
        ns = {'m': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
              'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        self.assertEqual(len(tree.findall('.//m:oMathPara', ns)), 10)
        self.assertGreaterEqual(len(tree.findall('.//m:oMath', ns)), 40)
        self.assertGreater(len(tree.findall('.//m:f', ns)), 0)
        ordinary_text = ' '.join(n.text or '' for n in tree.findall('.//w:t', ns))
        self.assertNotRegex(ordinary_text, r'\\(?:frac|mathbf|tag|hat|sum)\b')


if __name__ == '__main__':
    unittest.main(verbosity=2)
