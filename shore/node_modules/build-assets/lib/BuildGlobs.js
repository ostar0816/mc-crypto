/**
 * buildGlobs
 * @module
 */
'use strict';

var _          = require('lodash');
var obj        = require('object-path');
var minimatch  = require('minimatch');
var Dependency = require('./Dependency');
var types      = require('./types.json');
var path       = require('path');

/**
 * buildGlobs
 *
 * @class
 * @param {Object} dependencies a map of dependencies
 * @param {Object} options
 *
 * @property {Object} globs the glob strings organized by type
 * @property {Object} globs.js an array of javascript Dependency objects
 * @property {Object} globs.css an array of css Dependency objects
 * @property {Object} globs.fonts an array of fonts path glob strings
 * @property {Object} globs.images an array of image path glob strings
 */
var BuildGlobs = module.exports = function(dependencies, options) {
  options = options || {};

  this.globs = {
    // js is an array of objects because there can be multople js files
    js: this.getOutputFiles('js', dependencies),
    // css is an array of objects because there can be multiple css files
    css: this.getOutputFiles('css', dependencies),
    // fonts is a flat array since all the fonts go to the same place
    fonts: [].concat(
      obj.get(dependencies, 'fonts.files')
    ),
    // images is a flat array since all the images go to the same place
    images: [].concat(
      obj.get(dependencies, 'images.files')
    )
  };
};

/**
 * getOutputFiles
 *
 * @param {String} type
 * @param {Object} dependencies
 * @return {undefined}
 */
BuildGlobs.prototype.getOutputFiles = function(type, dependencies) {
  var outputFiles;

  outputFiles = _.pick(dependencies, function(dependency, name) {
    // only select dependencies with valid file extensions
    return new RegExp('\.' + type + '$').test(name);
  });

  outputFiles = _.transform(outputFiles, function(result, dependency, name) {
    // convert to an array of dependencyObjects
    var dep = new Dependency(name, dependency);
    dep.prependGlobs();
    result.push(dep);
  }, [], this);

  return outputFiles;
};

/**
 * filterByPackage
 *
 * @param {Array} files
 * @param {String|Array} names
 * @return {Array} files for a particular package name
 */
BuildGlobs.prototype.filterByPackage = function(files, names, reject) {
  var method = reject ? 'reject' : 'filter';
  if (!_.isArray(names)) {
    names = [names];
  }
  return _[method](files, function(file) {
    return _.some(names, function(name) {
      return file.indexOf(
        path.normalize( name + '/')
      ) > -1;
    });
  });
};

BuildGlobs.prototype.rejectByPackage = function(files, names) {
  return BuildGlobs.prototype.filterByPackage(files, names, true);
};

/**
 * filterByType
 *
 * @param {Array} files
 * @param {String} type
 * @return {Array} files for a particular type
 */
BuildGlobs.prototype.filterByType = function(files, type) {
  return _.filter(files, minimatch.filter(types[type], {matchBase: true}));
};
