const STORAGE_KEY = 'cc_dashboard_summary_v1';
const MAX_AGE_MS = 90 * 1000;

export function readDashboardCache() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const { at, payload } = JSON.parse(raw);
    if (typeof at !== 'number' || !payload) return null;
    if (Date.now() - at > MAX_AGE_MS) return null;
    return payload;
  } catch {
    return null;
  }
}

export function writeDashboardCache(payload) {
  try {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ at: Date.now(), payload })
    );
  } catch {
    // ignore quota / private mode
  }
}

export function clearDashboardCache() {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
