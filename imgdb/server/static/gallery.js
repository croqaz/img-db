document.addEventListener("DOMContentLoaded", function () {
  const modalWrap = document.getElementById("modal-wrap");
  const popupImage = document.getElementById("popup-image");
  const closePopup = document.getElementById("close-popup");
  const spinner = document.getElementById("spinner");

  if (!modalWrap || !popupImage || !closePopup || !spinner) {
    return;
  }

  const openPopup = (el) => {
    const imagePath = el.getAttribute("data-pth");
    if (imagePath) {
      spinner.style.display = "block";
      // Check server health before fetching the image
      fetch("/api/health")
        .then((response) => {
          if (!response.ok) {
            throw new Error("Server health check failed");
          }
          popupImage.src = `/img?path=${encodeURIComponent(imagePath)}`;
          modalWrap.classList.remove("hidden");
          modalWrap.classList.add("flex");
          document.body.style.overflow = "hidden";
        })
        .catch((error) => {
          console.warn("Server not available, trying to load image directly", error);
          popupImage.src = `file://${imagePath}`; // Fallback to direct path
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

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modalWrap.classList.contains("hidden")) {
      closePopupFunction();
    }
  });
});
