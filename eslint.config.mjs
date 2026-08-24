import js from '@eslint/js';
import globals from 'globals';

export default [
  {
    ignores: [
      // Vendored, minified, third-party. Not ours to lint or to reformat, and
      // the only correct way to change it is to drop in a new release.
      'web/assets/alpine.min.js',
      // The legacy single-file app. Its JavaScript lives inline in index.html,
      // which ESLint does not read. The frontend rewrite that splits it into
      // modules removes this entry.
      'web/index.html',
      'web/offline.html',
      'node_modules/**',
    ],
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
