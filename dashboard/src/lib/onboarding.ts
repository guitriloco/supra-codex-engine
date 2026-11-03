export const ONBOARDING_STORAGE_KEY = 'supra-codex:onboarding-complete'

/** Fired on `window` when the tour is re-opened from Settings. */
export const ONBOARDING_RESET_EVENT = 'supra-codex:onboarding-reset'

/** First-run detection: the tour shows only until it has been completed once. */
export function isOnboardingComplete(): boolean {
  try {
    return localStorage.getItem(ONBOARDING_STORAGE_KEY) === 'true'
  } catch {
    // Storage unavailable (private mode) — treat as complete so we never nag.
    return true
  }
}

export function completeOnboarding(): void {
  try {
    localStorage.setItem(ONBOARDING_STORAGE_KEY, 'true')
  } catch {
    // Ignore write failures — the wizard will simply re-appear next visit.
  }
}

/** Wipe the completion flag and re-open the wizard immediately. */
export function resetOnboarding(): void {
  try {
    localStorage.removeItem(ONBOARDING_STORAGE_KEY)
  } catch {
    // Ignore — the in-memory event below still re-opens the tour.
  }
  window.dispatchEvent(new Event(ONBOARDING_RESET_EVENT))
}
