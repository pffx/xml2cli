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
  const deployBoardSelect = document.getElementById("deploy-board-select");
  const deviceUser = document.getElementById("device-user");
  const devicePassword = document.getElementById("device-password");
  const devicePasswordToggle = document.getElementById("device-password-toggle");
  const clearDeviceBtn = document.getElementById("clear-device-btn");
  const deployBtn = document.getElementById("deploy-btn");
  const deployStatusEl = document.getElementById("deploy-status");
  const pastePanel = document.getElementById("paste-panel");
  const uploadPanel = document.getElementById("upload-panel");
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");

  let currentMode = "xml2cli";
  let lastDetectedBoard = null;
  const boardMeta = {};

  const CLI_SSH_PORT = 22;
  const NETCONF_PORT_IHUB = 831;
  const NETCONF_PORT_NT = 832;
  const NETCONF_PORT_LT_BASE = 833;

  const LT_SLOT_BOARD_IDS = {
    1: "LWLT-C",
    2: "LLLT-A",
    3: "LGLT-D",
  };

  const DEPLOY_SLOTS = [
    { id: "ihub", label: "IHUB", port: NETCONF_PORT_IHUB, boardId: "IHUB-LMNT-A" },
    { id: "nt", label: "NT", port: NETCONF_PORT_NT, boardId: "NT-LMNT-A" },
  ];

  for (let slot = 1; slot <= 16; slot += 1) {
    DEPLOY_SLOTS.push({
      id: `lt-${slot}`,
      label: `LT${slot}`,
      port: NETCONF_PORT_LT_BASE + slot - 1,
      boardId: LT_SLOT_BOARD_IDS[slot] || "LWLT-C",
    });
  }

  const deploySlotById = Object.fromEntries(DEPLOY_SLOTS.map((slot) => [slot.id, slot]));

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

  function getSelectedConversionBoard() {
    return boardSelect.value.trim() || lastDetectedBoard || null;
  }

  function getDeploySlot() {
    const slotId = deployBoardSelect.value;
    return deploySlotById[slotId] || deploySlotById.ihub;
  }

  function getDeployPort() {
    if (currentMode === "xml2cli") {
      return CLI_SSH_PORT;
    }
    return getDeploySlot().port;
  }

  function getDeployBoardId() {
    const conversionBoard = getSelectedConversionBoard();
    if (conversionBoard) {
      return conversionBoard;
    }
    return getDeploySlot().boardId;
  }

  function populateDeployBoardSelect() {
    const ihubGroup = document.createElement("optgroup");
    ihubGroup.label = "IHUB";
    const ntGroup = document.createElement("optgroup");
    ntGroup.label = "NT";
    const ltGroup = document.createElement("optgroup");
    ltGroup.label = "LT";

    deployBoardSelect.replaceChildren();

    for (const slot of DEPLOY_SLOTS) {
      const option = document.createElement("option");
      option.value = slot.id;
      option.textContent = `${slot.label} (${slot.port})`;
      if (slot.id === "ihub") {
        ihubGroup.appendChild(option);
      } else if (slot.id === "nt") {
        ntGroup.appendChild(option);
      } else {
        ltGroup.appendChild(option);
      }
    }

    deployBoardSelect.append(ihubGroup, ntGroup, ltGroup);
    deployBoardSelect.value = "ihub";
  }

  function boardIdToDeploySlot(boardId) {
    const meta = boardMeta[boardId];
    if (!meta) {
      return "ihub";
    }
    if (meta.family === "IHUB") {
      return "ihub";
    }
    if (meta.family === "NT") {
      return "nt";
    }
    if (meta.lt_slot) {
      return `lt-${meta.lt_slot}`;
    }
    return "lt-1";
  }

  function syncDeployBoardFromConversionBoard(boardId) {
    if (!boardId || currentMode !== "cli2xml") {
      return;
    }
    const slotId = boardIdToDeploySlot(boardId);
    if (deploySlotById[slotId]) {
      deployBoardSelect.value = slotId;
    }
  }

  function updateDeployBoardForMode() {
    const isNetconf = currentMode === "cli2xml";
    deployBoardSelect.disabled = !isNetconf;
    if (isNetconf && lastDetectedBoard) {
      syncDeployBoardFromConversionBoard(lastDetectedBoard);
    }
  }

  function getOutputContentFormat() {
    return currentMode === "xml2cli" ? "cli" : "xml";
  }

  function getDeployTransport() {
    return currentMode === "xml2cli" ? "cli" : "netconf";
  }

  function setBoardInfo(board, yangTree) {
    lastDetectedBoard = board || null;
    if (!board) {
      boardInfoEl.textContent = "";
      boardInfoEl.classList.add("hidden");
      return;
    }
    const treeLabel = yangTree === "all" ? "（完整树）" : "";
    const slot = getDeploySlot();
    const portHint =
      currentMode === "cli2xml" ? ` · NETCONF ${slot.port}` : " · SSH 22";
    boardInfoEl.textContent = `板卡: ${board}${treeLabel}${portHint}`;
    boardInfoEl.classList.remove("hidden");
    syncDeployBoardFromConversionBoard(board);
  }

  function clearDeviceFields() {
    deviceHost.value = "";
    deviceUser.value = "";
    devicePassword.value = "";
    if (devicePassword.type === "text") {
      devicePassword.type = "password";
      devicePasswordToggle.setAttribute("aria-label", "显示密码");
      devicePasswordToggle.setAttribute("title", "显示密码");
      devicePasswordToggle.querySelector(".icon-eye-open").classList.remove("hidden");
      devicePasswordToggle.querySelector(".icon-eye-closed").classList.add("hidden");
    }
    deployBoardSelect.value = "ihub";
    updateDeployBoardForMode();
    clearDeployStatus();
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
        boardMeta[board.id] = {
          family: board.family,
          lt_slot: board.lt_slot ?? null,
          netconf_port: board.netconf_port ?? null,
        };
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
      updateDeployBoardForMode();
      inputText.placeholder =
        currentMode === "xml2cli"
          ? "粘贴 NETCONF XML..."
          : "粘贴 CLI 命令（每行一条）...";
    });
  });

  deployBoardSelect.addEventListener("change", () => {
    clearDeployStatus();
    if (lastDetectedBoard) {
      const treeLabel = yangTreeAll.checked ? "（完整树）" : "";
      const slot = getDeploySlot();
      boardInfoEl.textContent = `板卡: ${lastDetectedBoard}${treeLabel} · NETCONF ${slot.port}`;
    }
  });

  devicePasswordToggle.addEventListener("click", () => {
    const show = devicePassword.type === "password";
    devicePassword.type = show ? "text" : "password";
    devicePasswordToggle.setAttribute("aria-label", show ? "隐藏密码" : "显示密码");
    devicePasswordToggle.setAttribute("title", show ? "隐藏密码" : "显示密码");
    devicePasswordToggle.querySelector(".icon-eye-open").classList.toggle("hidden", show);
    devicePasswordToggle.querySelector(".icon-eye-closed").classList.toggle("hidden", !show);
  });

  clearDeviceBtn.addEventListener("click", () => {
    clearDeviceFields();
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
    const port = getDeployPort();
    if (!host) {
      showDeployStatus("请输入设备地址", false);
      return;
    }
    if (!username) {
      showDeployStatus("请输入用户名", false);
      return;
    }

    const board = getDeployBoardId();
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

  populateDeployBoardSelect();
  loadBoards();
  updateDeployBoardForMode();
});
