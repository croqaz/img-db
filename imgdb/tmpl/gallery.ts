function preventDefault(ev: Event) {
    ev.preventDefault();
}
function reverseString(str: string): string {
    return str.split('').reverse().join('');
}
function sluggify(str: string): string {
    return str
        .replace(/[^a-zA-Z0-9 -]/gi, '-')
        .replace(/ /g, '-')
        .replace(/-+/g, '-')
        .replace(/-+$/, '');
}
function rgbLightness(r: number, g: number, b: number) {
    return (Math.max(r, g, b) + Math.min(r, g, b)) / 2;
}

// global sort by name
let sortName = '';
// global enabled groups
let enableGroups = false;

// canvas used for drawing
const drawCtx = document.createElement('canvas').getContext('2d');
drawCtx.imageSmoothingEnabled = true;

function imageSortKey(img: HTMLImageElement): any {
    // defines the sort key for each image, based on the sort class name
    if (sortName === 'date') return img.getAttribute('data-date');
    if (sortName === 'bytes') return parseInt(img.getAttribute('data-bytes'));
    if (sortName === 'camera,model') return (img.getAttribute('data-make-model') || '') + ';' + img.getAttribute('data-date');
    if (sortName === 'width,height' || sortName === 'height,width') {
        const [w, h] = img.getAttribute('data-size').split(',');
        return { w: parseInt(w), h: parseInt(h), b: parseInt(img.getAttribute('data-bytes')) };
    }
    if (sortName === 'type,mode')
        return img.getAttribute('data-format') + ' ' + img.getAttribute('data-mode') + ';' + img.getAttribute('data-date');
    if (sortName === 'top colors') {
        return (img.getAttribute('data-top-colors') || '').split(',')[0] + ';' + img.getAttribute('data-date');
    } else if (sortName === 'color lightness') {
        // draw the thumb on a smooth canvas and get the avg color
        // this is pretty unstable and browser dependant
        drawCtx.drawImage(img, 0, 0, 1, 1);
        const rgbx: Uint8ClampedArray = drawCtx.getImageData(0, 0, 1, 1).data;
        // img.parentNode.style.backgroundColor = `rgb(${rgbx[0]}, ${rgbx[1]}, ${rgbx[2]})`;
        // @ts-ignore
        return rgbLightness(...rgbx) * 100;
    } else if (
        sortName === 'ahash' ||
        sortName === 'dhash' ||
        sortName === 'vhash' ||
        sortName === 'bhash' ||
        sortName === 'rchash'
    ) {
        return img.getAttribute(`data-${sortName}`) || '';
    } else if (
        sortName === 'ahash inverse' ||
        sortName === 'dhash inverse' ||
        sortName === 'vhash inverse' ||
        sortName === 'rchash inverse'
    ) {
        const v = sortName.split(' ')[0];
        return reverseString(img.getAttribute(`data-${v}`) || '');
    } else console.error(`Invalid sort function`);
}

function imageSortAB(): any {
    // defines the sort order between 2 images, based on the sort keys
    if (sortName === 'bytes' || sortName === 'color lightness') return (a, b) => b[0] - a[0];
    else if (sortName === 'width,height') {
        return (a, b) => b[0].w - a[0].w || b[0].h - a[0].h || b[0].b - a[0].b;
    } else if (sortName === 'height,width') {
        return (a, b) => b[0].h - a[0].h || b[0].w - a[0].w || b[0].b - a[0].b;
    }
    return;
}

// convert sort key to a group name
const valueToGroup = {
    date: (v: string) => v.slice(0, 7), // year-month
    bytes: (v: number) => `${Math.round(v / 1048576)}mb`, // mb
    'camera,model': (v: string) => v.split(';')[0] || 'unknown',
    'width,height': (v: any) => `${Math.floor(v.w / 1000)}k`,
    'height,width': (v: any) => `${Math.floor(v.h / 1000)}k`,
    'type,mode': (v: string) => v.split(';')[0],
    'top colors': (v: string) => (v.split(';')[0] || '').split('=')[0] || 'unknown',
    'color lightness': (v: number) => `${Math.round(v / 1000)}L`, // light
};
for (let algo of [
    'ahash',
    'dhash',
    'vhash',
    'bhash',
    'rchash',
    'ahash inverse',
    'dhash inverse',
    'vhash inverse',
    'rchash inverse',
]) {
    valueToGroup[algo] = (v: string) => v.slice(0, 3);
}

function moveImageGroup(img: HTMLImageElement, value: string): void {
    let group = null as HTMLElement;
    if (!enableGroups) {
        group = document.querySelector('.no-group.grid-layout');
        group.appendChild(img.parentElement);
        return;
    }
    const s = sluggify(sortName);
    const g = valueToGroup[sortName](value);
    // find or create the group
    group = document.querySelector(`.grid-layout[data-${s}="${g}"]`);
    if (!group) {
        group = document.createElement('div');
        group.className = 'group grid-layout';
        group.setAttribute(`data-${s}`, g);
        const item = document.createElement('div');
        item.className = 'grid-item grid-header';
        const title = document.createElement('h4');
        title.innerText = g;
        item.appendChild(title);
        group.appendChild(item);
        const main = document.getElementById('mainLayout');
        main.appendChild(group);
    }
    group.appendChild(img.parentElement);
}

function setupGrid(): void {
    // detect the widest img
    let maxWidth = 0;
    const imgs = document.querySelectorAll('#mainLayout img');
    for (let img of Array.from(imgs) as HTMLImageElement[]) {
        if (img.naturalWidth > maxWidth) maxWidth = img.naturalWidth;
    }
    // fix CSS grid layout using the widest img
    const cssGridFix = document.createElement('style');
    cssGridFix.innerText = `.grid-layout { grid-template-columns:repeat( auto-fill, minmax(${maxWidth}px, 1fr) ); }`;
    document.head.appendChild(cssGridFix);
}

function setupSort(): void {
    const sortBy = document.getElementById('sortBy') as HTMLSelectElement;
    const sortOrd = document.getElementById('sortOrd') as HTMLButtonElement;
    const toggleGroups = document.querySelector('#toggleGroups') as HTMLInputElement;
    const noGroup = document.querySelector('#mainLayout .no-group.grid-layout');
    const isArrowDown = () => sortOrd.innerText.trim() === '🠗';
    const isArrowUp = () => sortOrd.innerText.trim() === '🠕';
    sortOrd.onclick = function (ev: Event) {
        // 🠗 🠕
        if (isArrowUp()) (ev.target as HTMLElement).innerText = '🠗';
        else (ev.target as HTMLElement).innerText = '🠕';
        sortBy.dispatchEvent(new Event('change'));
    };
    toggleGroups.onclick = function () {
        enableGroups = toggleGroups.checked;
        sortBy.dispatchEvent(new Event('change'));
    };
    sortBy.onchange = function () {
        sortName = sortBy.value;
        const values = [];
        // select only VISIBLE imgs, the hidden images will not be sorted
        const imgs = document.querySelectorAll('#mainLayout .grid-layout img');
        for (let img of Array.from(imgs) as HTMLImageElement[]) {
            values.push([imageSortKey(img), img]);
            // move image in no-group
            noGroup.appendChild(img.parentElement);
        }
        // remove empty groups
        for (let div of document.querySelectorAll('#mainLayout .grid-layout')) {
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
    const searchBy = document.getElementById('searchBy') as HTMLInputElement;
    const clearSearch = document.getElementById('clearSearch') as HTMLButtonElement;
    clearSearch.onclick = function () {
        searchBy.value = '';
        searchBy.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    };

    const hidden =  document.querySelector('#mainLayout .hidden');
    const sortBy = document.getElementById('sortBy') as HTMLSelectElement;
    const noGroup = document.querySelector('#mainLayout .no-group.grid-layout');
    const safeData = (img: HTMLImageElement, name: string) => (img.getAttribute(`data-${name}`) || '').toLowerCase();
    searchBy.onkeydown = function (ev) {
        if (ev.key === 'Enter') {
            const query = searchBy.value.toLowerCase().trim();
            // select all imgs, including invisible
            const imgs = document.querySelectorAll('#mainLayout img');
            for (let img of Array.from(imgs) as HTMLImageElement[]) {
                const [w, h] = img.getAttribute('data-size').split(',');
                if (
                    query === '' ||
                    w === query ||
                    h === query ||
                    img.getAttribute('data-bytes') === query ||
                    img.getAttribute('id').toLowerCase() === query ||
                    img.getAttribute('data-format').toLowerCase() === query ||
                    img.getAttribute('data-mode').toLowerCase() === query ||
                    safeData(img, 'make-model').startsWith(query) ||
                    safeData(img, 'ahash').startsWith(query) ||
                    safeData(img, 'dhash').startsWith(query) ||
                    safeData(img, 'vhash').startsWith(query) ||
                    safeData(img, 'bhash').startsWith(query) ||
                    safeData(img, 'rchash').startsWith(query) ||
                    img.getAttribute('data-date').includes(query)
                ) {
                    (img.parentNode as HTMLElement).style.display = 'grid';
                    // move image in no-group, to be picked up by sort
                    noGroup.appendChild(img.parentElement);
                } else {
                    // hide element and move
                    (img.parentNode as HTMLElement).style.display = 'none';
                    hidden.appendChild(img.parentElement);
                }
            }
            sortBy.dispatchEvent(new Event('change'));
        }
    };
}

function setupModal(): void {
    const modal = document.getElementById('modalWrap');
    const modalImg = document.getElementById('modalImg') as HTMLImageElement;
    const wheelEvent = 'onwheel' in modal ? 'wheel' : 'mousewheel';
    function disableScroll() {
        window.addEventListener(wheelEvent, preventDefault, { passive: false });
        window.addEventListener('touchmove', preventDefault, { passive: false });
    }
    function enableScroll() {
        // @ts-ignore
        window.removeEventListener(wheelEvent, preventDefault, { passive: false });
        // @ts-ignore
        window.removeEventListener('touchmove', preventDefault, { passive: false });
    }
    function closeModal() {
        modal.classList.remove('open');
        enableScroll();
        modalImg.src = '';
    }
    modal.onclick = function (ev: Event) {
        if ((ev.target as HTMLElement).tagName !== 'IMG') closeModal();
    };
    document.body.onkeydown = function (ev: KeyboardEvent) {
        if (ev.key === 'Escape') closeModal();
        else if (ev.key === 'ArrowRight' || ev.key === 'ArrowLeft') {
            let next = null as HTMLElement;
            const img = document.getElementById(modalImg.getAttribute('data-id'));
            if (ev.key === 'ArrowRight') next = img.parentElement.nextElementSibling.querySelector('img');
            else next = img.parentElement.previousElementSibling.querySelector('img');
            modalImg.src = next.getAttribute('data-pth');
            modalImg.setAttribute('data-id', next.id);
        }
    };
    document.getElementById('mainLayout').onclick = function (ev: Event) {
        const tgt = ev.target as HTMLElement;
        if (tgt.tagName !== 'IMG') {
            return;
        }
        modalImg.src = tgt.getAttribute('data-pth');
        modalImg.setAttribute('data-id', tgt.id);
        modal.classList.add('open');
        disableScroll();
    };
}

window.addEventListener('load', function (): void {
    const searchBy = document.getElementById('searchBy') as HTMLInputElement;
    searchBy.value = '';
    const sortBy = document.getElementById('sortBy') as HTMLSelectElement;
    // @ts-ignore
    sortBy.value = window.sortName;

    setupGrid();
    setupSort();
    setupSearch();
    setupModal();

    // trigger initial sort
    sortBy.dispatchEvent(new Event('change'));
});
