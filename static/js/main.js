// API Base URL
const API_BASE = "/api";

// DOM Elements
const uploadForm = document.getElementById("uploadForm");
const pdfFile = document.getElementById("pdfFile");
const submitBtn = document.getElementById("submitBtn");
const progressContainer = document.getElementById("progressContainer");
const progressBar = document.getElementById("progressBar");
const progressPercent = document.getElementById("progressPercent");
const resultContainer = document.getElementById("resultContainer");
const successResult = document.getElementById("successResult");
const errorResult = document.getElementById("errorResult");
const infoResult = document.getElementById("infoResult");
const errorMessage = document.getElementById("errorMessage");
const infoMessage = document.getElementById("infoMessage");
const successDetails = document.getElementById("successDetails");
const modal = document.getElementById("modal");
const modalTitle = document.getElementById("modalTitle");
const modalContent = document.getElementById("modalContent");

// Event Listeners
document.addEventListener("DOMContentLoaded", () => {
  uploadForm.addEventListener("submit", handleUpload);
  refreshStats();
  loadRecentLogs();

  // Refresh stats every 30 seconds
  setInterval(refreshStats, 30000);
  setInterval(loadRecentLogs, 30000);
});

/**
 * Handle PDF file upload and extraction with real-time progress
 */
async function handleUpload(e) {
  e.preventDefault();

  const file = pdfFile.files[0];

  if (!file) {
    showError("Please select a PDF file");
    return;
  }

  if (file.type !== "application/pdf") {
    showError("Please select a valid PDF file");
    return;
  }

  if (file.size > 50 * 1024 * 1024) {
    showError("File is too large (max 50MB)");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    showProgress(true);
    submitBtn.disabled = true;

    // Start realistic progress
    let progress = 0;
    const progressInterval = setInterval(() => {
      if (progress < 85) {
        // Slower progress initially, faster near end
        const increment = Math.random() * (85 - progress) * 0.05;
        progress += increment;
        updateProgress(Math.min(progress, 85));
      }
    }, 300);

    const response = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });

    clearInterval(progressInterval);
    updateProgress(95); // Almost done

    const data = await response.json();

    // Simulate final processing
    await new Promise((resolve) => setTimeout(resolve, 500));
    updateProgress(100);

    if (response.ok && data.status === "success") {
      showSuccess(data.data);
      uploadForm.reset();

      // Refresh data with slight delay
      await new Promise((resolve) => setTimeout(resolve, 500));
      refreshStats();
      loadRecentLogs();
    } else {
      showError(data.message || data.error || "Upload failed");
    }
  } catch (error) {
    console.error("Upload error:", error);
    showError(error.message || "Network error during upload");
  } finally {
    setTimeout(() => {
      showProgress(false);
      submitBtn.disabled = false;
    }, 1000);
  }
}

/**
 * Show success message with extraction details
 */
function showSuccess(data) {
  hideAllMessages();
  successResult.classList.remove("hidden");

  const details = successDetails;
  details.innerHTML = "";

  if (data.filename) {
    details.appendChild(createDetailItem("📄 File", data.filename));
  }

  if (data.stats) {
    details.appendChild(createDetailItem("🏛️ States", data.stats.total_states));
    details.appendChild(createDetailItem("📍 LGAs", data.stats.total_lgas));
    details.appendChild(createDetailItem("🗳️ Wards", data.stats.total_wards));
  }

  if (data.json_file) {
    const link = document.createElement("a");
    link.href = "#";
    link.className = "text-green-600 hover:text-green-800 underline";
    link.textContent = "📥 Download JSON";
    link.onclick = (e) => {
      e.preventDefault();
      showInfo(`JSON file saved to: ${data.json_file}`);
    };
    const item = document.createElement("div");
    item.className = "flex justify-between items-center";
    item.appendChild(document.createTextNode("Export"));
    item.appendChild(link);
    details.appendChild(item);
  }
}

/**
 * Show error message
 */
function showError(message) {
  hideAllMessages();
  errorResult.classList.remove("hidden");
  errorMessage.textContent = message;
}

/**
 * Show info message
 */
function showInfo(message) {
  hideAllMessages();
  infoResult.classList.remove("hidden");
  infoMessage.textContent = message;
}

/**
 * Hide all messages
 */
function hideAllMessages() {
  successResult.classList.add("hidden");
  errorResult.classList.add("hidden");
  infoResult.classList.add("hidden");
}

/**
 * Create detail item element
 */
function createDetailItem(label, value) {
  const div = document.createElement("div");
  div.className = "flex justify-between items-center";
  div.innerHTML = `
    <span>${label}:</span>
    <strong>${value}</strong>
  `;
  return div;
}

/**
 * Show/hide progress bar
 */
function showProgress(show) {
  if (show) {
    progressContainer.classList.remove("hidden");
    updateProgress(0);
  } else {
    progressContainer.classList.add("hidden");
  }
}

/**
 * Update progress bar
 */
function updateProgress(percent) {
  progressBar.style.width = percent + "%";
  progressPercent.textContent = Math.round(percent) + "%";
}

/**
 * Refresh database statistics
 */
async function refreshStats() {
  try {
    const response = await fetch(`${API_BASE}/status`);
    const data = await response.json();

    if (data.stats) {
      document.getElementById("statStates").textContent =
        data.stats.total_states || 0;
      document.getElementById("statLgas").textContent =
        data.stats.total_lgas || 0;
      document.getElementById("statWards").textContent =
        data.stats.total_wards || 0;
      document.getElementById("statExtractions").textContent =
        data.stats.total_extractions || 0;
    }
  } catch (error) {
    console.error("Error fetching stats:", error);
  }
}

/**
 * Load recent extraction logs
 */
async function loadRecentLogs() {
  try {
    const response = await fetch(`${API_BASE}/status`);
    const data = await response.json();

    const logsContainer = document.getElementById("recentLogs");

    if (data.recent_logs && data.recent_logs.length > 0) {
      logsContainer.innerHTML = "";

      data.recent_logs.slice(0, 5).forEach((log) => {
        const logEl = document.createElement("div");
        logEl.className = `text-sm p-3 rounded ${
          log.status === "success"
            ? "bg-green-50 border-l-2 border-green-500"
            : log.status === "failed"
            ? "bg-red-50 border-l-2 border-red-500"
            : "bg-yellow-50 border-l-2 border-yellow-500"
        }`;

        const statusEmoji =
          log.status === "success" ? "✓" : log.status === "failed" ? "✕" : "⏳";
        const filenameShort =
          log.filename.length > 20
            ? log.filename.substring(0, 17) + "..."
            : log.filename;

        logEl.innerHTML = `
          <div class="font-semibold">${statusEmoji} ${filenameShort}</div>
          <div class="text-xs text-gray-600">
            LGAs: ${log.lgas_extracted} | Wards: ${log.wards_extracted}
          </div>
          <div class="text-xs text-gray-500">
            ${formatTime(log.completed_at || log.created_at)}
          </div>
          ${
            log.error
              ? `<div class="text-xs text-red-600 mt-1">${log.error}</div>`
              : ""
          }
        `;

        logsContainer.appendChild(logEl);
      });
    } else {
      logsContainer.innerHTML =
        '<p class="text-sm text-gray-500">No extractions yet</p>';
    }
  } catch (error) {
    console.error("Error loading logs:", error);
  }
}

/**
 * Format time for display
 */
function formatTime(isoTime) {
  if (!isoTime) return "N/A";

  const date = new Date(isoTime);
  const now = new Date();
  const diff = now - date;

  // Less than a minute
  if (diff < 60000) return "Just now";

  // Less than an hour
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000);
    return `${minutes}m ago`;
  }

  // Less than a day
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000);
    return `${hours}h ago`;
  }

  // Default format
  return date.toLocaleDateString();
}

/**
 * Search data
 */
async function searchData() {
  const query = prompt("Search for state, LGA, or ward:");
  if (!query) return;

  try {
    const response = await fetch(
      `${API_BASE}/search?q=${encodeURIComponent(query)}`
    );
    const data = await response.json();

    let html = '<div class="space-y-4">';

    if (data.states && data.states.length > 0) {
      html += "<div>";
      html += '<h4 class="font-semibold text-blue-600 mb-2">States</h4>';
      data.states.forEach((state) => {
        html += `<div class="text-sm p-2 bg-blue-50 rounded mb-1">${state.name} (${state.code})</div>`;
      });
      html += "</div>";
    }

    if (data.lgas && data.lgas.length > 0) {
      html += "<div>";
      html += '<h4 class="font-semibold text-green-600 mb-2">LGAs</h4>';
      data.lgas.forEach((lga) => {
        html += `<div class="text-sm p-2 bg-green-50 rounded mb-1">${lga.name} (${lga.code}) - ${lga.state}</div>`;
      });
      html += "</div>";
    }

    if (data.wards && data.wards.length > 0) {
      html += "<div>";
      html += '<h4 class="font-semibold text-purple-600 mb-2">Wards</h4>';
      data.wards.forEach((ward) => {
        html += `<div class="text-sm p-2 bg-purple-50 rounded mb-1">${ward.name} (${ward.code}) - ${ward.lga}</div>`;
      });
      html += "</div>";
    }

    if (!data.states?.length && !data.lgas?.length && !data.wards?.length) {
      html += '<p class="text-gray-500">No results found</p>';
    }

    html += "</div>";

    showModal("Search Results", html);
  } catch (error) {
    console.error("Search error:", error);
    showError("Search failed: " + error.message);
  }
}

/**
 * Export all data
 */
async function exportData() {
  try {
    showInfo("Preparing export...");

    const response = await fetch(`${API_BASE}/export`);
    const data = await response.json();

    // Create blob
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = window.URL.createObjectURL(blob);

    // Download
    const a = document.createElement("a");
    a.href = url;
    a.download = `xtractor_export_${
      new Date().toISOString().split("T")[0]
    }.json`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    showInfo("Export downloaded successfully");
  } catch (error) {
    console.error("Export error:", error);
    showError("Export failed: " + error.message);
  }
}

/**
 * View all states
 */
async function viewStates() {
  try {
    const response = await fetch(`${API_BASE}/states`);
    const states = await response.json();

    let html = '<div class="space-y-2">';

    if (states.length > 0) {
      states.forEach((state) => {
        html += `
          <div class="p-3 bg-blue-50 rounded cursor-pointer hover:bg-blue-100" onclick="viewStateLGAs(${state.id}, '${state.name}')">
            <div class="font-semibold text-blue-700">${state.name}</div>
            <div class="text-xs text-gray-600">Code: ${state.code} | LGAs: ${state.lga_count}</div>
          </div>
        `;
      });
    } else {
      html += '<p class="text-gray-500">No states found</p>';
    }

    html += "</div>";

    showModal("All States", html);
  } catch (error) {
    console.error("Error fetching states:", error);
    showError("Failed to fetch states: " + error.message);
  }
}

/**
 * View LGAs for a state
 */
async function viewStateLGAs(stateId, stateName) {
  try {
    const response = await fetch(`${API_BASE}/states/${stateId}/lgas`);
    const lgas = await response.json();

    let html = '<div class="space-y-2">';

    if (lgas.length > 0) {
      lgas.forEach((lga) => {
        html += `
          <div class="p-3 bg-green-50 rounded cursor-pointer hover:bg-green-100" onclick="viewLGAWards(${lga.id}, '${lga.name}')">
            <div class="font-semibold text-green-700">${lga.name}</div>
            <div class="text-xs text-gray-600">Code: ${lga.code} | Wards: ${lga.ward_count}</div>
          </div>
        `;
      });
    } else {
      html += '<p class="text-gray-500">No LGAs found</p>';
    }

    html += "</div>";

    showModal(`LGAs in ${stateName}`, html);
  } catch (error) {
    console.error("Error fetching LGAs:", error);
    showError("Failed to fetch LGAs: " + error.message);
  }
}

/**
 * View wards for an LGA
 */
async function viewLGAWards(lgaId, lgaName) {
  try {
    const response = await fetch(`${API_BASE}/lgas/${lgaId}/wards`);
    const wards = await response.json();

    let html = '<div class="space-y-2">';

    if (wards.length > 0) {
      wards.forEach((ward) => {
        html += `
          <div class="p-2 bg-purple-50 rounded">
            <div class="font-semibold text-purple-700">${ward.name}</div>
            <div class="text-xs text-gray-600">Code: ${ward.code}</div>
          </div>
        `;
      });
    } else {
      html += '<p class="text-gray-500">No wards found</p>';
    }

    html += "</div>";

    showModal(`Wards in ${lgaName}`, html);
  } catch (error) {
    console.error("Error fetching wards:", error);
    showError("Failed to fetch wards: " + error.message);
  }
}

/**
 * Show modal with content
 */
function showModal(title, content) {
  modalTitle.textContent = title;
  modalContent.innerHTML = content;
  modal.classList.remove("hidden");
}

/**
 * Close modal
 */
function closeModal() {
  modal.classList.add("hidden");
}

/**
 * Close modal on outside click
 */
modal.addEventListener("click", (e) => {
  if (e.target === modal) {
    closeModal();
  }
});

// Log initialization
console.log("Xtractor frontend initialized");
