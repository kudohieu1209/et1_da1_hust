// Local Vite proxies /api on the frontend origin so HttpOnly SameSite cookies
// work with either localhost or 127.0.0.1. Deployments may set an explicit base.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

/** Phát ra khi backend trả 401 (chưa đăng nhập / phiên hết hạn). App lắng nghe để về màn đăng nhập. */
export const UNAUTHORIZED_EVENT = 'hust:unauthorized';

export function apiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

/**
 * fetch kèm cookie phiên đăng nhập (HttpOnly). Mọi lời gọi backend phải đi qua
 * hàm này, nếu không trình duyệt không gửi cookie và backend trả 401.
 */
export async function apiFetch(url, options = {}) {
  const response = await fetch(url, { ...options, credentials: 'include' });
  // Sai mật khẩu ở /api/auth/login cũng là 401 nhưng không phải "hết phiên".
  if (response.status === 401 && !url.includes('/api/auth/')) {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
  return response;
}

/** Lấy thông báo lỗi dễ đọc từ phản hồi FastAPI ({detail: string | [...]}). */
export async function readError(response, fallback) {
  try {
    const data = await response.json();
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.detail) && data.detail[0]?.msg) return data.detail[0].msg;
  } catch {
    // phản hồi không phải JSON
  }
  return fallback;
}
