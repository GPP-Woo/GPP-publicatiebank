import * as esbuild from 'esbuild';
import {sassPlugin} from 'esbuild-sass-plugin';

await esbuild.build({
  entryPoints: [
    'src/woo_publications/scss/screen.scss',
    'src/woo_publications/scss/admin/admin_overrides.scss',
  ],
  bundle: true,
  minify: true,
  sourcemap: true,
  outdir: 'src/woo_publications/static/bundles/',
  plugins: [sassPlugin({embedded: true})],
  external: ['*.svg', '*.png', '*.woff2', '*.ttf'],
})
