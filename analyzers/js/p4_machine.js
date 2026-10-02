// Role: machine text (protocol keyword match).
export function isKeyword(token, keyword) { return token.localeCompare(keyword, undefined, { sensitivity: 'accent' }) === 0; }
