/**
 * Axios API Client
 * Centralized HTTP client with JWT auth, auto-refresh, and error handling.
 */

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import toast from 'react-hot-toast';

const BASE_URL = import.meta.env.VITE_API_URL || '/api';

// Create Axios instance
const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 60000, // 60s for large PDF uploads
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─── Request Interceptor: Attach JWT ─────────────────────────────────────────

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Response Interceptor: Handle Errors & Auto-Refresh ──────────────────────

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Auto-refresh on 401 (token expired)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        } catch {
          // Refresh failed → force logout
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      } else {
        window.location.href = '/login';
      }
    }

    // Show user-friendly error messages
    const message = error.response?.data?.detail || error.message || 'An error occurred';
    if (error.response?.status !== 401) {
      toast.error(message);
    }

    return Promise.reject(error);
  }
);

export default api;

// ─── Typed API Helper Functions ───────────────────────────────────────────────

export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),

  register: (data: { email: string; username: string; password: string; full_name?: string }) =>
    api.post('/auth/register', data),

  refresh: (refreshToken: string) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),

  me: () => api.get('/auth/me'),

  logout: () => api.post('/auth/logout'),
};

export const documentsAPI = {
  list: (page = 1, pageSize = 20, status?: string) => {
    const params: Record<string, string | number> = { page, page_size: pageSize };
    if (status) params.status = status;
    return api.get('/documents', { params });
  },

  get: (id: number) => api.get(`/documents/${id}`),

  upload: (files: File[], folderName?: string, onProgress?: (pct: number) => void) => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    if (folderName) formData.append('folder_name', folderName);

    return api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
      timeout: 5 * 60 * 1000, // 5 min timeout for large uploads
    });
  },

  getProgress: (sessionId: string) =>
    api.get(`/upload/${sessionId}/progress`),

  reprocess: (id: number) => api.post(`/documents/${id}/reprocess`),

  delete: (id: number) => api.delete(`/documents/${id}`),
};

export const searchAPI = {
  search: (params: Record<string, string | number | undefined>) =>
    api.get('/search', { params }),

  searchPost: (body: object) => api.post('/search', body),

  suggestions: (q: string, field: string) =>
    api.get('/search/suggestions', { params: { q, field } }),

  filterOptions: () => api.get('/search/filters'),
};

export const exportAPI = {
  export: (request: object) =>
    api.post('/export', request, { responseType: 'blob' }),
};

export const statsAPI = {
  getStats: () => api.get('/stats'),
};
