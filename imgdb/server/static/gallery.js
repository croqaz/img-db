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
  document.querySelectorAll(".gallery-image").forEach((img) => {
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
