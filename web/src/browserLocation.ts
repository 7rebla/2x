// Leaves the web UI for a page that Django serves itself (the admin).
// A module of its own, so that tests can replace it (jsdom cannot navigate).

/** Opens `path` of this server as a new page (full page load). */
export function openServerPage(path: string): void {
  window.location.assign(path);
}
