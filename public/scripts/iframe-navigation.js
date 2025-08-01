// iframe-navigation.js - Add this script to your iframe apps

(function() {
  const STORAGE_KEY = 'iframeNavigationHistory';
  
  // State variables
  let historyPosition = 0;
  let historyStack = [];
  let isInitialized = false;

  // Initialize with default state
  const initializeState = (url = window.location.href) => {
    historyStack = [url];
    historyPosition = 0;
  };

  // Calculate navigation capabilities
  const getNavigationState = () => ({
    canGoBack: historyPosition > 0,
    canGoForward: historyPosition < historyStack.length - 1,
    currentUrl: window.location.href
  });

  // Send navigation state to parent
  const sendNavigationState = () => {
    if (window.parent !== window) {
      window.parent.postMessage({
        type: 'navigation-state',
        ...getNavigationState()
      }, '*');
    }
  };

  // Save state to session storage
  const saveState = () => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
        historyStack,
        historyPosition
      }));
    } catch (e) {
      console.warn('Failed to save navigation state:', e);
    }
  };

  // Restore state from session storage
  const restoreState = () => {
    try {
      const savedState = sessionStorage.getItem(STORAGE_KEY);
      if (!savedState) return false;

      const { historyStack: savedStack, historyPosition: savedPosition } = JSON.parse(savedState);
      
      // Validate saved data
      if (!Array.isArray(savedStack) || typeof savedPosition !== 'number') {
        return false;
      }

      const currentUrl = window.location.href;
      
      // Find current URL in saved history
      const urlIndex = savedStack.indexOf(currentUrl);
      if (urlIndex !== -1) {
        historyStack = savedStack;
        historyPosition = urlIndex;
      } else {
        // Current URL not in history, append it
        historyStack = [...savedStack, currentUrl];
        historyPosition = historyStack.length - 1;
      }

      // Clear saved state
      sessionStorage.removeItem(STORAGE_KEY);
      return true;
    } catch (e) {
      console.warn('Failed to restore navigation state:', e);
      return false;
    }
  };

  // Update history state for new navigation
  const updateHistoryState = () => {
    const currentUrl = window.location.href;
    
    // Skip if URL hasn't changed
    if (historyStack[historyPosition] === currentUrl) {
      return;
    }

    // Remove any forward history and add new URL
    historyStack = historyStack.slice(0, historyPosition + 1);
    historyStack.push(currentUrl);
    historyPosition = historyStack.length - 1;
    
    sendNavigationState();
  };

  // Handle browser back/forward navigation
  const handlePopState = () => {
    const currentUrl = window.location.href;
    const urlIndex = historyStack.indexOf(currentUrl);
    
    if (urlIndex !== -1) {
      historyPosition = urlIndex;
    } else {
      // URL not in our history, treat as new navigation
      updateHistoryState();
    }
    
    sendNavigationState();
  };

  // Navigation command handlers
  const navigationHandlers = {
    back: () => {
      if (historyPosition > 0) {
        historyPosition--;
        window.history.back();
        // sendNavigationState will be called by popstate event
      }
    },
    
    forward: () => {
      if (historyPosition < historyStack.length - 1) {
        historyPosition++;
        window.history.forward();
        // sendNavigationState will be called by popstate event
      }
    },
    
    refresh: () => {
      saveState();
      window.location.reload();
    }
  };

  // Listen for navigation commands from parent
  const handleMessage = (event) => {
    if (event.data?.type === 'navigation-command') {
      const handler = navigationHandlers[event.data.action];
      if (handler) {
        handler();
      }
    }
  };

  // Initialize the navigation system
  const initialize = () => {
    if (isInitialized) return;
    
    // Try to restore state, fallback to default
    if (!restoreState()) {
      initializeState();
    }
    
    // Set up event listeners
    window.addEventListener('message', handleMessage);
    window.addEventListener('popstate', handlePopState);
    
    // Override history methods for SPA support
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;
    
    history.pushState = function(...args) {
      originalPushState.apply(this, args);
      updateHistoryState();
    };
    
    history.replaceState = function(...args) {
      originalReplaceState.apply(this, args);
      updateHistoryState();
    };
    
    isInitialized = true;
    sendNavigationState();
  };

  // Start initialization
  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', initialize);
  } else {
    initialize();
  }

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    window.removeEventListener('message', handleMessage);
    window.removeEventListener('popstate', handlePopState);
  });

})();