from orchestrator.intent_extractor import extract_user_intent

result = extract_user_intent('who are the ministers of the newly elected german government')
print('Intent type:', result.get('intent_type'))
print('Tools needed:', result.get('tools_needed', []))
print('Confidence:', result.get('confidence'))
print('Reasoning:', result.get('reasoning', ''))

if result.get('tools_needed') and 'search_web' in result.get('tools_needed'):
    print('✅ SUCCESS: Query routed to search_web tool')
elif result.get('tools_needed') and 'search_products' in result.get('tools_needed'):
    print('❌ FAILURE: Query still routed to search_products')
else:
    print('⚠️  UNEXPECTED: Query routed to:', result.get('tools_needed'))
