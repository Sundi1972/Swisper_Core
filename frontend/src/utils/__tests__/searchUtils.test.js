import { shouldShowSearchPopup } from '../searchUtils.js';

describe('shouldShowSearchPopup', () => {
  const currentSessionId = 'session-123';
  
  test('should return false for empty results', () => {
    expect(shouldShowSearchPopup([], currentSessionId, 'global')).toBe(false);
    expect(shouldShowSearchPopup(null, currentSessionId, 'global')).toBe(false);
  });
  
  test('should return true for current scope with any results', () => {
    const results = [
      { session_id: 'session-123', message_index: 0 }
    ];
    expect(shouldShowSearchPopup(results, currentSessionId, 'current')).toBe(true);
  });
  
  test('should return false for global scope with only current session results', () => {
    const results = [
      { session_id: 'session-123', message_index: 0 },
      { session_id: 'session-123', message_index: 1 }
    ];
    expect(shouldShowSearchPopup(results, currentSessionId, 'global')).toBe(false);
  });
  
  test('should return true for global scope with results from other sessions', () => {
    const results = [
      { session_id: 'session-123', message_index: 0 },
      { session_id: 'session-456', message_index: 0 }
    ];
    expect(shouldShowSearchPopup(results, currentSessionId, 'global')).toBe(true);
  });
  
  test('should return true for global scope with only other session results', () => {
    const results = [
      { session_id: 'session-456', message_index: 0 },
      { session_id: 'session-789', message_index: 1 }
    ];
    expect(shouldShowSearchPopup(results, currentSessionId, 'global')).toBe(true);
  });
  
  test('should handle mixed results correctly', () => {
    const results = [
      { session_id: 'session-123', message_index: 0 },
      { session_id: 'session-456', message_index: 0 },
      { session_id: 'session-123', message_index: 1 }
    ];
    expect(shouldShowSearchPopup(results, currentSessionId, 'global')).toBe(true);
  });
});
