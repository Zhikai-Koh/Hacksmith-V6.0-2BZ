(function () {
  const TELEMETRY_ENDPOINT = "/telemetry";
  const SEND_ON_INTERVAL_MS = 0; 

  const startTime = performance.now();
  let timeOnPage = 0;

  let mousePathLength = 0;
  let lastMouseX = null;
  let lastMouseY = null;
  let mouseEventCount = 0;

  let clickCount = 0;
  let maxScrollY = 0;
  
  let maxNormalizedDeviation = 0; 

  let firstActionTime = null;
  let firstKeystrokeTime = null;
  const keystrokeTimestamps = [];
  const scrollTimestamps = [];
  const mouseMoveTimestamps = [];

  function now() {
    return performance.now();
  }

  function markFirstAction() {
    if (firstActionTime === null) {
      firstActionTime = now() - startTime;
    }
  }

  function isActionableElement(element) {
      if (!element || !element.tagName) return false;
      const tagName = element.tagName.toLowerCase();
      // Only measure deviation for elements a user would intentionally target
      return ['a', 'button', 'input', 'textarea', 'select', 'li'].includes(tagName) || element.hasAttribute('onclick');
  }

  function countBursts(timestamps, gapMs) {
      if (!timestamps.length) return 0;
      let bursts = 1;
      for (let i = 1; i < timestamps.length; i++) {
        if (timestamps[i] - timestamps[i - 1] > gapMs) {
          bursts++;
        }
      }
      return bursts;
    }

  
  window.addEventListener("mousemove", (e) => {
    markFirstAction();
    mouseEventCount++;
    mouseMoveTimestamps.push(now());

    if (lastMouseX !== null && lastMouseY !== null) {
      const dx = e.clientX - lastMouseX;
      const dy = e.clientY - lastMouseY;
      mousePathLength += Math.sqrt(dx * dx + dy * dy);
    }

    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
  });

  window.addEventListener("click", (e) => {
    markFirstAction();
    clickCount++;
    
    const targetElement = e.target;
    
    if (targetElement && targetElement.getBoundingClientRect && isActionableElement(targetElement)) {
        const rect = targetElement.getBoundingClientRect();
        
        if (rect.width === 0 || rect.height === 0) {
            return;
        }

        const centerX = rect.left + (rect.width / 2);
        const centerY = rect.top + (rect.height / 2);

        const clickX = e.clientX;
        const clickY = e.clientY;
        
        //Deviation Distance (Euclidean Distance from center)
        const dx = clickX - centerX;
        const dy = clickY - centerY;
        const deviationDistance = Math.sqrt(dx * dx + dy * dy);

        // Maximum Possible Radius
        const maxRadiusX = rect.width / 2;
        const maxRadiusY = rect.height / 2;
        const maxDeviationRadius = Math.sqrt(maxRadiusX * maxRadiusX + maxRadiusY * maxRadiusY);

        // 3. Normalized Deviation
        let normalizedDeviation = 0;
        if (maxDeviationRadius > 0) {
            normalizedDeviation = deviationDistance / maxDeviationRadius;
            normalizedDeviation = Math.min(1.0, normalizedDeviation); 
        }

        if (normalizedDeviation > maxNormalizedDeviation) {
            maxNormalizedDeviation = normalizedDeviation;
        }
    }
  });

  window.addEventListener("scroll", () => {
    markFirstAction();
    scrollTimestamps.push(now());
    const y = window.scrollY || window.pageYOffset || document.documentElement.scrollTop || 0;
    if (y > maxScrollY) {
      maxScrollY = y;
    }
  }, { passive: true });

  window.addEventListener("keydown", (e) => {
    if (!e.metaKey && !e.ctrlKey && !e.altKey && !e.shiftKey) {
        markFirstAction();
        const t = now() - startTime;
        if (firstKeystrokeTime === null) {
          firstKeystrokeTime = t;
        }
        keystrokeTimestamps.push(t);
    }
  });


  function collectTelemetry() {
    timeOnPage = now() - startTime;

    return {
      avg_speed: (mousePathLength / Math.max(timeOnPage, 0.001)),
      page_url: location.href,
      time_on_page_ms: Math.round(timeOnPage),
      time_to_first_action_ms: firstActionTime !== null ? Math.round(firstActionTime) : null,
      time_to_first_keystroke_ms: firstKeystrokeTime !== null ? Math.round(firstKeystrokeTime) : null,

      mouse_path_length_px: Math.round(mousePathLength),
      mouse_event_count: mouseEventCount,
      click_count: clickCount,
      max_scroll_y: maxScrollY,
      
      max_normalized_deviation: parseFloat(maxNormalizedDeviation.toFixed(4)),

      keystroke_count: keystrokeTimestamps.length,
      keystroke_timestamps_ms: keystrokeTimestamps, 
      
      scroll_bursts: countBursts(scrollTimestamps, 400),
      mouse_move_bursts: countBursts(mouseMoveTimestamps, 400),
      user_agent: navigator.userAgent,
      timestamp_ms: Date.now()
    };
  }

  function sendTelemetry(reason) {
    const payload = collectTelemetry();
    payload.send_reason = reason;
    const body = JSON.stringify(payload);

    console.log("Sending telemetry:", payload);

    if (navigator.sendBeacon && (reason === "beforeunload" || reason === "pagehide")) {
      navigator.sendBeacon(TELEMETRY_ENDPOINT, body);
    } else {
      fetch(TELEMETRY_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        keepalive: true,
        body
      }).catch(() => {});
    }
  }

  window.addEventListener("pagehide", () => {
    sendTelemetry("pagehide");
  });

  window.sendBehaviourTelemetry = function (reason = "manual") {
    sendTelemetry(reason);
  };
})();