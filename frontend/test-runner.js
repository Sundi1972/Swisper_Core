import { shouldShowSearchPopup } from './src/utils/searchUtils.js';

const runTests = () => {
  console.log('Running Search Popup Logic Tests...\n');
  
  const currentSessionId = 'session-123';
  let passed = 0;
  let total = 0;
  
  const test = (description, fn) => {
    total++;
    try {
      fn();
      console.log(`✅ ${description}`);
      passed++;
    } catch (error) {
      console.log(`❌ ${description}: ${error.message}`);
    }
  };
  
  test('should return false for empty results', () => {
    const result = shouldShowSearchPopup([], currentSessionId, 'global');
    if (result !== false) throw new Error(`Expected false, got ${result}`);
  });
  
  test('should return true for current scope with any results', () => {
    const results = [{ session_id: 'session-123', message_index: 0 }];
    const result = shouldShowSearchPopup(results, currentSessionId, 'current');
    if (result !== true) throw new Error(`Expected true, got ${result}`);
  });
  
  test('should return false for global scope with only current session results', () => {
    const results = [
      { session_id: 'session-123', message_index: 0 },
      { session_id: 'session-123', message_index: 1 }
    ];
    const result = shouldShowSearchPopup(results, currentSessionId, 'global');
    if (result !== false) throw new Error(`Expected false, got ${result}`);
  });
  
  test('should return true for global scope with results from other sessions', () => {
    const results = [
      { session_id: 'session-123', message_index: 0 },
      { session_id: 'session-456', message_index: 0 }
    ];
    const result = shouldShowSearchPopup(results, currentSessionId, 'global');
    if (result !== true) throw new Error(`Expected true, got ${result}`);
  });
  
  test('should return true for global scope with only other session results', () => {
    const results = [
      { session_id: 'session-456', message_index: 0 },
      { session_id: 'session-789', message_index: 1 }
    ];
    const result = shouldShowSearchPopup(results, currentSessionId, 'global');
    if (result !== true) throw new Error(`Expected true, got ${result}`);
  });
  
  console.log(`\nTest Results: ${passed}/${total} passed`);
  
  if (passed === total) {
    console.log('🎉 All tests passed!');
    return true;
  } else {
    console.log('💥 Some tests failed!');
    return false;
  }
};

runTests();
