const POLL_URL      = "{POLL_URL}";
const POLL_INTERVAL = "{POLL_INTERVAL}";
const PAGE_TITLE    = "{PAGE_TITLE}";

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


function addNotification({ title, detail, timestamp, isUnread = false }) {
  const list = document.getElementById("notification-list");
  if (!list) return;

  const card = document.createElement("div");
  card.className = `notification-card ${isUnread ? "unread" : ""}`;
  card.innerHTML = `
    <h4 class="notification-title">${title}</h4>
    <p class="notification-detail">${detail}</p>
    <span class="notification-time" data-timestamp="${timestamp}">${timeAgo(new Date(timestamp))}</span>
    <button class="copy-btn" title="Copy detail">📋</button>
  `;

  card.querySelector(".copy-btn").addEventListener("click", (e) => {
    navigator.clipboard.writeText(detail).then(() => {
      e.target.innerText = "✅";
      setTimeout(() => (e.target.innerText = "📋"), 1500);
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
      list.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">No notifications</p>';
    } else {
      notifications.forEach((noti) => addNotification(noti));
    }
  } catch (error) {
    console.error("Fetch failed:", error);
    list.innerHTML = `<p style="color: red; text-align: center; padding: 20px;">Error: ${error.message}<br>Make sure server is running on port 8001</p>`;
  }
}

function startPolling() {
  stopPolling();
  fetchNotifications();
  pollTimer = setInterval(fetchNotifications, POLL_INTERVAL);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function main() {
  document.getElementById("reload-btn").addEventListener("click", fetchNotifications);
  document.title = PAGE_TITLE;
  startPolling();
}

main();