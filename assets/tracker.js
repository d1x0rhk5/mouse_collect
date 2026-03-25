(function () {
  const endpoint = "/getter";
  const intervalMs = 120;
  const sessionKey = "webarena-tracker-session-id";

  function readSessionId() {
    try {
      const existing = window.sessionStorage.getItem(sessionKey);
      if (existing) {
        return existing;
      }

      const created = "sess-" + Date.now() + "-" + Math.random().toString(36).slice(2, 10);
      window.sessionStorage.setItem(sessionKey, created);
      return created;
    } catch (error) {
      return "sess-" + Date.now() + "-" + Math.random().toString(36).slice(2, 10);
    }
  }

  function describeTarget(target) {
    if (!(target instanceof Element)) {
      return null;
    }

    const tag = target.tagName.toLowerCase();
    const id = target.id ? "#" + target.id : "";
    const className = typeof target.className === "string"
      ? "." + target.className.trim().split(/\s+/).filter(Boolean).slice(0, 3).join(".")
      : "";
    const name = target.getAttribute("name");
    const role = target.getAttribute("role");
    const href = target.getAttribute("href");

    return {
      tag: tag,
      selector: tag + id + className,
      name: name || null,
      role: role || null,
      href: href || null
    };
  }

  const state = {
    sessionId: readSessionId(),
    lastMouse: null,
    clicks: [],
    inFlight: false
  };

  function snapshotPayload(reason) {
    return {
      sessionId: state.sessionId,
      reason: reason,
      capturedAt: new Date().toISOString(),
      page: {
        href: window.location.href,
        path: window.location.pathname + window.location.search,
        title: document.title
      },
      mouse: state.lastMouse,
      clicks: state.clicks.splice(0, state.clicks.length)
    };
  }

  function hasUsefulData(payload) {
    return Boolean(payload.mouse) || payload.clicks.length > 0;
  }

  function queueClick(event) {
    state.clicks.push({
      type: "click",
      at: new Date().toISOString(),
      clientX: event.clientX,
      clientY: event.clientY,
      pageX: event.pageX,
      pageY: event.pageY,
      button: event.button,
      target: describeTarget(event.target)
    });
  }

  function updateMouse(event) {
    state.lastMouse = {
      at: new Date().toISOString(),
      clientX: event.clientX,
      clientY: event.clientY,
      pageX: event.pageX,
      pageY: event.pageY,
      screenX: event.screenX,
      screenY: event.screenY
    };
  }

  function restoreClicks(payload) {
    if (payload.clicks.length > 0) {
      state.clicks = payload.clicks.concat(state.clicks);
    }
  }

  function sendPayload(payload, useBeacon) {
    if (!hasUsefulData(payload)) {
      return;
    }

    const body = JSON.stringify(payload);

    if (useBeacon && navigator.sendBeacon) {
      navigator.sendBeacon(endpoint, new Blob([body], { type: "application/json" }));
      return;
    }

    if (state.inFlight) {
      restoreClicks(payload);
      return;
    }

    state.inFlight = true;
    fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: body,
      keepalive: true,
      credentials: "same-origin"
    }).catch(function () {
      restoreClicks(payload);
    }).finally(function () {
      state.inFlight = false;
    });
  }

  function flush(reason, useBeacon) {
    sendPayload(snapshotPayload(reason), useBeacon);
  }

  document.addEventListener("mousemove", updateMouse, { passive: true });
  document.addEventListener("click", queueClick, true);
  window.addEventListener("beforeunload", function () {
    flush("beforeunload", true);
  });
  window.addEventListener("pagehide", function () {
    flush("pagehide", true);
  });
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") {
      flush("hidden", true);
    }
  });

  flush("page-enter", false);
  window.setInterval(function () {
    flush("interval", false);
  }, intervalMs);
})();
