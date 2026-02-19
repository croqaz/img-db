// Formatted with Deno fmt:
// deno fmt imgdb/tmpl/gallery.ts --line-width 120
// Transpile with Deno bundle:
// deno bundle --no-check --no-lock --output=imgdb/tmpl/gallery.js imgdb/tmpl/gallery.ts
//
function preventDefault(ev: Event) {
  ev.preventDefault();
}
function base36ToBigInt(str: string): bigint {
  const digits = "0123456789abcdefghijklmnopqrstuvwxyz";
  let result = 0n;
  for (const char of str.toLowerCase()) {
    result = result * 36n + BigInt(digits.indexOf(char));
  }
  return result;
}
function sluggify(str: string): string {
  return str
    .replace(/[^a-zA-Z0-9 -]/gi, "-")
    .replace(/ /g, "-")
    .replace(/-+/g, "-")
    .replace(/-+$/, "");
}

// global sort by date
// window.sortName = "";
// global enabled groups
// window.enableGroups = false;

function imageSortKey(img: HTMLImageElement): any {
  // defines the sort key for each image, based on the sort class name
  if (!sortName || sortName === "date") return img.getAttribute("data-date");
  if (sortName === "bytes") return parseInt(img.getAttribute("data-bytes"));
  if (sortName === "camera,model") {
    return (img.getAttribute("data-maker-model") || "") + ";" + img.getAttribute("data-date");
  }
  if (sortName === "width,height" || sortName === "height,width") {
    const [w, h] = img.getAttribute("data-size").split(",");
    return { w: parseInt(w), h: parseInt(h), b: parseInt(img.getAttribute("data-bytes")) };
  }
  if (sortName === "type,mode") {
    return img.getAttribute("data-format") + " " + img.getAttribute("data-mode") + ";" + img.getAttribute("data-date");
  }
  if (sortName === "top-colors") {
    return (img.getAttribute(`data-${sortName}`) || "").split(",")[0] + ";" + img.getAttribute("data-date");
  } else if (
    sortName === "illumination" || sortName === "contrast" || sortName === "saturation"
  ) {
    return parseInt(img.getAttribute(`data-${sortName}`) || "0");
  } else if (sortName === "bhash") {
    return img.getAttribute(`data-${sortName}`) || "";
  } else if (
    sortName === "ahash" ||
    sortName === "chash" ||
    sortName === "dhash" ||
    sortName === "vhash" ||
    sortName === "rchash"
  ) {
    return base36ToBigInt(img.getAttribute(`data-${sortName}`) || "");
  } else console.error(`Invalid sort function: ${sortName}`);
}

function imageSortTitle(img: HTMLImageElement): string {
  // defines the sort title for each image, based on the sort class name
  // reset the background color
  img.parentNode.style.backgroundColor = "";
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
  if (sortName === "top-colors") {
    if (!img.getAttribute("data-top-colors")) return "Color: -";
    const color = img.getAttribute("data-top-colors")!.split(",")[0].split("=")[0];
    img.parentNode.style.backgroundColor = color;
    return "Color: " + color;
  } else if (sortName === "illumination") {
    if (!img.getAttribute(`data-${sortName}`)) return "Light: -";
    const light = parseInt(img.getAttribute(`data-${sortName}`) || "0");
    img.parentNode.style.backgroundColor = `hsl(0, 0%, ${light}%)`;
    return `Light: ${light || "-"}%`;
  } else if (sortName === "contrast") {
    const val = img.getAttribute("data-contrast");
    return val ? `Contrast: ${val}` : "Contrast: -";
  } else if (sortName === "saturation") {
    const val = img.getAttribute("data-saturation");
    return val ? `Saturation: ${val}%` : "Saturation: -";
  } else if (sortName === "bhash" || sortName === "chash" || sortName === "rchash") {
    return `${sortName}: ${img.getAttribute(`data-${sortName}`)?.slice(0, 8) + "…" || ""}`;
  } else if (
    sortName === "ahash" ||
    sortName === "dhash" ||
    sortName === "vhash"
  ) {
    return `${sortName}: ${img.getAttribute(`data-${sortName}`) || ""}`;
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
  if (
    sortName === "bytes" || sortName === "illumination" || sortName === "contrast" ||
    sortName === "saturation"
  ) return (a, b) => b[0] - a[0];
  if (
    sortName === "ahash" || sortName === "chash" || sortName === "dhash" || sortName === "vhash" ||
    sortName === "rchash"
    // bigint comparison
  ) return (a, b) => Number(b[0] - a[0]);
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
  "camera,model": (v: string) => v.split(";")[0].replaceAll("-", " ") || "unknown",
  "width,height": (v: any) => `${Math.floor(v.w / 1000)}k`,
  "height,width": (v: any) => `${Math.floor(v.h / 1000)}k`,
  "type,mode": (v: string) => v.split(";")[0],
  "illumination": (v: number) => `${Math.round(v / 10)}L`, // light
  "contrast": (v: number) => `${Math.round(v / 20)}C`, // contrast groups by 20
  "saturation": (v: number) => `${Math.round(v / 10)}S`, // saturation groups by 10
  "top-colors": (v: string) => (v.split(";")[0] || "").split("=")[0] || "unknown",
};
for (
  let algo of [
    "ahash",
    "chash",
    "dhash",
    "vhash",
    "bhash",
    "rchash",
  ]
) {
  sortNameToGroup[algo] = (v: string) => v.toString()[0] + "…";
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
    window.enableGroups = toggleGroups.checked;
    sortBy.dispatchEvent(new Event("change"));
  };
  sortBy.onchange = function () {
    window.sortName = sortBy.value;
    const values: [any, HTMLImageElement][] = [];
    // select only VISIBLE imgs, the hidden images will not be sorted
    const imgs = document.querySelectorAll("#mainLayout .grid-layout img");
    for (const img of Array.from(imgs) as HTMLImageElement[]) {
      values.push([imageSortKey(img), img]);
      // change the small sub-text description
      img.parentElement.querySelector("small.sub").innerText = imageSortTitle(img);
      // move image in no-group
      noGroup.appendChild(img.parentElement!);
    }
    // remove empty groups
    for (const div of document.querySelectorAll("#mainLayout .grid-layout")) {
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
        const llmText = img.getAttribute("data-obj-detect-llm");
        if (
          query === "" ||
          w === query ||
          h === query ||
          img.getAttribute("data-bytes") === query ||
          img.getAttribute("id")!.toLowerCase() === query ||
          img.getAttribute("data-format")!.toLowerCase() === query ||
          img.getAttribute("data-mode")!.toLowerCase() === query ||
          safeData(img, "maker-model").startsWith(query) ||
          img.getAttribute("data-date")!.includes(query) ||
          (query.startsWith("#") && safeData(img, "top-colors").includes(query)) ||
          (llmText && llmText.toLowerCase().includes(query))
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

  let currentScale = 1;
  let translateX = 0;
  let translateY = 0;
  let isPanning = false;
  let startPanX = 0;
  let startPanY = 0;

  function updateZoomAndPan() {
    modalImg.style.transform = `scale(${currentScale}) translate(${translateX}px, ${translateY}px)`;
  }
  function resetZoomAndPan() {
    currentScale = 1;
    translateX = 0;
    translateY = 0;
    modalImg.style.transform = "";
    modalImg.style.cursor = "default";
  }

  function disableScroll() {
    (window as EventTarget).addEventListener(wheelEvent, preventDefault, { passive: false });
    (window as EventTarget).addEventListener("touchmove", preventDefault, { passive: false });
  }
  function enableScroll() {
    (window as EventTarget).removeEventListener(wheelEvent, preventDefault, false);
    (window as EventTarget).removeEventListener("touchmove", preventDefault, false);
  }
  function closeModal() {
    modal.classList.remove("open");
    modalImg.src = "";
    enableScroll();
    resetZoomAndPan();
  }
  modal.onclick = function (ev: Event) {
    if ((ev.target as HTMLElement).tagName !== "IMG") closeModal();
  };

  modalImg.onmousedown = (e) => {
    if (currentScale > 1) {
      isPanning = true;
      startPanX = e.clientX - translateX * currentScale;
      startPanY = e.clientY - translateY * currentScale;
      modalImg.style.cursor = "grabbing";
      e.preventDefault();
    }
  };
  modalImg.onmousemove = (e) => {
    if (isPanning) {
      translateX = (e.clientX - startPanX) / currentScale;
      translateY = (e.clientY - startPanY) / currentScale;
      updateZoomAndPan();
    }
  };
  modalImg.onmouseup = () => {
    isPanning = false;
    if (currentScale > 1) {
      modalImg.style.cursor = "move";
    }
  };
  modalImg.onmouseleave = () => {
    isPanning = false;
    if (currentScale > 1) {
      modalImg.style.cursor = "move";
    }
  };

  document.body.onkeydown = function (ev: KeyboardEvent) {
    if (!modal.classList.contains("open")) return;
    if (ev.key === "Escape") closeModal();
    else if (ev.key === "ArrowUp" || ev.key === "ArrowDown" || ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
      resetZoomAndPan();
      let next: HTMLElement;
      const img = document.getElementById(modalImg.getAttribute("data-id")!) as HTMLImageElement;
      if (ev.key === "ArrowRight" || ev.key === "ArrowDown") {
        next = img.parentElement!.nextElementSibling!.querySelector("img")!;
      } else next = img.parentElement!.previousElementSibling!.querySelector("img")!;
      modalImg.src = next.getAttribute("data-pth")!;
      modalImg.setAttribute("data-id", next.id);
      ev.preventDefault();
    } else if (ev.key === "Home" || ev.key === "End") {
      resetZoomAndPan();
      const imgs = document.querySelectorAll("#mainLayout img");
      let img: HTMLElement;
      if (ev.key === "Home") {
        img = imgs[0] as HTMLImageElement;
        modalImg.src = img.getAttribute("data-pth")!;
      } else {
        img = imgs[imgs.length - 1] as HTMLImageElement;
        modalImg.src = img.getAttribute("data-pth")!;
      }
      modalImg.setAttribute("data-id", img.id);
      ev.preventDefault();
    } else if (ev.key === "+" || ev.key === "=") {
      // Zoom in, max 2x of original size
      currentScale = Math.min(2.33, currentScale + 0.333);
      modalImg.style.cursor = "move";
      updateZoomAndPan();
    } else if (ev.key === "-" || ev.key === "_") {
      // Zoom out, min fit screen height
      currentScale = Math.max(1, currentScale - 0.333);
      if (currentScale === 1) {
        resetZoomAndPan();
      } else {
        updateZoomAndPan();
      }
    } else if (ev.key === "0") {
      // Reset zoom to fit height
      resetZoomAndPan();
    }
  };
  document.getElementById("mainLayout").onclick = function (ev: Event) {
    const tgt = ev.target as HTMLElement;
    if (tgt.tagName !== "IMG") {
      return;
    }
    modalImg.src = tgt.getAttribute("data-pth")!;
    modalImg.setAttribute("data-id", tgt.id);
    modal.classList.add("open");
    modalImg.onload = () => {
      resetZoomAndPan();
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
  const enableGroups = document.getElementById("toggleGroups") as HTMLInputElement;
  // @ts-ignore
  window.enableGroups = enableGroups.checked;

  setupGrid();
  setupSort();
  setupSearch();
  setupModal();

  // trigger initial sort
  sortBy.dispatchEvent(new Event("change"));
});
