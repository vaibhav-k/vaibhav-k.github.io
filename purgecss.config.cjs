// Re-purge the Bootstrap theme after changing templates:
//   python build.py && npx purgecss --config purgecss.config.cjs
module.exports = {
  content: ['index.html', '404.html'],
  css: ['src/styles.full.css'],
  output: 'css/styles.css',
  // Classes added at runtime by Bootstrap's JS
  safelist: ['active', 'show', 'collapse', 'collapsing', 'collapsed', 'fixed-top', 'navbar-toggler-icon', 'js-scroll-trigger'],
  keyframes: true,
  variables: true,
  fontFace: false,
};
