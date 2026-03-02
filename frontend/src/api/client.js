/**
 * API Client - Centralized HTTP client with error handling
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * API error class for better error handling
 */
export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Make a GET request to the API
 * @param {string} endpoint - API endpoint path
 * @param {Object} params - Query parameters
 * @returns {Promise<any>} - Response data
 */
export async function get(endpoint, params = {}) {
  const url = new URL(`${BASE_URL}${endpoint}`, window.location.origin);
  
  // Add query parameters
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      url.searchParams.append(key, value);
    }
  });
  
  try {
    const response = await fetch(url.toString());
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `HTTP ${response.status}`,
        response.status,
        errorData
      );
    }
    
    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(error.message, 0, null);
  }
}

/**
 * Make a POST request to the API
 * @param {string} endpoint - API endpoint path
 * @param {Object} data - Request body
 * @returns {Promise<any>} - Response data
 */
export async function post(endpoint, data = {}) {
  const url = `${BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `HTTP ${response.status}`,
        response.status,
        errorData
      );
    }
    
    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(error.message, 0, null);
  }
}

/**
 * Stream NDJSON from an endpoint
 * @param {string} endpoint - API endpoint path
 * @returns {AsyncGenerator<Object>} - Stream of JSON objects
 */
export async function* streamNDJSON(endpoint) {
  const url = `${BASE_URL}${endpoint}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new ApiError(`HTTP ${response.status}`, response.status, null);
  }
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    
    // Keep the last incomplete line in the buffer
    buffer = lines.pop() || '';
    
    for (const line of lines) {
      if (line.trim()) {
        try {
          yield JSON.parse(line);
        } catch (e) {
          console.warn('Failed to parse NDJSON line:', line);
        }
      }
    }
  }
  
  // Process any remaining data
  if (buffer.trim()) {
    try {
      yield JSON.parse(buffer);
    } catch (e) {
      console.warn('Failed to parse final NDJSON line:', buffer);
    }
  }
}

export default {
  get,
  post,
  streamNDJSON,
  ApiError,
};

