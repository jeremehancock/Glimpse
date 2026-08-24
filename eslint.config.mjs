import js from '@eslint/js';
import globals from 'globals';

export default [
  {
    // The legacy single-file app. Its JavaScript lives inline in index.html,
    // which ESLint does not read, and sw.js/offline.html are written against it.
    // The rewrite replaces all three; these entries go with them.
    ignores: ['web/index.html', 'web/sw.js', 'web/offline.html', 'node_modules/**'],
  },
  js.configs.recommended,
  {
    files: ['web/**/*.js'],
    languageOptions: {
      ecmaVersion: 2024,
      sourceType: 'module',
      globals: { ...globals.browser, Alpine: 'readonly' },
    },
    rules: {
      eqeqeq: ['error', 'always'],
      'no-var': 'error',
      'prefer-const': 'error',
      // An unused catch binding is fine; an unused anything else is a leftover.
      'no-unused-vars': ['error', { caughtErrors: 'none' }],
    },
  },
  {
    // The service worker has its own globals and no DOM.
    files: ['web/sw.js'],
    languageOptions: { globals: globals.serviceworker },
  },
];
