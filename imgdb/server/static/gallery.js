document.addEventListener("DOMContentLoaded", function () {
  const modalWrap = document.getElementById("modal-wrap");
  const popupImage = document.getElementById("popup-image");
  const closePopup = document.getElementById("close-popup");
  const spinner = document.getElementById("spinner");

  if (!modalWrap || !popupImage || !spinner || !closePopup) {
    return;
  }

  const openPopup = (el) => {
    const imagePath = el.getAttribute("data-pth");
    if (imagePath) {
      spinner.style.display = "block";
      popupImage.style.display = "none";
      popupImage.src = `/img?path=${encodeURIComponent(imagePath)}`;
      modalWrap.classList.remove("hidden");
      modalWrap.classList.add("flex");
      document.body.style.overflow = "hidden";
    }
  };

  const closePopupFunction = () => {
    modalWrap.classList.add("hidden");
    modalWrap.classList.remove("flex");
    popupImage.src = "";
    document.body.style.overflow = "auto";
  };

  popupImage.onload = () => {
    spinner.style.display = "none";
    popupImage.style.display = "block";
  };

  popupImage.onerror = () => {
    spinner.style.display = "none";
    // Optionally, show an error message in the popup?
    closePopupFunction();
  };

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
