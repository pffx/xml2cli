document.addEventListener("DOMContentLoaded", () => {
  const inputText = document.getElementById("input-text");
  const outputText = document.getElementById("output-text");
  const convertBtn = document.getElementById("convert-btn");
  const clearBtn = document.getElementById("clear-btn");
  const copyBtn = document.getElementById("copy-btn");
  const downloadBtn = document.getElementById("download-btn");
  const errorEl = document.getElementById("error");
  const boardInfoEl = document.getElementById("board-info");
  const boardSelect = document.getElementById("board-select");
  const yangTreeAll = document.getElementById("yang-tree-all");
  const deviceHost = document.getElementById("device-host");
  const devicePort = document.getElementById("device-port");
  const deviceUser = document.getElementById("device-user");
  const devicePassword = document.getElementById("device-password");
  const deployBtn = document.getElementById("deploy-btn");
  const deployStatusEl = document.getElementById("deploy-status");
  const pastePanel = document.getElementById("paste-panel");
  const uploadPanel = document.getElementById("upload-panel");
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");

  let currentMode = "xml2cli";
  let lastDetectedBoard = null;

  const DEFAULT_PORTS = {
    netconf: "830",
    cli: "22",
  };

  const FAMILY_LABELS = {
    IHUB: "IHUB",
    NT: "NT",
    LT: "LT",
  };

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

  function clearDeployStatus() {
    deployStatusEl.textContent = "";
    deployStatusEl.className = "deploy-status hidden";
  }

  function showDeployStatus(message, isSuccess) {
    deployStatusEl.textContent = message;
    deployStatusEl.className = `deploy-status ${isSuccess ? "success" : "error"}`;
  }

  function getSelectedBoard() {
    return boardSelect.value.trim() || lastDetectedBoard || null;
  }

  function getOutputContentFormat() {
    return currentMode === "xml2cli" ? "cli" : "xml";
  }

  function getDeployTransport() {
    return currentMode === "xml2cli" ? "cli" : "netconf";
  }

  function updateDeployPortForMode() {
    devicePort.value = currentMode === "xml2cli" ? DEFAULT_PORTS.cli : DEFAULT_PORTS.netconf;
  }

  function setBoardInfo(board, yangTree) {
    lastDetectedBoard = board || null;
    if (!board) {
      boardInfoEl.textContent = "";
      boardInfoEl.classList.add("hidden");
      return;
    }
    const treeLabel = yangTree === "all" ? "（完整树）" : "";
    boardInfoEl.textContent = `板卡: ${board}${treeLabel}`;
    boardInfoEl.classList.remove("hidden");
  }

  function clearAllText() {
    inputText.value = "";
    outputText.value = "";
    if (fileInput) {
      fileInput.value = "";
    }
    clearError();
    clearDeployStatus();
    setBoardInfo(null);
    lastDetectedBoard = null;
    inputText.focus();
  }

  function populateBoardSelect(boards) {
    const grouped = {};
    for (const board of boards) {
      if (!grouped[board.family]) {
        grouped[board.family] = [];
      }
      grouped[board.family].push(board);
    }

    for (const family of ["IHUB", "NT", "LT"]) {
      const items = grouped[family];
      if (!items || items.length === 0) {
        continue;
      }
      const optgroup = document.createElement("optgroup");
      optgroup.label = FAMILY_LABELS[family] || family;
      for (const board of items) {
        const option = document.createElement("option");
        option.value = board.id;
        option.textContent = board.id;
        optgroup.appendChild(option);
      }
      boardSelect.appendChild(optgroup);
    }
  }

  async function loadBoards() {
    try {
      const response = await fetch("/api/boards");
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      populateBoardSelect(data.boards || []);
    } catch {
      // Board list is optional; auto-detect still works.
    }
  }

  function buildRequestBody(content) {
    const body = { content };
    const board = boardSelect.value.trim();
    if (board) {
      body.board = board;
    }
    if (yangTreeAll.checked) {
      body.yang_tree = "all";
    }
    return body;
  }

  const pasteTabBtn = document.querySelector('[data-tab="paste"]');
  const uploadTabBtn = document.querySelector('[data-tab="upload"]');

  function updateTabStyles(activeTab) {
    const isPaste = activeTab === "paste";

    pasteTabBtn.classList.toggle("active", isPaste);
    uploadTabBtn.classList.toggle("active", !isPaste);

    pasteTabBtn.classList.toggle("btn-primary", isPaste);
    pasteTabBtn.classList.toggle("btn-tab", !isPaste);

    uploadTabBtn.classList.remove("btn-primary");
    uploadTabBtn.classList.add("btn-tab");
  }

  function switchTab(tab) {
    updateTabStyles(tab);
    pastePanel.classList.toggle("hidden", tab !== "paste");
    uploadPanel.classList.toggle("hidden", tab !== "upload");
  }

  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
  });

  document.querySelectorAll('input[name="mode"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      currentMode = getMode();
      updateDeployPortForMode();
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
    clearDeployStatus();
    const content = inputText.value.trim();
    if (!content) {
      showError("请输入或上传内容");
      return;
    }

    const endpoint = currentMode === "xml2cli" ? "/api/xml2cli" : "/api/cli2xml";
    const yangTree = yangTreeAll.checked ? "all" : "standard";

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildRequestBody(content)),
      });

      const data = await response.json();
      if (!response.ok) {
        showError(data.detail || "转换失败");
        setBoardInfo(null);
        return;
      }

      if (data.errors && data.errors.length > 0) {
        const hasOutput =
          (currentMode === "xml2cli" && data.cli && data.cli.length > 0) ||
          (currentMode === "cli2xml" && data.xml);
        if (!hasOutput) {
          showError(data.errors.join("; "));
          outputText.value = "";
          setBoardInfo(null);
          return;
        }
      }

      outputText.value =
        currentMode === "xml2cli" ? (data.cli || []).join("\n") : data.xml || "";
      setBoardInfo(data.board, yangTree);
    } catch (error) {
      showError(`请求失败: ${error.message}`);
      setBoardInfo(null);
    }
  });

  clearBtn.addEventListener("click", (event) => {
    event.preventDefault();
    clearAllText();
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

  deployBtn.addEventListener("click", async () => {
    clearDeployStatus();
    const content = outputText.value.trim();
    if (!content) {
      showDeployStatus("请先生成或粘贴要下发的配置", false);
      return;
    }

    const host = deviceHost.value.trim();
    const username = deviceUser.value.trim();
    const port = Number.parseInt(devicePort.value, 10);
    if (!host) {
      showDeployStatus("请输入设备地址", false);
      return;
    }
    if (!username) {
      showDeployStatus("请输入用户名", false);
      return;
    }
    if (!Number.isFinite(port) || port < 1 || port > 65535) {
      showDeployStatus("端口号无效", false);
      return;
    }

    const board = getSelectedBoard();
    const transport = getDeployTransport();
    const contentFormat = getOutputContentFormat();

    const body = {
      content,
      content_format: contentFormat,
      host,
      port,
      username,
      password: devicePassword.value,
      transport,
    };
    if (board) {
      body.board = board;
    }
    if (yangTreeAll.checked) {
      body.yang_tree = "all";
    }

    deployBtn.disabled = true;
    deployBtn.textContent = "下发中...";

    try {
      const response = await fetch("/api/deploy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) {
        showDeployStatus(data.detail || "下发请求失败", false);
        return;
      }
      showDeployStatus(data.message, data.success);
    } catch (error) {
      showDeployStatus(`请求失败: ${error.message}`, false);
    } finally {
      deployBtn.disabled = false;
      deployBtn.textContent = "配置下发";
    }
  });

  loadBoards();
  updateDeployPortForMode();
});
