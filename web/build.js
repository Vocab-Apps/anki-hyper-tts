const fs = require("fs");
const esbuild = require("esbuild");
const sveltePlugin = require("esbuild-svelte");

esbuild
  .build({
    entryPoints: ["./hypertts.js"],
    outdir: "../",
    format: "esm",
    minify: false /* do not set this to true */,
    bundle: true,
    splitting: false,
    plugins: [sveltePlugin()],
  })
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
