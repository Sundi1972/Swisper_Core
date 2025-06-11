from mcp_server.swisper_mcp import create_mcp_server

server = create_mcp_server()
tools = server.list_tools()
print('Available tools:', list(tools['tools'].keys()))
print('search_web tool exists:', 'search_web' in tools['tools'])

if 'search_web' in tools['tools']:
    result = server.call_tool('search_web', {'query': 'German government ministers 2024'})
    print('Search result success:', result.get('success'))
    print('Search result count:', result.get('count'))
    if result.get('results'):
        print('First result title:', result['results'][0].get('title', 'No title'))
else:
    print('search_web tool not found!')
