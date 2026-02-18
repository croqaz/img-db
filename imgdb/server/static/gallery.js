// global sort by date
window.sortName = "date";

function sluggify(str) {
  if (str && typeof str === "string") {
    return str.replace(/[^a-zA-Z0-9 -]/gi, "-").replace(/ /g, "-").replace(/-+/g, "-").replace(/-+$/, "");
  }
}

function imgProp(img, prop) {
  return (img.getAttribute(`data-${prop}`) || "").toLowerCase();
}

function base32ToBigInt(str) {
  const digits = "0123456789abcdefghijklmnopqrstuv";
  let result = 0n;
  for (const char of str.toLowerCase()) {
    result = result * 32n + BigInt(digits.indexOf(char));
  }
  return result;
}

function imageSortKey(img) {
  // Returns the sort key for one image, based on the current sort name
  if (!sortName || sortName === "date") return img.getAttribute("data-date");
  if (sortName === "bytes") return parseInt(img.getAttribute("data-bytes"));
  if (sortName === "type-mode") {
    return img.getAttribute("data-format") + " " + img.getAttribute("data-mode") + ";" + img.getAttribute("data-date");
  }
  if (sortName === "camera-model") {
    return (img.getAttribute("data-maker-model") || "") + ";" + img.getAttribute("data-date");
  }
  if (sortName === "width-height" || sortName === "height-width") {
    const [w, h] = img.getAttribute("data-size").split(",");
    return {
      w: parseInt(w),
      h: parseInt(h),
      b: parseInt(img.getAttribute("data-bytes")),
    };
  } else if (sortName === "illumination" || sortName === "contrast" || sortName === "saturation") {
    return parseInt(img.getAttribute(`data-${sortName}`) || "0");
  } else if (sortName === "top-colors") {
    return (img.getAttribute(`data-${sortName}`) || "").split(",")[0] + ";" + img.getAttribute("data-date");
  } else if (sortName === "bhash") {
    return img.getAttribute(`data-${sortName}`) || "";
  } else if (sortName === "ahash" || sortName === "dhash" || sortName === "vhash" || sortName === "rchash") {
    return base32ToBigInt(img.getAttribute(`data-${sortName}`) || "");
  } else console.error(`Invalid sort function: ${sortName}`);
}

function imageSortTitle(img) {
  // Returns the sort title for one image, based on the current sort name
  // img.parentNode.style.backgroundColor = "";
  if (sortName === "bytes") {
    const bytes = parseInt(img.getAttribute("data-bytes"));
    return "Size: " + (bytes / 1024).toFixed(2) + " KB";
  } else if (sortName === "type-mode") {
    return `${img.getAttribute("data-format")} ${img.getAttribute("data-mode")}`;
  } else if (sortName === "camera-model") {
    return "Cam: " + (img.getAttribute("data-maker-model") || "unknown");
  } else if (sortName === "top-colors") {
    if (!img.getAttribute("data-top-colors")) return "Color: -";
    const color = img.getAttribute("data-top-colors").split(",")[0].split("=")[0];
    // img.parentNode.style.backgroundColor = color;
    return "Color: " + color;
  } else if (sortName === "illumination") {
    if (!img.getAttribute(`data-${sortName}`)) return "Light: -";
    const light = parseInt(img.getAttribute(`data-${sortName}`) || "0");
    // img.parentNode.style.backgroundColor = `hsl(0, 0%, ${light}%)`;
    return `Light: ${light || "-"}%`;
  } else if (sortName === "contrast") {
    const val = img.getAttribute("data-contrast");
    return val ? `Contrast: ${val}` : "Contrast: -";
  } else if (sortName === "saturation") {
    const val = img.getAttribute("data-saturation");
    return val ? `Saturation: ${val}%` : "Saturation: -";
  } else if (sortName === "bhash" || sortName === "rchash") {
    return `${sortName}: ${img.getAttribute(`data-${sortName}`)?.slice(0, 8) + "\u2026" || ""}`;
  } else if (sortName === "ahash" || sortName === "dhash" || sortName === "vhash") {
    return `${sortName}: ${img.getAttribute(`data-${sortName}`) || ""}`;
  }

  const [w, h] = img.getAttribute("data-size").split(",");
  if (sortName === "width-,height") {
    return `W\xD7H ${w}\xD7${h} px`;
  }
  if (sortName === "height-width") {
    return `H\xD7W ${h}\xD7${w} px`;
  }
  return `${img.getAttribute("data-format")} ${w}\xD7${h} px`;
}

function imageSortAB() {
  // Returns the comparison function for sorting DOM img elements
  if (sortName === "bytes" || sortName === "illumination" || sortName === "contrast" || sortName === "saturation") {
    return (a, b) => b[0] - a[0];
  }
  if (sortName === "ahash" || sortName === "dhash" || sortName === "vhash" || sortName === "rchash") {
    return (a, b) => Number(b[0] - a[0]);
  } else if (sortName === "width-height") {
    return (a, b) => b[0].w - a[0].w || b[0].b - a[0].b;
  } else if (sortName === "height-width") {
    return (a, b) => b[0].h - a[0].h || b[0].b - a[0].b;
  }
  return;
}

function setupSearch() {
  const filterBy = document.getElementById("filterBy");
  const clearFilter = document.getElementById("clearFilter");
  clearFilter.onclick = function () {
    filterBy.value = "";
    filterBy.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Enter" }),
    );
  };
  const visibleContainer = document.querySelector(".container .grid");
  const hiddenContainer = document.getElementById("hidden-images");
  filterBy.onkeydown = function (ev) {
    if (ev.key === "Enter") {
      ev.preventDefault();
      const query = filterBy.value.toLowerCase().trim();
      for (const img of Array.from(document.querySelectorAll(".gallery-image-container img.gallery-image"))) {
        const parent = img.parentElement.parentElement;
        const [w, h] = img.getAttribute("data-size").split(",");
        const llmText = imgProp(img, "obj-detect-llm");
        // imgProp(img, "pth").includes(query) ||
        if (
          query === "" ||
          imgProp(img, "date").startsWith(query) ||
          imgProp(img, "format") === query ||
          imgProp(img, "mode") === query ||
          imgProp(img, "maker-model").startsWith(query) ||
          img.getAttribute("bytes") === query ||
          w === query || h === query || img.id === query ||
          (query.startsWith("#") && imgProp(img, "top-colors").includes(query)) ||
          (llmText && llmText.toLowerCase().includes(query))
        ) {
          parent.style.display = "flex";
          visibleContainer.appendChild(parent);
        } else {
          parent.style.display = "none";
          hiddenContainer.appendChild(parent);
        }
      }
    }
  };
}

function setupSort() {
  const sortBy = document.getElementById("sortBy");
  const sortOrd = document.getElementById("sortOrder");
  const visibleContainer = document.querySelector(".container .grid");
  // the sorting arrow values
  const isArrowRev = () => sortOrd.innerText.trim() === "🠗";
  const isArrowNorm = () => sortOrd.innerText.trim() === "🠕";
  sortOrd.onclick = function (ev) {
    // 🠗 🠕
    if (isArrowNorm()) ev.target.innerText = "🠗";
    else ev.target.innerText = "🠕";
    sortBy.dispatchEvent(new Event("change"));
  };
  sortBy.onchange = function () {
    window.sortName = sluggify(sortBy.value);
    const sorted = [];
    for (const img of Array.from(document.querySelectorAll(".gallery-image-container img.gallery-image"))) {
      sorted.push([imageSortKey(img), img]);
      // img.parentElement.querySelector("small.sub").innerText = imageSortTitle(img);
    }
    sorted.sort(imageSortAB());
    if (isArrowRev()) sorted.reverse();
    for (let [_, img] of sorted) {
      visibleContainer.appendChild(img.parentElement.parentElement);
    }
  };
}

document.addEventListener("DOMContentLoaded", function () {
  const modalWrap = document.getElementById("modal-wrap");
  const modalClose = document.getElementById("modal-close");
  const modalInfo = document.getElementById("modal-info");
  const modalImage = document.getElementById("popup-image");
  const spinner = document.getElementById("spinner");
  const infoPanel = document.getElementById("info-panel");
  const infoContent = document.getElementById("info-content");

  if (!modalWrap || !modalClose || !modalInfo || !modalImage || !spinner || !infoPanel || !infoContent) {
    console.error("Essential gallery elements not found in the DOM!");
    return;
  }

  let currentImageId = null;
  let isInfoVisible = false;
  let isDragging = false;
  let zoomScale = 1;
  let panY = 0;
  let panX = 0;
  let dragStartY = 0;
  let dragStartX = 0;

  // Enable triggers
  setupSearch();
  setupSort();

  // Function to format and display image info
  const updateInfoPanel = () => {
    if (!currentImageId) return;
    const currentImg = document.getElementById(currentImageId);
    if (!currentImg) return;

    const info = [];

    // Always present fields
    const bytes = currentImg.getAttribute("data-bytes");
    const date = currentImg.getAttribute("data-date");
    const format = currentImg.getAttribute("data-format");
    const mode = currentImg.getAttribute("data-mode");
    const path = currentImg.getAttribute("data-pth");
    const size = currentImg.getAttribute("data-size");

    if (path) {
      const displayPath = path.length > 42 ? path.slice(0, 6) + "..." + path.slice(-36) : path;
      info.push(`<div><strong>Path:</strong><br><span class="text-xs">${displayPath}</span></div>`);
    }
    if (date) info.push(`<div><strong>Date:</strong> <span class="text-xs">${date}</span></div>`);
    if (format && mode) info.push(`<div><strong>Format:</strong> <span class="text-xs">${format} ${mode}</span></div>`);
    if (size) {
      const [width, height] = size.split(",");
      info.push(`<div><strong>Size:</strong> <span class="text-xs">${width} × ${height}</span></div>`);
    }
    if (bytes) {
      const kb = (parseInt(bytes) / 1024).toFixed(2);
      info.push(`<div><strong>File Size:</strong> <span class="text-xs">${kb} KB</span></div>`);
    }

    // Optional fields
    const makerModel = currentImg.getAttribute("data-maker-model");
    const lensInfo = currentImg.getAttribute("data-lens");
    const iso = currentImg.getAttribute("data-iso");
    const aperture = currentImg.getAttribute("data-aperture");
    const focalLength = currentImg.getAttribute("data-focal-length");
    const shutterSpeed = currentImg.getAttribute("data-shutter-speed");
    const llmText = currentImg.getAttribute("data-obj-detect-llm");

    if (makerModel) {
      info.push(`<div><strong>Camera:</strong> <span class="text-xs">${makerModel.replace(/-/g, " ")}</span></div>`);
    }
    if (lensInfo) {
      info.push(`<div><strong>Lens:</strong> <span class="text-xs">${lensInfo.replace(/-/g, " ")}</span></div>`);
    }
    if (iso && iso !== "0") info.push(`<div><strong>ISO:</strong> <span class="text-xs">${iso}</span></div>`);
    if (aperture) info.push(`<div><strong>Aperture:</strong> <span class="text-xs">${aperture}</span></div>`);
    if (focalLength) info.push(`<div><strong>Focal Length:</strong> <span class="text-xs">${focalLength}</span></div>`);
    if (shutterSpeed) {
      info.push(`<div><strong>Shutter Speed:</strong> <span class="text-xs">${shutterSpeed}</span></div>`);
    }
    if (llmText) {
      info.push(`<div><strong>LLM text:</strong><br><span class="text-xs">${llmText}</span></div>`);
    }

    // Image download buttons
    const downloadUrl = `/img?path=${encodeURIComponent(path)}`;
    const downloadButtons = `
      <div class="mt-4 flex space-x-2">
        <a href="${downloadUrl}" download="${currentImageId}"
          class="flex-1 text-center px-4 py-2 text-sm font-medium border border-transparent rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 border-stone-300 bg-stone-800 hover:bg-stone-600 text-stone-400 hover:text-stone-800"> ⬇️ orig
        </a>
        <a href="${downloadUrl}&sz=2560" download="${currentImageId}-2560px"
          class="flex-1 text-center px-4 py-2 text-sm font-medium border border-transparent rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 border-stone-300 bg-stone-800 hover:bg-stone-600 text-stone-400 hover:text-stone-800"> ⬇️ med
        </a>
        <a href="${downloadUrl}&sz=1280" download="${currentImageId}-1280px"
          class="flex-1 text-center px-4 py-2 text-sm font-medium border border-transparent rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 border-stone-300 bg-stone-800 hover:bg-stone-600 text-stone-400 hover:text-stone-800"> ⬇️ sm
        </a>
      </div>
    `;
    info.push(downloadButtons);

    // <div id="info-content" class="text-sm space-y-3 -mt-1"></div>
    infoContent.innerHTML = info.join('<div class="border-b border-gray-800 my-2"></div>');
  };

  // Toggle info panel visibility
  const toggleInfoPanel = () => {
    isInfoVisible = !isInfoVisible;
    if (isInfoVisible) {
      updateInfoPanel();
      infoPanel.classList.remove("translate-x-full");
      infoPanel.classList.add("translate-x-0");
    } else {
      infoPanel.classList.remove("translate-x-0");
      infoPanel.classList.add("translate-x-full");
    }
  };

  const updateTransform = () => {
    // Reset pan if checked back to 1x
    if (zoomScale <= 1.01) {
      zoomScale = 1;
      panX = 0;
      panY = 0;
    }
    modalImage.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomScale})`;
    // Update cursor
    if (zoomScale > 1) {
      modalImage.style.cursor = isDragging ? "grabbing" : "grab";
    } else {
      modalImage.style.cursor = "default";
    }
  };

  const updateZoom = (direction) => {
    const baseWidth = modalImage.offsetWidth;
    const naturalWidth = modalImage.naturalWidth;
    if (!baseWidth || !naturalWidth) return;

    // Zoom up to 2x actual image width
    // Calculate scale required to reach 2x actual width
    const maxScale = Math.max(1, (naturalWidth * 2) / baseWidth);

    let newScale = zoomScale + direction;

    // Clamp
    if (newScale < 1) newScale = 1;
    if (newScale > maxScale) newScale = maxScale;

    zoomScale = newScale;
    updateTransform();
  };

  const resetZoom = () => {
    isDragging = false;
    zoomScale = 1;
    panX = 0;
    panY = 0;
    updateTransform();
  };

  const openPopup = (el) => {
    resetZoom();
    currentImageId = el.id;
    const imgPath = el.getAttribute("data-pth");
    if (imgPath) {
      spinner.style.display = "block";
      modalWrap.classList.remove("hidden");
      modalWrap.classList.add("flex");
      document.body.style.overflow = "hidden";
      // Update info panel if it's visible
      if (isInfoVisible) {
        updateInfoPanel();
      }
      // Check server health before fetching the image
      fetch("/api/health")
        .then((response) => {
          if (!response.ok) {
            throw new Error("Server health check failed!");
          }
          modalImage.src = `/img?path=${encodeURIComponent(imgPath)}`;
        })
        .catch((error) => {
          console.warn("Server not available, trying to load image directly", error);
          modalImage.src = `file://${imgPath}`; // Fallback to direct path
        });
    }
  };

  const closePopup = () => {
    modalImage.src = "";
    modalWrap.classList.add("hidden");
    modalWrap.classList.remove("flex");
    document.body.style.overflow = "auto";
    if (isInfoVisible) {
      toggleInfoPanel();
    }
  };

  // Hook up all gallery images
  document.querySelectorAll("img.gallery-image").forEach((img) => {
    img.addEventListener("click", (e) => {
      openPopup(e.currentTarget);
    });
  });

  modalImage.onload = () => {
    spinner.style.display = "none";
  };

  // Not used for now, could be helpful later
  // modalImage.onerror = (err) => {
  //   spinner.style.display = "none";
  //   closePopup(); ??
  // };

  modalImage.onmousedown = (e) => {
    if (zoomScale > 1) {
      e.preventDefault();
      isDragging = true;
      dragStartX = e.clientX - panX;
      dragStartY = e.clientY - panY;
      modalImage.style.transition = "none"; // Disable transition for direct manipulation
      updateTransform();
    }
  };
  modalImage.onmousemove = (e) => {
    if (isDragging) {
      e.preventDefault();
      panX = e.clientX - dragStartX;
      panY = e.clientY - dragStartY;
      updateTransform();
    }
  };

  const endDrag = () => {
    if (isDragging) {
      isDragging = false;
      modalImage.style.transition = ""; // Restore transition
      updateTransform();
    }
  };
  modalImage.onmouseup = endDrag;
  modalImage.onmouseleave = endDrag;

  modalInfo.onclick = toggleInfoPanel;
  modalClose.onclick = closePopup;
  modalWrap.onclick = (ev) => {
    if (ev.target.id === "modal-close" || (zoomScale <= 1 && ev.target.id == "image-container")) {
      closePopup();
    }
  };

  const navigateImages = (direction) => {
    if (!currentImageId) {
      return;
    }
    const currentImg = document.getElementById(currentImageId);
    if (!currentImg) {
      console.error(`Internal error: current img ID ${currentImageId} not found!`);
      return;
    }
    const currentContainer = currentImg.closest(".gallery-image-container");
    if (!currentContainer) {
      return;
    }

    let container;
    if (direction === "first") {
      container = document.querySelector(".gallery-image-container");
    } else if (direction === "last") {
      container = document.querySelector(".gallery-image-container:last-child");
    } else {
      container = direction === "next" ? currentContainer.nextElementSibling : currentContainer.previousElementSibling;
    }

    if (container) {
      const nextImg = container.querySelector(".gallery-image");
      if (nextImg) {
        openPopup(nextImg);
      }
    }
  };

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") {
      closePopup();
      return;
    }
    if (!modalWrap.classList.contains("hidden")) {
      if (ev.key === "ArrowRight" || ev.key === "ArrowDown") {
        navigateImages("next");
      } else if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") {
        navigateImages("previous");
      } else if (ev.key === "Home") {
        navigateImages("first");
      } else if (ev.key === "End") {
        navigateImages("last");
      } else if (ev.key === "i" || ev.key === "I") {
        toggleInfoPanel();
      } else if (ev.key === "+" || ev.key === "=") {
        updateZoom(1);
      } else if (ev.key === "-" || ev.key === "_") {
        updateZoom(-1);
      } else if (ev.key === "0") {
        resetZoom();
      }
    }
  });
});

document.addEventListener("DOMContentLoaded", function () {
  //
  // Import modal functionality
  //
  const importModal = document.getElementById("import-modal");
  const openImportBtn = document.getElementById("openImport");
  const closeImportBtn = document.getElementById("closeImport");
  const cancelImportBtn = document.getElementById("cancelImport");
  const startImportBtn = document.getElementById("startImport");
  const importForm = document.getElementById("importForm");
  const importStatus = document.getElementById("import-status");
  const importBrowseBtn = document.getElementById("importBrowse");
  const importBrowseFolderBtn = document.getElementById("importBrowseFolder");
  const importDropZone = document.getElementById("import-drop-zone");
  const importFileList = document.getElementById("import-file-list");
  const importFilesInput = document.getElementById("importFiles");
  const importFolderInput = document.getElementById("importFolder");
  const importProgressBar = document.getElementById("import-progress-bar");
  const importProgressCount = document.getElementById("import-progress-count");
  const importProgressFile = document.getElementById("import-progress-file");
  const importProgressWrap = document.getElementById("import-progress-wrap");
  let importAbortController = null;
  let isImportBusy = false;
  let droppedFiles = [];

  if (
    !importModal || !openImportBtn || !importForm || !importStatus || !startImportBtn || !cancelImportBtn ||
    !closeImportBtn || !importDropZone || !importFilesInput || !importFileList || !importBrowseBtn ||
    !importBrowseFolderBtn || !importFolderInput || !importProgressWrap || !importProgressBar || !importProgressCount ||
    !importProgressFile
  ) {
    console.error("Import modal elements not found in the DOM!");
    return;
  }

  const setDroppedFiles = (fileList) => {
    droppedFiles = Array.from(fileList || []).filter((file) => file instanceof File);
    if (droppedFiles.length === 0) {
      importFileList.textContent = "No files selected.";
      return;
    }
    const names = droppedFiles.slice(0, 3).map((file) => file.name).join(", ");
    const more = droppedFiles.length > 3 ? ` +${droppedFiles.length - 3} more` : "";
    const types = [...new Set(droppedFiles.map((file) => file.type ? "file" : "folder"))].join(" and ");
    importFileList.textContent = `Selected ${droppedFiles.length} ${types}(s): ${names}${more}`;
  };

  const resetImportProgress = () => {
    importProgressBar.style.width = "0%";
    importProgressCount.textContent = "Starting...";
    importProgressFile.textContent = "";
    importProgressWrap.classList.add("hidden");
  };

  const toggleImportModal = (show) => {
    if (!show && isImportBusy) {
      return;
    }
    if (show) {
      importModal.classList.remove("hidden");
      importModal.classList.add("flex");
    } else {
      importModal.classList.add("hidden");
      importModal.classList.remove("flex");
    }
  };

  const setImportBusy = (isBusy) => {
    isImportBusy = isBusy;
    Array.from(importForm.elements).forEach((el) => {
      if (el instanceof HTMLInputElement) {
        el.disabled = isBusy;
      }
    });
    startImportBtn.disabled = isBusy;
    startImportBtn.classList.toggle("opacity-60", isBusy);
  };

  const setImportStatus = (message, isError = false) => {
    console.log("Import status:", message);
    importStatus.textContent = message;
    importStatus.classList.remove("hidden");
    if (isError) {
      importStatus.classList.add("text-red-600");
      importStatus.classList.remove("text-stone-600");
    } else {
      importStatus.classList.remove("text-red-600");
      importStatus.classList.add("text-stone-600");
    }
  };

  // Helper to recursively get files from an entry
  async function getFilesFromEntry(entry) {
    if (entry.isFile) {
      return new Promise((resolve, reject) => {
        entry.file(resolve, reject);
      });
    } else if (entry.isDirectory) {
      const dirReader = entry.createReader();
      const entries = await new Promise((resolve, reject) => {
        const result = [];
        function read() {
          dirReader.readEntries((batch) => {
            if (batch.length === 0) resolve(result);
            else {
              result.push(...batch);
              read();
            }
          }, reject);
        }
        read();
      });
      const files = await Promise.all(entries.map((entry) => getFilesFromEntry(entry)));
      return files.flat();
    }
    return [];
  }

  // Handle dropped items
  async function handleDroppedItems(items) {
    const filePromises = [];
    for (const item of items) {
      if (item.kind !== "file") continue;
      const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : (item.getAsEntry ? item.getAsEntry() : null);
      if (entry) {
        filePromises.push(getFilesFromEntry(entry));
      } else {
        const file = item.getAsFile();
        if (file) filePromises.push(Promise.resolve([file]));
      }
    }
    try {
      const filesArrays = await Promise.all(filePromises);
      const files = filesArrays.flat();
      setDroppedFiles(files);
    } catch (err) {
      console.error("Error processing dropped files:", err);
      setImportStatus("Error processing dropped files.", true);
    }
  }

  const updateImportProgress = (availableCount, importedCount, filename) => {
    console.debug(`Updating import progress: ${importedCount}/${availableCount}, file: ${filename}`);
    if (availableCount >= 1) {
      importProgressWrap.classList.remove("hidden");
      const percent = Math.min(
        100,
        parseFloat(Math.round(importedCount / availableCount * 100).toFixed(1)),
      );
      importProgressBar.style.width = `${percent}%`;
      importProgressCount.textContent = `Importing ${importedCount}/${availableCount}`;
      if (filename) {
        importProgressFile.textContent = filename;
      }
    } else {
      importProgressWrap.classList.add("hidden");
    }
  };

  async function handleImportStream(response) {
    if (!response.body) {
      throw new Error("Import stream unavailable!");
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let availableCount = 0;
    let importedCount = 0;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";
      for (const part of parts) {
        const dataLine = part.split("\n").find((line) => line.startsWith("data:"));
        if (!dataLine) continue;
        const payload = dataLine.replace(/^data:\s*/, "");
        if (!payload) continue;
        let data;
        try {
          data = JSON.parse(payload);
        } catch (err) {
          console.warn("Failed to parse import payload", err, payload);
          continue;
        }

        if (typeof data.available === "number") {
          availableCount = data.available;
          if (typeof data.imported === "number") {
            importedCount = data.imported;
          }
          if (data.filename === "start") {
            // Make sure availableCount is set before showing progress
            if (availableCount > 0) {
              setImportStatus(`Importing ${availableCount} files...`);
              updateImportProgress(availableCount, importedCount, "");
            }
          }
          if (data.filename === "done") {
            setImportStatus(`Imported ${data.imported} of ${availableCount} files.`);
            importedCount = data.imported;
            updateImportProgress(availableCount, importedCount, "");
          }
        } else if (typeof data.imported_count === "number") {
          importedCount = data.imported_count;
          updateImportProgress(availableCount, importedCount, data.filename);
          // Force UI update to show progress bar movement
          await new Promise((resolve) => requestAnimationFrame(resolve));
        } else if (data.message) {
          setImportStatus(data.message);
        }
      }
    }
    return { availableCount, importedCount };
  }

  const startImport = async () => {
    const inputs = {
      filterInput: document.getElementById("importFilter"),
      extsInput: document.getElementById("importExts"),
      limitInput: document.getElementById("importLimit"),
      skipInput: document.getElementById("importSkip"),
      deepInput: document.getElementById("importDeep"),
    };
    const dbPath = document.getElementById("db")?.value || "";
    if (!dbPath) {
      setImportStatus("Please load a gallery database first.", true);
      return;
    }
    if (droppedFiles.length === 0) {
      setImportStatus("Please browse or drop image files.", true);
      return;
    }

    const url = new URL(window.location.origin + `/import?db=${encodeURIComponent(dbPath)}`);
    const body = new FormData();
    // TODO :: restore support for input path !!
    // body.set("input", inputPath);
    if (droppedFiles.length > 0) {
      for (const file of droppedFiles) {
        body.append("files", file);
      }
    }

    const filterValue = inputs.filterInput?.value.trim();
    const extsValue = inputs.extsInput?.value.trim();
    const limitValue = inputs.limitInput?.value.trim();
    if (filterValue) url.searchParams.set("filter", filterValue);
    if (extsValue) url.searchParams.set("exts", extsValue);
    if (limitValue) url.searchParams.set("limit", limitValue);
    if (inputs.skipInput?.checked) url.searchParams.set("skip_imported", "true");
    if (inputs.deepInput?.checked) url.searchParams.set("deep", "true");

    setImportBusy(true);
    resetImportProgress();
    setImportStatus("Starting import...");

    importAbortController = new AbortController();
    try {
      const response = await fetch(url, { method: "POST", body: body, signal: importAbortController.signal });
      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || "Import failed");
      }
      await handleImportStream(response);
      setImportStatus("Reloading gallery...");
      setTimeout(() => {
        // Reload the whole page to show new images
        // could be optimized later to just append new images without reload
        window.location.reload();
      }, 1000);
    } catch (error) {
      if (error.name === "AbortError") {
        console.warn("Import aborted by user");
        setImportStatus("Import cancelled.");
      } else {
        console.error("Import failed with error:", error);
        setImportStatus(`Import failed: ${error.message}. Check console for details.`, true);
      }
    } finally {
      importAbortController = null;
      setImportBusy(false);
    }
  };

  openImportBtn.addEventListener("click", () => {
    resetImportProgress();
    importStatus.classList.add("hidden");
    setDroppedFiles([]);
    importFilesInput.value = "";
    toggleImportModal(true);
  });

  let importMessage = "";
  closeImportBtn.onclick = () => {
    if (!isImportBusy) {
      toggleImportModal(false);
    } else {
      if (!importStatus.textContent.includes("Use Cancel")) {
        importMessage = importStatus.textContent;
      }
      setImportStatus("Import in progress. Use Cancel to stop the import first.");
      setTimeout(() => {
        if (importMessage) {
          setImportStatus(importMessage);
        }
      }, 1000);
    }
  };
  cancelImportBtn.onclick = () => {
    if (importAbortController) importAbortController.abort();
    else toggleImportModal(false);
  };
  importBrowseBtn.addEventListener("click", () => {
    if (isImportBusy) return;
    importFilesInput.click();
  });
  importFilesInput.addEventListener("change", (ev) => {
    if (isImportBusy) return;
    setDroppedFiles(ev.target.files || []);
  });
  importBrowseFolderBtn.addEventListener("click", () => {
    if (isImportBusy) return;
    importFolderInput.click();
  });
  importFolderInput.addEventListener("change", (ev) => {
    if (isImportBusy) return;
    setDroppedFiles(ev.target.files || []);
  });
  importDropZone.addEventListener("dragenter", (ev) => {
    if (isImportBusy) return;
    ev.preventDefault();
    importDropZone.classList.add("border-indigo-500", "bg-indigo-50/60");
  });
  importDropZone.addEventListener("dragover", (ev) => {
    if (isImportBusy) return;
    ev.preventDefault();
  });
  importDropZone.addEventListener("dragleave", () => {
    importDropZone.classList.remove("border-indigo-500", "bg-indigo-50/60");
  });
  importDropZone.addEventListener("drop", (ev) => {
    if (isImportBusy) return;
    ev.preventDefault();
    ev.stopPropagation();
    importDropZone.classList.remove("border-indigo-500", "bg-indigo-50/60");
    if (ev.dataTransfer?.items) {
      handleDroppedItems(Array.from(ev.dataTransfer.items));
    } else if (ev.dataTransfer?.files?.length) {
      setDroppedFiles(ev.dataTransfer.files);
    }
  });
  document.addEventListener("dragover", (ev) => {
    if (isImportBusy) return;
    if (ev.dataTransfer && Array.from(ev.dataTransfer.types || []).includes("Files")) {
      ev.preventDefault();
    }
  });
  document.addEventListener("drop", (ev) => {
    if (isImportBusy) return;
    if (!(ev.dataTransfer && Array.from(ev.dataTransfer.types || []).includes("Files"))) return;
    ev.preventDefault();
    resetImportProgress();
    importStatus.classList.add("hidden");
    toggleImportModal(true);
    if (ev.dataTransfer?.items) {
      handleDroppedItems(Array.from(ev.dataTransfer.items));
    } else if (ev.dataTransfer?.files?.length) {
      setDroppedFiles(ev.dataTransfer.files);
    }
  });
  importModal.onclick = (ev) => {
    if (ev.target === importModal) {
      if (isImportBusy) return;
      else toggleImportModal(false);
    }
  };
  startImportBtn.onclick = startImport;

  //
  // Settings modal functionality
  //
  const settingsModal = document.getElementById("settings-modal");
  const openSettingsBtn = document.getElementById("openSettings");
  const closeSettingsBtn = document.getElementById("closeSettings");
  const cancelSettingsBtn = document.getElementById("cancelSettings");
  const saveSettingsBtn = document.getElementById("saveSettings");
  const settingsForm = document.getElementById("settingsForm");

  if (
    !settingsModal || !openSettingsBtn || !closeSettingsBtn || !cancelSettingsBtn || !saveSettingsBtn || !settingsForm
  ) {
    console.error("Settings modal elements not found in the DOM!");
    return;
  }

  function toggleSettings(show) {
    if (show) {
      settingsModal.classList.remove("hidden");
      settingsModal.classList.add("flex");
    } else {
      settingsModal.classList.add("hidden");
      settingsModal.classList.remove("flex");
    }
  }

  if (openSettingsBtn) {
    openSettingsBtn.addEventListener("click", () => toggleSettings(true));
  }
  [closeSettingsBtn, cancelSettingsBtn].forEach((btn) => {
    if (btn) btn.addEventListener("click", () => toggleSettings(false));
  });
  settingsModal.addEventListener("click", (e) => {
    // Close modal if clicking outside the content area
    if (e.target === settingsModal) toggleSettings(false);
  });

  saveSettingsBtn.addEventListener("click", async () => {
    const formData = new FormData(settingsForm);
    const dbPath = document.getElementById("db").value;

    // Combine checkboxes
    const checkboxGroups = ["metadata", "algorithms", "v_hashes"];
    checkboxGroups.forEach((group) => {
      const checked = Array.from(settingsForm.querySelectorAll(`input[name="${group}_cb"]:checked`)).map((cb) =>
        cb.value
      );
      if (checked.length > 0) {
        formData.set(group, checked.join(","));
      } else {
        formData.set(group, "");
      }
      formData.delete(`${group}_cb`);
    });

    try {
      const url = `/gallery_settings?db=${encodeURIComponent(dbPath)}`;
      const response = await fetch(url, {
        method: "POST",
        body: formData,
      });

      const result = await response.json();
      if (result.status === "ok" || result.status === "no changes") {
        // Reload to show changes (though most are config matching)
        window.location.reload();
      } else {
        alert("Settings update status: " + result.status);
        if (result.status === "ok" || result.status === "no changes") window.location.reload();
      }
    } catch (error) {
      console.error("Error saving settings:", error);
      alert("Failed to save settings.");
    }
  });

  //
  // Download current gallery as static HTML
  //
  const downloadGalleryBtn = document.getElementById("downloadGallery");
  if (downloadGalleryBtn) {
    downloadGalleryBtn.addEventListener("click", async () => {
      try {
        const clone = document.documentElement.cloneNode(true);

        // Remove the "Load Gallery" form (not useful in a static page)
        const loadForm = clone.querySelector('form[action="/gallery"]');
        if (loadForm) loadForm.remove();

        // Remove server-only buttons (Import, Config, Download)
        for (const id of ["openImport", "openSettings", "downloadGallery"]) {
          const btn = clone.querySelector(`#${id}`);
          if (btn) btn.remove();
        }

        // Remove server-only modals (import & settings)
        for (const id of ["import-modal", "settings-modal"]) {
          const modal = clone.querySelector(`#${id}`);
          if (modal) modal.remove();
        }

        // Move hidden (filtered-out) images back into the visible grid
        const hiddenContainer = clone.querySelector("#hidden-images");
        const visibleGrid = clone.querySelector(".container .grid");
        if (hiddenContainer && visibleGrid) {
          while (hiddenContainer.firstChild) {
            const child = hiddenContainer.firstChild;
            // Make sure the item is visible again
            if (child.style) child.style.display = "";
            visibleGrid.appendChild(child);
          }
        }

        // Inline the gallery.js script, stripping server-only code
        const scriptTag = clone.querySelector('script[src="/static/gallery.js"]');
        if (scriptTag) {
          const resp = await fetch("/static/gallery.js");
          if (resp.ok) {
            let jsText = await resp.text();
            // Remove everything from the second DOMContentLoaded block onwards
            // (import modal, settings modal, download gallery)
            const marker = 'addEventListener("DOMContentLoaded", function () {\n  //\n  // Import modal functionality';
            const cutIdx = jsText.indexOf(marker);
            if (cutIdx !== -1) {
              jsText = jsText.substring(0, cutIdx).trimEnd() + "\n";
            }
            const inlineScript = document.createElement("script");
            inlineScript.textContent = jsText;
            scriptTag.parentNode.replaceChild(inlineScript, scriptTag);
          }
        }

        // Build filename from gallery path
        const dbPath = document.getElementById("currentDB")?.textContent || "";
        let filename = "gallery.html";
        if (dbPath) {
          const base = dbPath.split("/").pop().replace(/\.[^.]+$/, "");
          if (base) filename = sluggify(base) + ".html";
        }

        // Trigger download
        const html = "<!DOCTYPE html>\n" + clone.outerHTML;
        const blob = new Blob([html], { type: "text/html;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } catch (err) {
        console.error("Failed to download gallery:", err);
        alert("Download failed. Check console for details.");
      }
    });
  }
});
