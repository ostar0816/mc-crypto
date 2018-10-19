const webpack = require('webpack'),
    UglifyJsPlugin = require('uglifyjs-webpack-plugin'),
    path = require('path');

module.exports = {
    context: __dirname + "/static",
    entry: "./js/main.js",
    output: {
        path: __dirname + "/static/dist/prod",
        filename: "./js/scripts.min.js"
    },
    plugins: [
        new webpack.IgnorePlugin(/\.\/locale$/),
        new UglifyJsPlugin({
            uglifyOptions: {
                ecma: 8,
                include: /\.min\.js$/,
                compress: true,
                output: {
                    comments: false,
                    beautify: false
                },
            }
        })
    ]
};
