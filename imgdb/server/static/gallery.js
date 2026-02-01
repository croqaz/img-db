document.addEventListener("DOMContentLoaded", function () {
  const modalWrap = document.getElementById("modal-wrap");
  const popupImage = document.getElementById("popup-image");
  const closePopup = document.getElementById("close-popup");
  const spinner = document.getElementById("spinner");
  const infoPanel = document.getElementById("info-panel");
  const infoContent = document.getElementById("info-content");
  let currentImageId = null;
  let isInfoVisible = false;

  if (!modalWrap || !popupImage || !closePopup || !spinner || !infoPanel || !infoContent) {
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

  const openPopup = (el) => {
    currentImageId = el.id;
    const imgPath = el.getAttribute("data-pth");
    if (imgPath) {
      spinner.style.display = "block";
      // Update info panel if it's visible
      if (isInfoVisible) {
        updateInfoPanel();
      }
      // Check server health before fetching the image
      fetch("/api/health")
        .then((response) => {
          if (!response.ok) {
            throw new Error("Server health check failed");
          }
          popupImage.src = `/img?path=${encodeURIComponent(imgPath)}`;
          modalWrap.classList.remove("hidden");
          modalWrap.classList.add("flex");
          document.body.style.overflow = "hidden";
        })
        .catch((error) => {
          console.warn("Server not available, trying to load image directly", error);
          popupImage.src = `file://${imgPath}`; // Fallback to direct path
          modalWrap.classList.remove("hidden");
          modalWrap.classList.add("flex");
          document.body.style.overflow = "hidden";
        });
    }
  };

  const closePopupFunction = () => {
    popupImage.src = "";
    modalWrap.classList.add("hidden");
    modalWrap.classList.remove("flex");
    document.body.style.overflow = "auto";
    if (isInfoVisible) {
      toggleInfoPanel();
    }
  };

  popupImage.onload = () => {
    spinner.style.display = "none";
  };

  // popupImage.onerror = (err) => {
  //   spinner.style.display = "none";
  //   closePopupFunction();
  // };

  // Hook up all gallery images
  document.querySelectorAll(".gallery-image").forEach((img) => {
    img.addEventListener("click", (e) => {
      openPopup(e.currentTarget);
    });
  });

  closePopup.addEventListener("click", closePopupFunction);

  modalWrap.addEventListener("click", (e) => {
    if (e.target === modalWrap) {
      closePopupFunction();
    }
  });

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
    if (ev.key === "Escape" && !modalWrap.classList.contains("hidden")) {
      closePopupFunction();
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
      }
    }
  });
});
