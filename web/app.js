const inputText = document.getElementById("input-text");
const outputText = document.getElementById("output-text");
const convertBtn = document.getElementById("convert-btn");
const copyBtn = document.getElementById("copy-btn");
const downloadBtn = document.getElementById("download-btn");
const errorEl = document.getElementById("error");
const pastePanel = document.getElementById("paste-panel");
const uploadPanel = document.getElementById("upload-panel");
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");

let currentMode = "xml2cli";

function getMode() {
  return document.querySelector('input[name="mode"]:checked').value;
}

function showError(message) {
  errorEl.textContent = message;
  errorEl.classList.remove("hidden");
}

function clearError() {
  errorEl.textContent = "";
  errorEl.classList.add("hidden");
}

function switchTab(tab) {
  document.querySelectorAll(".tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tab);
  });
  pastePanel.classList.toggle("hidden", tab !== "paste");
  uploadPanel.classList.toggle("hidden", tab !== "upload");
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => switchTab(button.dataset.tab));
});

document.querySelectorAll('input[name="mode"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    currentMode = getMode();
    inputText.placeholder =
      currentMode === "xml2cli"
        ? "粘贴 NETCONF XML..."
        : "粘贴 CLI 命令（每行一条）...";
  });
});

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  const file = event.dataTransfer.files[0];
  if (file) {
    readFile(file);
  }
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (file) {
    readFile(file);
  }
});

function readFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    inputText.value = reader.result;
    switchTab("paste");
  };
  reader.readAsText(file);
}

convertBtn.addEventListener("click", async () => {
  clearError();
  const content = inputText.value.trim();
  if (!content) {
    showError("请输入或上传内容");
    return;
  }

  const endpoint = currentMode === "xml2cli" ? "/api/xml2cli" : "/api/cli2xml";

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });

    const data = await response.json();
    if (!response.ok) {
      showError(data.detail || "转换失败");
      return;
    }

    if (data.errors && data.errors.length > 0) {
      const hasOutput =
        (currentMode === "xml2cli" && data.cli && data.cli.length > 0) ||
        (currentMode === "cli2xml" && data.xml);
      if (!hasOutput) {
        showError(data.errors.join("; "));
        outputText.value = "";
        return;
      }
    }

    outputText.value =
      currentMode === "xml2cli" ? (data.cli || []).join("\n") : data.xml || "";
  } catch (error) {
    showError(`请求失败: ${error.message}`);
  }
});

copyBtn.addEventListener("click", async () => {
  if (!outputText.value) {
    return;
  }
  await navigator.clipboard.writeText(outputText.value);
});

downloadBtn.addEventListener("click", () => {
  if (!outputText.value) {
    return;
  }
  const isXml = currentMode === "cli2xml";
  const blob = new Blob([outputText.value], {
    type: isXml ? "application/xml" : "text/plain",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = isXml ? "output.xml" : "output.cli";
  link.click();
  URL.revokeObjectURL(url);
});
