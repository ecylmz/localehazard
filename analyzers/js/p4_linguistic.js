// Role: linguistic text (user search term against a Turkish name).
export function matchesName(query, name) { return query.localeCompare(name, undefined, { sensitivity: 'accent' }) === 0; }
