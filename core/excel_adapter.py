"""Read-only workbook adapter shared by native tools and optional MCP stdio."""
from core.document_archive import selected_file


def read(path, sheet='', cell_range='A1:T50'):
    from openpyxl import load_workbook
    from openpyxl.utils.cell import range_boundaries
    p = selected_file(path)
    if p.suffix.lower() not in ('.xlsx', '.xlsm'):
        raise ValueError('Use an .xlsx/.xlsm workbook; legacy .xls requires conversion.')
    left, top, right, bottom = range_boundaries(cell_range)
    if None in (left, top, right, bottom) or left < 1 or top < 1 or right < left or bottom < top or (right-left+1)*(bottom-top+1) > 5000:
        raise ValueError('Select a concrete range of at most 5000 cells.')
    formulas = load_workbook(p, read_only=True, data_only=False, keep_links=False)
    values = load_workbook(p, read_only=True, data_only=True, keep_links=False)
    try:
        name = sheet or formulas.sheetnames[0]
        if name not in formulas.sheetnames:
            raise ValueError('Sheet not found: ' + ', '.join(formulas.sheetnames))
        cells = []
        for fr, vr in zip(formulas[name].iter_rows(min_row=top,max_row=bottom,min_col=left,max_col=right), values[name].iter_rows(min_row=top,max_row=bottom,min_col=left,max_col=right)):
            for f, v in zip(fr, vr):
                if f.value is not None:
                    cells.append({'cell': f.coordinate, 'value': str(v.value) if v.value is not None else None,
                                  'formula': f.value if f.data_type == 'f' else None})
        return {'path': str(p), 'sheet': name, 'sheets': formulas.sheetnames, 'range':cell_range, 'cells': cells,
                'read_only':True,'formula_notice':'Cached values may be missing/stale; no formulas are recalculated or executed.'}
    finally:
        formulas.close()
        values.close()
