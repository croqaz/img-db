// Precompute a popcount table for numbers 0-255
const POPCOUNT_TABLE = new Uint8Array(256);
for (let i = 0; i < 256; i++) {
  let count = 0;
  let n = i;
  while (n > 0) {
    count += n & 1;
    n >>= 1;
  }
  POPCOUNT_TABLE[i] = count;
}
// Compute Hamming Distance between two packed arrays
function getHammingDistance(arrA, arrB) {
  let distance = 0;
  // Assume arrA and arrB are the same length
  for (let i = 0; i < arrA.length; i++) {
    // XOR the numbers to find differences and look up the bit count
    const difference = arrA[i] ^ arrB[i];
    distance += POPCOUNT_TABLE[difference];
  }
  return distance;
}

function imageSortAB(sortName) {
  // Returns the comparison function for sorting img data
  if (sortName === "bytes" || sortName === "illumination" || sortName === "contrast" || sortName === "saturation") {
    return (a, b) => b.score - a.score;
  }
  if (sortName === "width-height") {
    return (a, b) => b.score.w - a.score.w || b.score.b - a.score.b;
  } else if (sortName === "height-width") {
    return (a, b) => b.score.h - a.score.h || b.score.b - a.score.b;
  } else if (sortName.includes("hash")) {
    return (a, b) => b.score - a.score;
  }
  return (a, b) => a.score.localeCompare(b.score);
}

function imageSortHash(items, direction) {
  // Initial stable sort
  items.sort((a, b) => {
    return a.score[0].localeCompare(b.score[0]) * direction;
  });

  // Greedy nearest-neighbor ordering based on Hamming distance
  let current = items[0];
  const ordered = [current];
  const remaining = new Set(items);
  remaining.delete(current);

  while (remaining.size > 0) {
    const currentHash = current.score[1];
    let nearest = null;
    let nearestDist = Infinity;
    for (const candidate of remaining) {
      const candidateHash = candidate.score[1];
      const dist = getHammingDistance(currentHash, candidateHash);
      if (dist < nearestDist) {
        nearestDist = dist;
        nearest = candidate;
      }
    }
    ordered.push(nearest);
    remaining.delete(nearest);
    current = nearest;
  }

  return ordered;
}

self.onmessage = (event) => {
  // { items: [{ score, id }], sortName, direction }
  let items = event.data.items;
  const sortName = event.data.sortName;
  const direction = event.data.direction;
  console.log(`Worker: Sorting ${items.length} items by ${sortName} direction ${direction === 1 ? "asc" : "desc"}`);
  // console.debug("Worker: Sample items before sorting:", items.slice(0, 5));

  try {
    if (sortName === "chash" || sortName === "jhash" || sortName === "rchash") {
      items = imageSortHash(items, direction);
    } else {
      items.sort(imageSortAB(sortName));
    }
  } catch (error) {
    console.error("Worker: Error during sorting:", error);
  }

  self.postMessage(items.map((elem) => elem.id));
};
