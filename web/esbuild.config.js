const fs = require("fs");
const { build } = require("esbuild");
const sveltePreprocess = require("svelte-preprocess");
const sveltePlugin = require("esbuild-svelte");
const sassPlugin = require("esbuild-sass-plugin").default;


const production = process.env.NODE_ENV === "production";
const development = process.env.NODE_ENV === "development";

const watch = development
    ? {
          onRebuild(error) {
              console.timeLog;

              if (error) {
                  console.error(
                      new Date(),
                      "esbuild: build failed:",
                      error.getMessage(),
                  );
              } else {
                  console.log(new Date(), "esbuild: build succeeded");
              }
          },
      }
    : false;

/**
 * This should point to all entry points for scripts.
 * Each one will create one js and one css file in `../src/dist/web'
 */
const entryPoints = ["hypertts.ts"];

/**
 * Esbuild build options
 * See https://esbuild.github.io/api/#build-api for more
 */
const options = {
    entryPoints,
    outdir: "./",
    format: "iife",
    target: "es6",
    bundle: true,
    minify: production,
    treeShaking: production,
    sourcemap: !production,
    pure: production ? ["console.log", "console.time", "console.timeEnd"] : [],
    watch,
    external: ["svelte", "anki"],
    plugins: [
        sveltePlugin({
            preprocess: sveltePreprocess({
                scss: {
                    includePaths: ["anki/sass"],
                },
            }),
        }),
        sassPlugin(),
    ],
    loader: {
        ".png": "dataurl",
        ".svg": "text",
    },
};

build(options).catch((err) => {
    console.error(err);
    process.exit(1);
});

if (watch) {
    console.log("Watching for changes...");
}
