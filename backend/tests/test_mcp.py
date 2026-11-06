import asyncio
import os
import sys
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from app.schemas import TOOLS

def test_official_mcp_stdio_handshake_and_tool_schemas():
    async def check():
        params = StdioServerParameters(command=sys.executable, args=['-m','app.mcp_server'], env={**os.environ})
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                result = await session.list_tools()
                assert {t.name for t in result.tools} == set(TOOLS)
                payment = next(t for t in result.tools if t.name=='payment_prepare')
                assert 'provenance_refs' in payment.input_schema['properties']
    asyncio.run(check())
