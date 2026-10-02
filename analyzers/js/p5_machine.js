// Role: machine text (keys written to a sorted index later searched bytewise).
export function sortIndexKeys(keys) { return keys.sort((a, b) => a.localeCompare(b)); }
