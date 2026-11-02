'use strict';

// The watering math (src/irrigation.js) and the public API client (src/api.js).
module.exports = {
  ...require('./src/irrigation'),
  ...require('./src/api'),
};
