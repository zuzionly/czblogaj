'use strict';

/* Controllers */

function CustomConfigCtrl($scope, $http) {
  $http.get('../static/config/custom_config.json').success(function(data) {
    $scope.custom_config = data;
  });
}