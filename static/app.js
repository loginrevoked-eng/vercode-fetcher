// Extract username and provider from URL path
// URL format: /username/provider (will append @gmail.com)
const pathParts = window.location.pathname.split('/').filter(p => p);
const username = pathParts[0] || '';
const provider = pathParts[1] || '';
const subscriber = `${username}@gmail.com`;

const POLL_INTERVAL = 60; // seconds
const POLL_URL = `/api/notifications/${username}/${provider}`;
const PAGE_TITLE = `${provider.charAt(0).toUpperCase() + provider.slice(1)} - ${subscriber}`;

let pollTimer;

function timeAgo(date) {
  const seconds   = Math.floor((new Date() - date) / 1000);
  const intervals = {
    year:   31536000,
    month:   2592000,
    day:       86400,
    hour:       3600,
    minute:       60,
  };

  for (const [unit, value] of Object.entries(intervals)) {
    const count = Math.floor(seconds / value);
    if (count >= 1) return `${count} ${unit}${count > 1 ? "s" : ""} ago`;
  }

  return seconds <= 5 ? "Just now" : `${seconds} seconds ago`;
}


function addNotification({ title, detail, timestamp, read }) {
  const list = document.getElementById("notification-list");
  if (!list) return;

  const isUnread = !read;
  const card = document.createElement("div");
  card.className = `notification-card ${isUnread ? "unread" : ""}`;
  card.innerHTML = `
    <div class="notification-header">
      <div class="notification-title">
        <span class="unread-badge"></span>
        ${title}
      </div>
      <span class="notification-time" data-timestamp="${timestamp}">${timeAgo(new Date(timestamp))}</span>
    </div>
    <div class="notification-detail">${detail}</div>
    <div class="notification-actions">
      <button class="action-btn copy-btn">Copy Link</button>
    </div>
  `;

  card.querySelector(".copy-btn").addEventListener("click", (e) => {
    navigator.clipboard.writeText(detail).then(() => {
      e.target.innerText = "Copied";
      e.target.classList.add("copied");
      setTimeout(() => {
        e.target.innerText = "Copy Link";
        e.target.classList.remove("copied");
      }, 2000);
    });
  });

  list.appendChild(card);
}


async function fetchNotifications() {
  const list = document.getElementById("notification-list");

  try {
    const response = await fetch(POLL_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const notifications = await response.json();
    list.innerHTML = "";

    if (notifications.length === 0) {
      list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📭</div><div class="empty-state-text">No notifications yet</div></div>';
    } else {
      notifications.reverse().forEach((noti) => addNotification(noti));
    }
  } catch (error) {
    console.error("Fetch failed:", error);
    list.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text" style="color: #d93025;">Error: ${error.message}<br><small>Check if server is running</small></div></div>`;
  }
}

function updatePageInfo() {
  document.title = PAGE_TITLE;
  document.querySelector('.app-bar h1').innerHTML = `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" fill="#5f6368"/>
    </svg>
    ${provider.charAt(0).toUpperCase() + provider.slice(1)} Magic Links
  `;
  
  document.querySelector('.config-badge').innerHTML = `
    <div class="config-badge-text">
      <span>${subscriber}</span>
      <span class="config-divider">•</span>
      <span>${provider}</span>
      <span class="config-divider">•</span>
      <span>Every ${POLL_INTERVAL}s</span>
    </div>
  `;
  
  document.querySelector('.status-text').textContent = `Auto-refresh every ${POLL_INTERVAL}s`;
}

function startPolling() {
  stopPolling();
  fetchNotifications();
  pollTimer = setInterval(fetchNotifications, POLL_INTERVAL * 1000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function main() {
  updatePageInfo();
  document.getElementById("reload-btn").addEventListener("click", fetchNotifications);
  startPolling();
}

main();