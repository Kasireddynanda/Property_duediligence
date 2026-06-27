const PRODUCTION_API = 'https://property-duediligence.onrender.com';
const LOCAL_API = 'http://localhost:8000';

function isLocalHost(): boolean {
  if (typeof window === 'undefined') return false;
  const host = window.location.hostname;
  return host === 'localhost' || host === '127.0.0.1';
}

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || (isLocalHost() ? LOCAL_API : PRODUCTION_API);
