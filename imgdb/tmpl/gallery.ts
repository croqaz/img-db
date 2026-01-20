// Formatted with Deno fmt:
// deno fmt imgdb/tmpl/gallery.ts --line-width 120
// Transpile with Deno bundle:
// deno bundle --no-check --no-lock --output=imgdb/tmpl/gallery.js imgdb/tmpl/gallery.ts
//
function preventDefault(ev: Event) {
  ev.preventDefault();
}
function reverseString(str: string): string {
  return str.split("").reverse().join("");
}
function sluggify(str: string): string {
  return str
    .replace(/[^a-zA-Z0-9 -]/gi, "-")
    .replace(/ /g, "-")
    .replace(/-+/g, "-")
    .replace(/-+$/, "");
}
function rgbLightness(r: number, g: number, b: number) {
  return (Math.max(r, g, b) + Math.min(r, g, b)) / 2;
}

// global sort by date
// window.sortName = "";
// global enabled groups
// window.enableGroups = false;

// canvas used for drawing
const drawCtx: CanvasRenderingContext2D = document.createElement("canvas").getContext("2d")!;
drawCtx.imageSmoothingEnabled = true;

function imageSortKey(img: HTMLImageElement): any {
  // defines the sort key for each image, based on the sort class name
  if (!sortName || sortName === "date") return img.getAttribute("data-date");
  if (sortName === "bytes") return parseInt(img.getAttribute("data-bytes"));
  if (sortName === "camera,model") {
    return (img.getAttribute("data-make-model") || "") + ";" + img.getAttribute("data-date");
  }
  if (sortName === "width,height" || sortName === "height,width") {
    const [w, h] = img.getAttribute("data-size").split(",");
    return { w: parseInt(w), h: parseInt(h), b: parseInt(img.getAttribute("data-bytes")) };
  }
  if (sortName === "type,mode") {
    return img.getAttribute("data-format") + " " + img.getAttribute("data-mode") + ";" + img.getAttribute("data-date");
  }
  if (sortName === "top colors") {
    return (img.getAttribute("data-top-colors") || "").split(",")[0] + ";" + img.getAttribute("data-date");
  } else if (sortName === "brightness") {
    return parseInt(img.getAttribute("data-brightness") || "0");
  } else if (
    sortName === "ahash" ||
    sortName === "dhash" ||
    sortName === "vhash" ||
    sortName === "bhash" ||
    sortName === "rchash"
  ) {
    return img.getAttribute(`data-${sortName}`) || "";
  } else if (
    sortName === "ahash inverse" ||
    sortName === "dhash inverse" ||
    sortName === "vhash inverse" ||
    sortName === "rchash inverse"
  ) {
    const v = sortName.split(" ")[0];
    return reverseString(img.getAttribute(`data-${v}`) || "");
  } else console.error(`Invalid sort function: ${sortName}`);
}

function imageSortTitle(img: HTMLImageElement): string {
  // defines the sort title for each image, based on the sort class name
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
    const colors = img.getAttribute("data-top-colors")!.split(",")[0].split("=")[0];
    // img.parentNode.style.backgroundColor = colors;
    return "Clr: " + colors;
  } else if (sortName === "brightness") {
    if (!img.getAttribute("data-brightness")) return "Light: -";
    const light = parseInt(img.getAttribute("data-brightness"));
    // img.parentNode.style.backgroundColor = `rgb(${light}, ${light}, ${light})`;
    return `Light: ${light || "-"}%`;
  } else if (
    sortName === "ahash" ||
    sortName === "dhash" ||
    sortName === "vhash" ||
    sortName === "bhash" ||
    sortName === "rchash"
  ) {
    return `${sortName}: ${img.getAttribute(`data-${sortName}`)?.slice(0, 8) + "…" || ""}`;
  } else if (
    sortName === "ahash inverse" ||
    sortName === "dhash inverse" ||
    sortName === "vhash inverse" ||
    sortName === "rchash inverse"
  ) {
    const v = sortName.split(" ")[0];
    return `rev ${v}: ${reverseString(img.getAttribute(`data-${v}`)?.slice(0, 8)) + "…" || ""}`;
  }

  // Size width x height
  const [w, h] = img.getAttribute("data-size").split(",");
  if (sortName === "width,height") {
    return `W×H ${w}×${h} px`;
  }
  if (sortName === "height,width") {
    return `H×W ${h}×${w} px`;
  }

  return `${img.getAttribute("data-format")} ${w}×${h} px`;
}

function imageSortAB(): any {
  // defines the sort order between 2 images, based on the sort keys
  if (sortName === "bytes" || sortName === "brightness") return (a, b) => b[0] - a[0];
  else if (sortName === "width,height") {
    return (a, b) => b[0].w - a[0].w || b[0].h - a[0].h || b[0].b - a[0].b;
  } else if (sortName === "height,width") {
    return (a, b) => b[0].h - a[0].h || b[0].w - a[0].w || b[0].b - a[0].b;
  }
  return;
}

// convert sort key to a group name
const sortNameToGroup: Record<string, (v: any) => string> = {
  date: (v: string) => v.slice(0, 7), // year-month
  bytes: (v: number) => `${Math.round(v / 1048576)}mb`, // mb
  "camera,model": (v: string) => v.split(";")[0] || "unknown",
  "width,height": (v: any) => `${Math.floor(v.w / 1000)}k`,
  "height,width": (v: any) => `${Math.floor(v.h / 1000)}k`,
  "type,mode": (v: string) => v.split(";")[0],
  "brightness": (v: number) => `${Math.round(v / 10)}L`, // light
  "top colors": (v: string) => (v.split(";")[0] || "").split("=")[0] || "unknown",
};
for (
  let algo of [
    "ahash",
    "dhash",
    "vhash",
    "bhash",
    "rchash",
    "ahash inverse",
    "dhash inverse",
    "vhash inverse",
    "rchash inverse",
  ]
) {
  sortNameToGroup[algo] = (v: string) => v.slice(0, 3);
}

function moveImageGroup(img: HTMLImageElement, value: string): void {
  let group: HTMLElement;
  if (!enableGroups) {
    group = document.querySelector(".no-group.grid-layout")!;
    group.appendChild(img.parentElement);
    return;
  }
  const s = sluggify(sortName);
  const g = sortNameToGroup[sortName](value);
  // find or create the group
  group = document.querySelector(`.grid-layout[data-${s}="${g}"]`)!;
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

function setupGrid(): void {
  // detect the widest img
  let maxWidth = 0;
  const imgs = document.querySelectorAll("#mainLayout img");
  for (let img of Array.from(imgs) as HTMLImageElement[]) {
    if (img.naturalWidth > maxWidth) maxWidth = img.naturalWidth;
  }
  // fix CSS grid layout using the widest img
  const cssGridFix = document.createElement("style");
  cssGridFix.innerText = `.grid-layout { grid-template-columns:repeat( auto-fill, minmax(${maxWidth}px, 1fr) ); }`;
  document.head.appendChild(cssGridFix);
}

function setupSort(): void {
  const sortBy = document.getElementById("sortBy") as HTMLSelectElement;
  const sortOrd = document.getElementById("sortOrd") as HTMLButtonElement;
  const toggleGroups = document.querySelector("#toggleGroups") as HTMLInputElement;
  const noGroup = document.querySelector("#mainLayout .no-group.grid-layout") as HTMLInputElement;
  const isArrowDown = () => sortOrd.innerText.trim() === "🠗";
  const isArrowUp = () => sortOrd.innerText.trim() === "🠕";
  sortOrd.onclick = function (ev: Event) {
    // 🠗 🠕
    if (isArrowUp()) (ev.target as HTMLElement).innerText = "🠗";
    else (ev.target as HTMLElement).innerText = "🠕";
    sortBy.dispatchEvent(new Event("change"));
  };
  toggleGroups.onclick = function () {
    enableGroups = toggleGroups.checked;
    sortBy.dispatchEvent(new Event("change"));
  };
  sortBy.onchange = function () {
    window.sortName = sortBy.value;
    const values = [];
    // select only VISIBLE imgs, the hidden images will not be sorted
    const imgs = document.querySelectorAll("#mainLayout .grid-layout img");
    for (let img of Array.from(imgs) as HTMLImageElement[]) {
      values.push([imageSortKey(img), img]);
      // change the small sub-text description
      img.parentElement.querySelector("small.sub").innerText = imageSortTitle(img);
      // move image in no-group
      noGroup.appendChild(img.parentElement);
    }
    // remove empty groups
    for (let div of document.querySelectorAll("#mainLayout .grid-layout")) {
      // the first element is the grid item header
      if (div.childNodes.length === 1) div.remove();
    }
    values.sort(imageSortAB());
    if (isArrowDown()) values.reverse();
    for (let [v, img] of values) {
      moveImageGroup(img, v);
    }
  };
}

function setupSearch(): void {
  const searchBy = document.getElementById("searchBy") as HTMLInputElement;
  const clearSearch = document.getElementById("clearSearch") as HTMLButtonElement;
  clearSearch.onclick = function () {
    searchBy.value = "";
    searchBy.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
  };

  const hidden = document.querySelector("#mainLayout .hidden");
  const sortBy = document.getElementById("sortBy") as HTMLSelectElement;
  const noGroup = document.querySelector("#mainLayout .no-group.grid-layout");
  const safeData = (img: HTMLImageElement, name: string) => (img.getAttribute(`data-${name}`) || "").toLowerCase();
  searchBy.onkeydown = function (ev) {
    if (ev.key === "Enter") {
      const query = searchBy.value.toLowerCase().trim();
      // select all imgs, including invisible
      const imgs = document.querySelectorAll("#mainLayout img");
      for (let img of Array.from(imgs) as HTMLImageElement[]) {
        const [w, h] = img.getAttribute("data-size").split(",");
        if (
          query === "" ||
          w === query ||
          h === query ||
          img.getAttribute("data-bytes") === query ||
          img.getAttribute("id").toLowerCase() === query ||
          img.getAttribute("data-format").toLowerCase() === query ||
          img.getAttribute("data-mode").toLowerCase() === query ||
          safeData(img, "make-model").startsWith(query) ||
          safeData(img, "ahash").startsWith(query) ||
          safeData(img, "dhash").startsWith(query) ||
          safeData(img, "vhash").startsWith(query) ||
          safeData(img, "bhash").startsWith(query) ||
          safeData(img, "rchash").startsWith(query) ||
          img.getAttribute("data-date").includes(query)
        ) {
          (img.parentNode as HTMLElement).style.display = "grid";
          // move image in no-group, to be picked up by sort
          noGroup.appendChild(img.parentElement);
        } else {
          // hide element and move
          (img.parentNode as HTMLElement).style.display = "none";
          hidden.appendChild(img.parentElement);
        }
      }
      sortBy.dispatchEvent(new Event("change"));
    }
  };
}

function setupModal(): void {
  const modal: HTMLElement = document.getElementById("modalWrap")!;
  const modalImg = document.getElementById("modalImg") as HTMLImageElement;
  const wheelEvent = "onwheel" in modal ? "wheel" : "mousewheel";
  let currentZoom = 1.0; // Track current zoom level
  let baseScale = 1.0; // The initial "fit-to-screen" scale
  let panX = 0; // Track pan X position
  let panY = 0; // Track pan Y position
  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;

  function applyZoom(zoom: number) {
    currentZoom = zoom;
    if (zoom === 1.0) {
      modalImg.style.transform = "";
      modalImg.style.cursor = "";
    } else {
      modalImg.style.transform = `scale(${zoom}) translate(${panX}px, ${panY}px)`;
      modalImg.style.cursor = "move";
    }
  }

  function resetZoom() {
    panX = 0;
    panY = 0;
    applyZoom(1.0);
  }

  // Mouse panning handlers
  modalImg.onmousedown = function (ev: MouseEvent) {
    if (currentZoom > 1.0) {
      isDragging = true;
      // We divide by currentZoom because the translation is affected by the scale
      dragStartX = ev.clientX - panX * currentZoom;
      dragStartY = ev.clientY - panY * currentZoom;
      ev.preventDefault();
      ev.stopPropagation();
    }
  };

  modalImg.onmousemove = function (ev: MouseEvent) {
    if (isDragging && currentZoom > 1.0) {
      // We divide by currentZoom because the translation is affected by the scale
      panX = (ev.clientX - dragStartX) / currentZoom;
      panY = (ev.clientY - dragStartY) / currentZoom;
      applyZoom(currentZoom);
      ev.preventDefault();
    }
  };

  modalImg.onmouseup = function (ev: MouseEvent) {
    isDragging = false;
  };

  modalImg.onmouseleave = function (ev: MouseEvent) {
    isDragging = false;
  };

  function disableScroll() {
    window.addEventListener(wheelEvent, preventDefault, { passive: false });
    window.addEventListener("touchmove", preventDefault, { passive: false });
  }
  function enableScroll() {
    // @ts-ignore
    window.removeEventListener(wheelEvent, preventDefault, { passive: false });
    // @ts-ignore
    window.removeEventListener("touchmove", preventDefault, { passive: false });
  }
  function closeModal() {
    modal.classList.remove("open");
    enableScroll();
    modalImg.src = "";
    resetZoom();
  }
  modal.onclick = function (ev: Event) {
    if ((ev.target as HTMLElement).tagName !== "IMG") closeModal();
  };
  document.body.onkeydown = function (ev: KeyboardEvent) {
    if (!modal.classList.contains("open")) return;
    if (ev.key === "Escape") closeModal();
    else if (ev.key === "ArrowUp" || ev.key === "ArrowDown" || ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
      let next: HTMLElement;
      const img = document.getElementById(modalImg.getAttribute("data-id"));
      if (ev.key === "ArrowRight" || ev.key === "ArrowDown") {
        next = img.parentElement.nextElementSibling.querySelector("img")!;
      } else next = img.parentElement.previousElementSibling.querySelector("img")!;
      modalImg.src = next.getAttribute("data-pth");
      modalImg.setAttribute("data-id", next.id);
      resetZoom();
      ev.preventDefault();
    } else if (ev.key === "Home" || ev.key === "End") {
      const imgs = document.querySelectorAll("#mainLayout img");
      let img: HTMLElement;
      if (ev.key === "Home") {
        img = imgs[0] as HTMLImageElement;
        modalImg.src = img.getAttribute("data-pth");
      } else {
        img = imgs[imgs.length - 1] as HTMLImageElement;
        modalImg.src = img.getAttribute("data-pth");
      }
      modalImg.setAttribute("data-id", img.id);
      resetZoom();
      ev.preventDefault();
    } else if (ev.key === "+" || ev.key === "=") {
      // Zoom in, max 2x of original size
      const maxZoom = 1 / baseScale * 2;
      const newZoom = Math.min(currentZoom + 0.33, maxZoom);
      applyZoom(newZoom);
      ev.preventDefault();
    } else if (ev.key === "-" || ev.key === "_") {
      // Zoom out, min 1x (fit screen)
      const newZoom = Math.max(currentZoom - 0.33, 1.0);
      applyZoom(newZoom);
      ev.preventDefault();
    } else if (ev.key === "0") {
      // Reset zoom to fit height
      resetZoom();
      ev.preventDefault();
    }
  };
  document.getElementById("mainLayout").onclick = function (ev: Event) {
    const tgt = ev.target as HTMLElement;
    if (tgt.tagName !== "IMG") {
      return;
    }
    modalImg.src = tgt.getAttribute("data-pth");
    modalImg.setAttribute("data-id", tgt.id);
    modal.classList.add("open");
    resetZoom();

    modalImg.onload = () => {
      // Calculate the initial "fit-to-screen" scale factor
      const ratio = modalImg.naturalWidth / modalImg.width;
      baseScale = 1 / ratio;
      // Set transform origin to top left for more predictable panning
      modalImg.style.transformOrigin = "top left";
    };

    disableScroll();
  };
}

window.addEventListener("load", function (): void {
  const searchBy = document.getElementById("searchBy") as HTMLInputElement;
  searchBy.value = "";
  const sortBy = document.getElementById("sortBy") as HTMLSelectElement;
  // @ts-ignore
  sortBy.value = window.sortName;

  setupGrid();
  setupSort();
  setupSearch();
  setupModal();

  // trigger initial sort
  sortBy.dispatchEvent(new Event("change"));
});
