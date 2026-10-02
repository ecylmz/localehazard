import js from '@eslint/js';
import unicorn from 'eslint-plugin-unicorn';
import sonarjs from 'eslint-plugin-sonarjs';
export default [
  { files: ['p*.js'], ...js.configs.all },
  { files: ['p*.js'], ...unicorn.configs.all },
  { files: ['p*.js'], ...sonarjs.configs.recommended },
];
