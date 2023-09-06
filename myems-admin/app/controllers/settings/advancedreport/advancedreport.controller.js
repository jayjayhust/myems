'use strict';

app.controller('AdvancedReportController', function(
    $scope,
    $rootScope,
    $window,
    $uibModal,
    $translate,
    AdvancedReportService,
    toaster,
    SweetAlert) {
    $scope.cur_user = JSON.parse($window.localStorage.getItem("myems_admin_ui_current_user"));

	$scope.initExpression = {};

	$scope.getAllAdvancedReport = function() {
        let headers = { "User-UUID": $scope.cur_user.uuid, "Token": $scope.cur_user.token };
		AdvancedReportService.getAllAdvancedReport(headers, function (response) {
			if (angular.isDefined(response.status) && response.status === 200) {
				$scope.advancedReports = response.data;
			} else {
				$scope.advancedReports = [];
			}
		});

	};

	$scope.addAdvancedReport = function() {

		var modalInstance = $uibModal.open({
			templateUrl: 'views/settings/advancedreport/advancedreport.model.html',
			controller: 'ModalAddAdvancedReportCtrl',
			windowClass: "animated fadeIn",
			size: 'xl',
			resolve: {
				params: function() {
					return {
						advancedReport: angular.copy($scope.advancedReport),
						expression:angular.copy($scope.initExpression),
					};
				}
			}
		});
		modalInstance.result.then(function(advancedReport) {
		    let headers = { "User-UUID": $scope.cur_user.uuid, "Token": $scope.cur_user.token };
			AdvancedReportService.addAdvancedReport(advancedReport, headers, function (response) {
				if (angular.isDefined(response.status) && response.status === 201) {
					toaster.pop({
						type: "success",
						title: $translate.instant("TOASTER.SUCCESS_TITLE"),
						body: $translate.instant("TOASTER.SUCCESS_ADD_BODY", {template: $translate.instant("MENU.SETTINGS.ADVANCED_REPORT")}),
						showCloseButton: true,
					});
					$scope.getAllAdvancedReport();
				} else {
					toaster.pop({
						type: "error",
						title: $translate.instant("TOASTER.ERROR_ADD_BODY",{template: $translate.instant("MENU.SETTINGS.ADVANCED_REPORT")}),
						body: $translate.instant(response.data.description),
						showCloseButton: true,
					});
				}
			});
		}, function() {

		});
		$rootScope.modalInstance = modalInstance;
	};

	$scope.editAdvancedReport = function(advancedReport) {
		var modalInstance = $uibModal.open({
			windowClass: "animated fadeIn",
			templateUrl: 'views/settings/advancedreport/advancedreport.model.html',
			controller: 'ModalEditAdvancedReportCtrl',
			size: 'xl',
			resolve: {
				params: function() {
					return {
						advancedReport: angular.copy(advancedReport)
					};
				}
			}
		});

		modalInstance.result.then(function(modifiedAdvancedReport) {
		    let headers = { "User-UUID": $scope.cur_user.uuid, "Token": $scope.cur_user.token };
			AdvancedReportService.editAdvancedReport(modifiedAdvancedReport, headers, function (response) {
				if (angular.isDefined(response.status) && response.status === 200) {
					toaster.pop({
						type: "success",
						title: $translate.instant("TOASTER.SUCCESS_TITLE"),
						body: $translate.instant("TOASTER.SUCCESS_UPDATE_BODY",{template: $translate.instant("MENU.SETTINGS.ADVANCED_REPORT")}),
						showCloseButton: true,
					});
					$scope.getAllAdvancedReport();
				} else {
					toaster.pop({
						type: "error",
						title: $translate.instant("TOASTER.ERROR_UPDATE_BODY", {template: $translate.instant("MENU.SETTINGS.ADVANCED_REPORT")}),
						body: $translate.instant(response.data.description),
						showCloseButton: true,
					});

				}
			});
		}, function() {
			//do nothing;
		});
		$rootScope.modalInstance = modalInstance;
	};

	$scope.deleteAdvancedReport = function(advancedReport) {
		SweetAlert.swal({
				title: $translate.instant("SWEET.TITLE"),
				text: $translate.instant("SWEET.TEXT"),
				type: "warning",
				showCancelButton: true,
				confirmButtonColor: "#DD6B55",
				confirmButtonText: $translate.instant("SWEET.CONFIRM_BUTTON_TEXT"),
				cancelButtonText: $translate.instant("SWEET.CANCEL_BUTTON_TEXT"),
				closeOnConfirm: true,
				closeOnCancel: true
			},
			function(isConfirm) {
                if (isConfirm) {
                    let headers = { "User-UUID": $scope.cur_user.uuid, "Token": $scope.cur_user.token };
                    AdvancedReportService.deleteAdvancedReport(advancedReport, headers, function (response) {
                        if (angular.isDefined(response.status) && response.status === 204) {
                            toaster.pop({
                                type: "success",
                                title: $translate.instant("TOASTER.SUCCESS_TITLE"),
                                body: $translate.instant("TOASTER.SUCCESS_DELETE_BODY", { template: $translate.instant("MENU.SETTINGS.ADVANCED_REPORT") }),
                                showCloseButton: true,
                            });
                            $scope.getAllAdvancedReport();
                        } else {
                            toaster.pop({
                                type: "error",
                                title: $translate.instant("TOASTER.ERROR_DELETE_BODY", {template: $translate.instant("MENU.SETTINGS.ADVANCED_REPORT")}),
                                body: $translate.instant(response.data.description),
                                showCloseButton: true,
                            });
						}
					});
				}
			});
	};

	$scope.getAllAdvancedReport();

});

app.controller('ModalAddAdvancedReportCtrl', function($scope, $uibModalInstance, params) {

	$scope.operation = "ADVANCED_REPORT.ADD_ADVANCED_REPORT";
	$scope.advancedReport={};
	$scope.advancedReport.is_enabled=true;
	$scope.advancedReport.expression=JSON.stringify(params.expression);
	debugger
	$scope.advancedReport.next_run_datetime = moment().add(10, 'm');
	$scope.dtOptions = {
		locale:{
			format: 'YYYY-MM-DD HH:mm:ss',
			applyLabel: "OK",
			cancelLabel: "Cancel",
		},
		timePicker: true,
		timePicker24Hour: true,
		timePickerSeconds: true,
		timePickerIncrement: 1,
		singleDatePicker: true,
	};

	$scope.ok = function() {
		$scope.advancedReport.next_run_datetime=moment($scope.advancedReport.next_run_datetime).format().slice(0,19);
		$uibModalInstance.close($scope.advancedReport);
	};

	$scope.cancel = function() {
		$uibModalInstance.dismiss('cancel');
	};
});

app.controller('ModalEditAdvancedReportCtrl', function($scope, $uibModalInstance, params) {
	$scope.operation = "ADVANCED_REPORT.EDIT_ADVANCED_REPORT";
	$scope.advancedReport = params.advancedReport;
	$scope.advancedReport.is_enabled = params.advancedReport.is_enabled;
	$scope.dtOptions = {
		locale:{
			format: 'YYYY-MM-DD HH:mm:ss',
			applyLabel: "OK",
			cancelLabel: "Cancel",
		},
		timePicker: true,
		timePicker24Hour: true,
		timePickerSeconds: true,
		timePickerIncrement: 1,
		singleDatePicker: true,
	};

	$scope.ok = function() {
		$scope.advancedReport.next_run_datetime=moment($scope.advancedReport.next_run_datetime).format().slice(0,19);
		$uibModalInstance.close($scope.advancedReport);
	};

	$scope.cancel = function() {
		$uibModalInstance.dismiss('cancel');
	};
});