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
        const llmText = img.getAttribute("data-obj-detect-llm");
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
  const modalImage = document.getElementById("popup-image");
  const spinner = document.getElementById("spinner");
  const infoPanel = document.getElementById("info-panel");
  const infoContent = document.getElementById("info-content");

  let currentImageId = null;
  let isInfoVisible = false;
  let isDragging = false;
  let zoomScale = 1;
  let panY = 0;
  let panX = 0;
  let dragStartY = 0;
  let dragStartX = 0;

  if (!modalWrap || !modalClose || !modalImage || !spinner || !infoPanel || !infoContent) {
    console.error("Essential gallery elements not found in the DOM!");
    return;
  }

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
    const lensInfo = currentImg.getAttribute("data-lens-maker-model");
    const iso = currentImg.getAttribute("data-iso");
    const aperture = currentImg.getAttribute("data-aperture");
    const focalLength = currentImg.getAttribute("data-focal-length");
    const shutterSpeed = currentImg.getAttribute("data-shutter-speed");

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
      console.log(`Internal error: current img ID ${currentImageId} not found!`);
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
