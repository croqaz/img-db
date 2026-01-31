document.addEventListener("DOMContentLoaded", function () {
  const modalWrap = document.getElementById("modal-wrap");
  const popupImage = document.getElementById("popup-image");
  const closePopup = document.getElementById("close-popup");
  const spinner = document.getElementById("spinner");
  let currentImageId = null;

  if (!modalWrap || !popupImage || !closePopup || !spinner) {
    return;
  }

  const openPopup = (el) => {
    currentImageId = el.id;
    const imgPath = el.getAttribute("data-pth");
    if (imgPath) {
      spinner.style.display = "block";
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
      container = direction === "next"
        ? currentContainer.nextElementSibling
        : currentContainer.previousElementSibling;
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
      }
    }
  });
});
