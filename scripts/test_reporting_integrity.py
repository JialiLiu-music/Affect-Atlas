"""Check that presentation edits preserve complete comparisons and appendices."""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReportingIntegrityTests(unittest.TestCase):
    def test_tables_appendices_and_references_preserved(self):
        before = subprocess.run(['git', 'show', '8becd13:manuscript_en.md'],
            cwd=ROOT, check=True, capture_output=True).stdout.decode('utf-8')
        after = (ROOT / 'manuscript_en.md').read_text(encoding='utf-8')
        tables = lambda text: [line for line in text.splitlines() if line.startswith('|')]
        self.assertEqual(tables(before), tables(after))
        self.assertEqual(before.split('## References', 1)[1], after.split('## References', 1)[1])
        limitations = lambda text: text.split('### 6.4. Scope and limitations', 1)[1].split('## 7. Conclusion', 1)[0]
        self.assertEqual(limitations(before), limitations(after))
        figure_paths = lambda text: re.findall(r'!\[[^]]*\]\(([^)]+)\)', text)
        self.assertEqual(figure_paths(before), figure_paths(after))

    def test_primary_and_conditional_results_remain_visible(self):
        text = (ROOT / 'manuscript_en.md').read_text(encoding='utf-8')
        abstract = text.split('## Abstract', 1)[1].split('**Keywords:**', 1)[0]
        for fact in ['13.50%', '334', 'conditional', 'two showing higher error']:
            self.assertIn(fact, abstract)
        self.assertIn('intervals include zero', text.split('### 5.4.', 1)[1].split('## 6.', 1)[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
