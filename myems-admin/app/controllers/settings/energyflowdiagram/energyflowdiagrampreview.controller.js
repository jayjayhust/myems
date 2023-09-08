'use strict';

app.controller('EnergyFlowDiagramPreviewController', function($scope, $window, EnergyFlowDiagramService, EnergyFlowDiagramLinkService) {
      $scope.cur_user = JSON.parse($window.localStorage.getItem("myems_admin_ui_current_user"));
      $scope.energyflowdiagrams = [];
      $scope.currentEnergyFlowDiagram = null;

      $scope.getAllEnergyFlowDiagrams = function() {
        let headers = { "User-UUID": $scope.cur_user.uuid, "Token": $scope.cur_user.token };
        EnergyFlowDiagramService.getAllEnergyFlowDiagrams(headers, function (response) {
          if (angular.isDefined(response.status) && response.status === 200) {
              $scope.energyflowdiagrams = response.data;
            } else {
              $scope.energyflowdiagrams = [];
          }
        });
    };

    $scope.getLinksByEnergyFlowDiagramID = function(id) {
        let headers = { "User-UUID": $scope.cur_user.uuid, "Token": $scope.cur_user.token };
  			EnergyFlowDiagramLinkService.getLinksByEnergyFlowDiagramID(id, headers, function (response) {
  				if (angular.isDefined(response.status) && response.status === 200) {
              return response.data;
  				} else {
            	return [];
          }
  			});
  	};

    $scope.changeEnergyFlowDiagram=function(item,model){
        $scope.currentEnergyFlowDiagram=item;
        $scope.currentEnergyFlowDiagram.selected=model;
        $scope.refreshEnergyFlowChart();
    };

    $scope.refreshEnergyFlowChart = function() {
      var data = {title: {text:null}, accessibility:{point:{valueDescriptionFormat:null}}, series:[{keys:null, data:null, type:null, name:null }]};
      data.title.text = ($scope.currentEnergyFlowDiagram != null) ? $scope.currentEnergyFlowDiagram.name: null;
      data.accessibility.point.valueDescriptionFormat = '{index}. {point.from} to {point.to}, {point.weight}.';
      data.series[0].keys = ['from', 'to', 'weight'];
      data.series[0].type = 'sankey';
      data.series[0].name =  ($scope.currentEnergyFlowDiagram != null) ? $scope.currentEnergyFlowDiagram.name: null;
      data.series[0].data = [];
      var  links = $scope.currentEnergyFlowDiagram.links;
      if (links != null) {
        for (var i=0;i < links.length; i++) {
          data.series[0].data.push([links[i].source_node.name, links[i].target_node.name, Math.floor(Math.random() * 100)]);
        }
      }
      $scope.energyFlowChart = data;
    };
    $scope.getAllEnergyFlowDiagrams();

    $scope.$on('handleBroadcastEnergyFlowDiagramChanged', function(event) {
      $scope.getAllEnergyFlowDiagrams();
      $scope.refreshEnergyFlowChart();
    });

    $scope.$on('handleBroadcastEnergyFlowDiagramLinkChanged', function(event) {
      $scope.getAllEnergyFlowDiagrams();
      $scope.refreshEnergyFlowChart();
    });

});
