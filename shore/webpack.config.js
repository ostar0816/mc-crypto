const webpack = require('webpack'),
      path = require('path'),
	  BundleTracker = require('webpack-bundle-tracker');

module.exports = {
        context: __dirname + "/static",
        entry: "./js/main.js",
        output: {
            path: __dirname + "/static/dist",
            filename: "./js/scripts.min.js"
        },
        plugins: [
            new webpack.IgnorePlugin(/\.\/locale$/),
            new BundleTracker({filename: './webpack-stats.json'})
        ]
};
