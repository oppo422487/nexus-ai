"""Optional explicit stdio MCP server. Never starts with the desktop app."""
import os
import asyncio
from pathlib import Path
# Load native numeric libraries on the process main thread before stdio readers
# start. Their Windows DLL initialization can stall when first imported in a worker.
import openpyxl
from mcp.server.fastmcp import FastMCP
from core.excel_adapter import read

server = FastMCP('Nexa read-only Excel')


@server.tool()
async def read_excel(path: str, sheet: str = '', cell_range: str = 'A1:T50') -> dict:
    """Read cells/formulas in a workbook under explicitly configured allowed roots."""
    roots = [Path(x).expanduser().resolve() for x in os.environ.get('NEXA_EXCEL_ROOTS','').split(os.pathsep) if x]
    target = Path(path).expanduser().resolve()
    if not roots or not any(target.is_relative_to(root) for root in roots):
        raise ValueError('Configure NEXA_EXCEL_ROOTS; this file is outside the allowed roots.')
    return await asyncio.to_thread(read, str(target), sheet, cell_range)


if __name__ == '__main__':
    server.run(transport='stdio')
