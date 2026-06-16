const POLL_URL      = POLL_ENDPOINT;
const POLL_INTERVAL = "60";
const PAGE_TITLE    = "Magic Link Push Notification";

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
      list.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">No notifications</p>';
    } else {
      notifications.forEach((noti) => addNotification(noti));
    }
  } catch (error) {
    console.error("Fetch failed:", error);
    list.innerHTML = `<p style="color: red; text-align: center; padding: 20px;">Error: ${error.message}<br> Check if server is actually running</p>`;
  }
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
  document.getElementById("reload-btn").addEventListener("click", fetchNotifications);
  document.title = PAGE_TITLE;
  startPolling();
}

main();