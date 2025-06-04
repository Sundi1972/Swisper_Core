/**
 * Determines whether to show the search popup based on search results and scope
 * @param {Array} searchResults - Array of search result objects
 * @param {string} currentSessionId - ID of the current active session
 * @param {string} searchScope - Either 'current' or 'global'
 * @returns {boolean} Whether to show the search popup
 */
export const shouldShowSearchPopup = (searchResults, currentSessionId, searchScope) => {
  if (!searchResults || searchResults.length === 0) {
    return false;
  }
  
  if (searchScope === 'current') {
    return searchResults.length > 0;
  }
  
  const hasResultsFromOtherSessions = searchResults.some(result => 
    result.session_id !== currentSessionId
  );
  
  return hasResultsFromOtherSessions;
};
