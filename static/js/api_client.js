/**
 * Cliente genérico para consumir la API de FastAPI
 */
const API_BASE = '/api/v1';

class ApiClient {
    static async get(endpoint, params = {}) {
        const url = new URL(`${API_BASE}${endpoint}`, window.location.origin);
        Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
        
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('API GET Error:', error);
            throw error;
        }
    }

    static async post(endpoint, body = {}) {
        const url = new URL(`${API_BASE}${endpoint}`, window.location.origin);
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(body)
            });
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API POST Error:', error);
            throw error;
        }
    }
}
