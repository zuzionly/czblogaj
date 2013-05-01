'use strict';

/* Filters */

angular.module('czblogFilters', []).filter('checkmark', function() {
  return function(input) {
    return input ? '\u2713' : '\u2718';
  };
});
