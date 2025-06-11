const fs = require('fs');


/** Parses package.json */
const pkg = JSON.parse(fs.readFileSync('./package.json', 'utf-8'));

/** Src dir */
const sourcesRoot = 'src/woo_publications/';

/** "Main" static dir */
const staticRoot = `${sourcesRoot}static/`;

/**
 * Application path configuration for use in frontend scripts
 */
module.exports = {
    // Parsed package.json
    package: pkg,

    // Path to the scss entry point
    scssEntry: `${sourcesRoot}scss/screen.scss`,

    // Path to the scss (sources) directory
    scssSrcDir: `${sourcesRoot}scss/`,

    // Path to the (transpiled) js directory
    jsDir: `${staticRoot}bundles/`,
};
