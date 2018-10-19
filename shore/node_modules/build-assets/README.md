[build-assets](http://github.com/1mgio/build-assets)
=============

Assembles and orchestrates your dependencies so you can run them through your asset pipeline. Feed it a [manifest file](help/spec.md) and it will give you globs.

[![NPM](https://nodei.co/npm/build-assets.png?downloads=true)](https://nodei.co/npm/build-assets/)

## Install

```bash
npm install build-assets --save-dev
```

## Usage

```javascript
var manifest = require('build-assets')('./assets/manifest.json');
```

## Help

- [Examples, troubleshooting tips](help/)
- [Manifest File Specification](help/spec.md)
