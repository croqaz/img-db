// imgdb/tmpl/gallery.ts
function preventDefault(ev) {
  ev.preventDefault();
}
function reverseString(str) {
  return str.split("").reverse().join("");
}
function sluggify(str) {
  return str.replace(/[^a-zA-Z0-9 -]/gi, "-").replace(/ /g, "-").replace(/-+/g, "-").replace(/-+$/, "");
}
function rgbLightness(r, g, b) {
  return (Math.max(r, g, b) + Math.min(r, g, b)) / 2;
}
var enableGroups = false;
var drawCtx = document.createElement("canvas").getContext("2d");
drawCtx.imageSmoothingEnabled = true;
function imageSortKey(img) {
  if (!sortName || sortName === "date") return img.getAttribute("data-date");
  if (sortName === "bytes") return parseInt(img.getAttribute("data-bytes"));
  if (sortName === "camera,model") {
    return (img.getAttribute("data-make-model") || "") + ";" + img.getAttribute("data-date");
  }
  if (sortName === "width,height" || sortName === "height,width") {
    const [w, h] = img.getAttribute("data-size").split(",");
    return {
      w: parseInt(w),
      h: parseInt(h),
      b: parseInt(img.getAttribute("data-bytes"))
    };
  }
  if (sortName === "type,mode") {
    return img.getAttribute("data-format") + " " + img.getAttribute("data-mode") + ";" + img.getAttribute("data-date");
  }
  if (sortName === "top colors") {
    return (img.getAttribute("data-top-colors") || "").split(",")[0] + ";" + img.getAttribute("data-date");
  } else if (sortName === "color lightness") {
    drawCtx.drawImage(img, 0, 0, 1, 1);
    const rgbx = drawCtx.getImageData(0, 0, 1, 1).data;
    const lightness = rgbLightness(...rgbx) * 100;
    img.setAttribute("data-lightness", lightness.toString());
    return lightness;
  } else if (sortName === "ahash" || sortName === "dhash" || sortName === "vhash" || sortName === "bhash" || sortName === "rchash") {
    return img.getAttribute(`data-${sortName}`) || "";
  } else if (sortName === "ahash inverse" || sortName === "dhash inverse" || sortName === "vhash inverse" || sortName === "rchash inverse") {
    const v = sortName.split(" ")[0];
    return reverseString(img.getAttribute(`data-${v}`) || "");
  } else console.error(`Invalid sort function: ${sortName}`);
}
function imageSortTitle(img) {
  if (sortName === "bytes") {
    const bytes = parseInt(img.getAttribute("data-bytes"));
    return "Size: " + (bytes / 1024).toFixed(2) + " KB";
  }
  if (sortName === "camera,model") {
    return "Cam: " + (img.getAttribute("data-maker-model") || "unknown");
  }
  if (sortName === "type,mode") {
    return `${img.getAttribute("data-format")} ${img.getAttribute("data-mode")}`;
  }
  if (sortName === "top colors") {
    if (!img.getAttribute("data-top-colors")) return "Clr: -";
    return "Clr: " + (img.getAttribute("data-top-colors") || "").split(",")[0].split("=")[0];
  } else if (sortName === "color lightness") {
    return `Light: ${img.getAttribute("data-lightness")}`;
  } else if (sortName === "ahash" || sortName === "dhash" || sortName === "vhash" || sortName === "bhash" || sortName === "rchash") {
    return `${sortName}: ${img.getAttribute(`data-${sortName}`)?.slice(0, 8) + "\u2026" || ""}`;
  } else if (sortName === "ahash inverse" || sortName === "dhash inverse" || sortName === "vhash inverse" || sortName === "rchash inverse") {
    const v = sortName.split(" ")[0];
    return `rev ${v}: ${reverseString(img.getAttribute(`data-${v}`)?.slice(0, 8)) + "\u2026" || ""}`;
  }
  const [w, h] = img.getAttribute("data-size").split(",");
  if (sortName === "width,height") {
    return `W\xD7H ${w}\xD7${h} px`;
  }
  if (sortName === "height,width") {
    return `H\xD7W ${h}\xD7${w} px`;
  }
  return `${img.getAttribute("data-format")} ${w}\xD7${h} px`;
}
function imageSortAB() {
  if (sortName === "bytes" || sortName === "color lightness") return (a, b) => b[0] - a[0];
  else if (sortName === "width,height") {
    return (a, b) => b[0].w - a[0].w || b[0].h - a[0].h || b[0].b - a[0].b;
  } else if (sortName === "height,width") {
    return (a, b) => b[0].h - a[0].h || b[0].w - a[0].w || b[0].b - a[0].b;
  }
  return;
}
var sortNameToGroup = {
  date: (v) => v.slice(0, 7),
  bytes: (v) => `${Math.round(v / 1048576)}mb`,
  "camera,model": (v) => v.split(";")[0] || "unknown",
  "width,height": (v) => `${Math.floor(v.w / 1e3)}k`,
  "height,width": (v) => `${Math.floor(v.h / 1e3)}k`,
  "type,mode": (v) => v.split(";")[0],
  "top colors": (v) => (v.split(";")[0] || "").split("=")[0] || "unknown",
  "color lightness": (v) => `${Math.round(v / 1e3)}L`
};
for (let algo of [
  "ahash",
  "dhash",
  "vhash",
  "bhash",
  "rchash",
  "ahash inverse",
  "dhash inverse",
  "vhash inverse",
  "rchash inverse"
]) {
  sortNameToGroup[algo] = (v) => v.slice(0, 3);
}
function moveImageGroup(img, value) {
  let group;
  if (!enableGroups) {
    group = document.querySelector(".no-group.grid-layout");
    group.appendChild(img.parentElement);
    return;
  }
  const s = sluggify(sortName);
  const g = sortNameToGroup[sortName](value);
  group = document.querySelector(`.grid-layout[data-${s}="${g}"]`);
  if (!group) {
    group = document.createElement("div");
    group.className = "group grid-layout";
    group.setAttribute(`data-${s}`, g);
    const item = document.createElement("div");
    item.className = "grid-item grid-header";
    const title = document.createElement("h4");
    title.innerText = g;
    item.appendChild(title);
    group.appendChild(item);
    const main = document.getElementById("mainLayout");
    main.appendChild(group);
  }
  group.appendChild(img.parentElement);
}
function setupGrid() {
  let maxWidth = 0;
  const imgs = document.querySelectorAll("#mainLayout img");
  for (let img of Array.from(imgs)) {
    if (img.naturalWidth > maxWidth) maxWidth = img.naturalWidth;
  }
  const cssGridFix = document.createElement("style");
  cssGridFix.innerText = `.grid-layout { grid-template-columns:repeat( auto-fill, minmax(${maxWidth}px, 1fr) ); }`;
  document.head.appendChild(cssGridFix);
}
function setupSort() {
  const sortBy = document.getElementById("sortBy");
  const sortOrd = document.getElementById("sortOrd");
  const toggleGroups = document.querySelector("#toggleGroups");
  const noGroup = document.querySelector("#mainLayout .no-group.grid-layout");
  const isArrowDown = () => sortOrd.innerText.trim() === "\u{1F817}";
  const isArrowUp = () => sortOrd.innerText.trim() === "\u{1F815}";
  sortOrd.onclick = function(ev) {
    if (isArrowUp()) ev.target.innerText = "\u{1F817}";
    else ev.target.innerText = "\u{1F815}";
    sortBy.dispatchEvent(new Event("change"));
  };
  toggleGroups.onclick = function() {
    enableGroups = toggleGroups.checked;
    sortBy.dispatchEvent(new Event("change"));
  };
  sortBy.onchange = function() {
    window.sortName = sortBy.value;
    const values = [];
    const imgs = document.querySelectorAll("#mainLayout .grid-layout img");
    for (let img of Array.from(imgs)) {
      values.push([
        imageSortKey(img),
        img
      ]);
      img.parentElement.querySelector("small.sub").innerText = imageSortTitle(img);
      noGroup.appendChild(img.parentElement);
    }
    for (let div of document.querySelectorAll("#mainLayout .grid-layout")) {
      if (div.childNodes.length === 1) div.remove();
    }
    values.sort(imageSortAB());
    if (isArrowDown()) values.reverse();
    for (let [v, img] of values) {
      moveImageGroup(img, v);
    }
  };
}
function setupSearch() {
  const searchBy = document.getElementById("searchBy");
  const clearSearch = document.getElementById("clearSearch");
  clearSearch.onclick = function() {
    searchBy.value = "";
    searchBy.dispatchEvent(new KeyboardEvent("keydown", {
      key: "Enter"
    }));
  };
  const hidden = document.querySelector("#mainLayout .hidden");
  const sortBy = document.getElementById("sortBy");
  const noGroup = document.querySelector("#mainLayout .no-group.grid-layout");
  const safeData = (img, name) => (img.getAttribute(`data-${name}`) || "").toLowerCase();
  searchBy.onkeydown = function(ev) {
    if (ev.key === "Enter") {
      const query = searchBy.value.toLowerCase().trim();
      const imgs = document.querySelectorAll("#mainLayout img");
      for (let img of Array.from(imgs)) {
        const [w, h] = img.getAttribute("data-size").split(",");
        if (query === "" || w === query || h === query || img.getAttribute("data-bytes") === query || img.getAttribute("id").toLowerCase() === query || img.getAttribute("data-format").toLowerCase() === query || img.getAttribute("data-mode").toLowerCase() === query || safeData(img, "make-model").startsWith(query) || safeData(img, "ahash").startsWith(query) || safeData(img, "dhash").startsWith(query) || safeData(img, "vhash").startsWith(query) || safeData(img, "bhash").startsWith(query) || safeData(img, "rchash").startsWith(query) || img.getAttribute("data-date").includes(query)) {
          img.parentNode.style.display = "grid";
          noGroup.appendChild(img.parentElement);
        } else {
          img.parentNode.style.display = "none";
          hidden.appendChild(img.parentElement);
        }
      }
      sortBy.dispatchEvent(new Event("change"));
    }
  };
}
function setupModal() {
  const modal = document.getElementById("modalWrap");
  const modalImg = document.getElementById("modalImg");
  const wheelEvent = "onwheel" in modal ? "wheel" : "mousewheel";
  function disableScroll() {
    window.addEventListener(wheelEvent, preventDefault, {
      passive: false
    });
    window.addEventListener("touchmove", preventDefault, {
      passive: false
    });
  }
  function enableScroll() {
    window.removeEventListener(wheelEvent, preventDefault, {
      passive: false
    });
    window.removeEventListener("touchmove", preventDefault, {
      passive: false
    });
  }
  function closeModal() {
    modal.classList.remove("open");
    enableScroll();
    modalImg.src = "";
  }
  modal.onclick = function(ev) {
    if (ev.target.tagName !== "IMG") closeModal();
  };
  document.body.onkeydown = function(ev) {
    if (!modal.classList.contains("open")) return;
    if (ev.key === "Escape") closeModal();
    else if (ev.key === "ArrowUp" || ev.key === "ArrowDown" || ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
      let next;
      const img = document.getElementById(modalImg.getAttribute("data-id"));
      if (ev.key === "ArrowRight" || ev.key === "ArrowDown") {
        next = img.parentElement.nextElementSibling.querySelector("img");
      } else next = img.parentElement.previousElementSibling.querySelector("img");
      modalImg.src = next.getAttribute("data-pth");
      modalImg.setAttribute("data-id", next.id);
      ev.preventDefault();
    } else if (ev.key === "Home" || ev.key === "End") {
      const imgs = document.querySelectorAll("#mainLayout img");
      let img;
      if (ev.key === "Home") {
        img = imgs[0];
        modalImg.src = img.getAttribute("data-pth");
      } else {
        img = imgs[imgs.length - 1];
        modalImg.src = img.getAttribute("data-pth");
      }
      modalImg.setAttribute("data-id", img.id);
      ev.preventDefault();
    }
  };
  document.getElementById("mainLayout").onclick = function(ev) {
    const tgt = ev.target;
    if (tgt.tagName !== "IMG") {
      return;
    }
    modalImg.src = tgt.getAttribute("data-pth");
    modalImg.setAttribute("data-id", tgt.id);
    modal.classList.add("open");
    disableScroll();
  };
}
window.addEventListener("load", function() {
  const searchBy = document.getElementById("searchBy");
  searchBy.value = "";
  const sortBy = document.getElementById("sortBy");
  sortBy.value = window.sortName;
  setupGrid();
  setupSort();
  setupSearch();
  setupModal();
  sortBy.dispatchEvent(new Event("change"));
});
