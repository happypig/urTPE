import sys
sys.path.insert(0, '.')

from urtpe.cli import _run
import tempfile
import os
import json

# Create a test PDF using the fixture
from tests.fixtures import build_sample_pdf, SAMPLE_ROWS

with tempfile.TemporaryDirectory() as tmpdir:
    pdf_path = os.path.join(tmpdir, 'test.pdf')
    build_sample_pdf(pdf_path, SAMPLE_ROWS)
    
    # Capture stdout to avoid encoding issues
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _run(pdf_path, tmpdir, no_tsv=False, viewer_dir=tmpdir, links=False)
    
    # Check output
    with open(os.path.join(tmpdir, 'projects.json'), 'r', encoding='utf-8') as f:
        doc = json.load(f)
    
    with open(os.path.join(tmpdir, 'test_out.txt'), 'w', encoding='utf-8') as f:
        f.write('Projects: ' + str(doc['counts']['projects']) + '\n')
        f.write('Records: ' + str(doc['counts']['records']) + '\n')
        for p in doc['projects']:
            f.write('  Project: ' + p['project_id'] + '\n')
            f.write('  Links: ' + str(p.get('links', {})) + '\n')
            for n in p['nodes']:
                if n.get('links'):
                    f.write('    Node ' + str(n['recno']) + ' links: ' + str(n['links']) + '\n')
    
    # Check viewer data
    with open(os.path.join(tmpdir, 'projects.data.js'), 'r', encoding='utf-8') as f:
        js = f.read()
    with open(os.path.join(tmpdir, 'test_out.txt'), 'a', encoding='utf-8') as f:
        f.write('Viewer data length: ' + str(len(js)) + ' chars\n')