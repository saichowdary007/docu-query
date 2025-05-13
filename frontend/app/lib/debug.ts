/**
 * Debug utilities for DocuQuery-AI
 */

// Enable/disable debug logging (set to true during troubleshooting)
export const DEBUG_ENABLED = true;

// Debug logger
export const debugLog = (message: string, ...args: any[]) => {
  if (DEBUG_ENABLED) {
    console.log(`[DEBUG] ${message}`, ...args);
  }
};

// Log with visual distinction for important events
export const debugWarn = (message: string, ...args: any[]) => {
  if (DEBUG_ENABLED) {
    console.warn(`[DEBUG-WARN] ${message}`, ...args);
  }
};

// Track file selection events
export const logFileSelection = (filename: string | null, source: string) => {
  if (DEBUG_ENABLED) {
    console.log(`%c[FILE SELECTION] ${source}: ${filename || 'none'}`, 
      'background: #4b5563; color: #fff; padding: 2px 4px; border-radius: 2px;');
  }
}; 