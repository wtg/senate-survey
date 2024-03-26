angular.module('questionaire', [])
.controller('QuestionController', ['$scope', '$http', '$interpolate', function($scope, $http, $interpolate) {
    // These need to match IDs in survey.json to show a header before a question.
    $scope.headers = {
        "demographics1": "Demographics",
        "ssr1":"Student Support Services",
        "shw1":"Student Health and Wellbeing",
        "fsc1":"Facilities and Dining",
        "general1":"General",
        "grk1":"Greek Life"
    };

    $scope.survey = survey;

    $scope.canProceed = function () {
        for (var q of $scope.survey[$scope.page - 1]) {
            if((q.value == undefined || q.value.length == 0)
                && $scope.should_show_question(q)
                && q.required) {
                return false;
            }
        }
        return true;
    }

    $scope.should_show_question = function(q) {
        if (!('show_if_id' in q)) return true;
        if ('show_if_value' in q) {
            for (var page of $scope.survey) {
                for (var other_q of page) {
                    if (other_q.id === q.show_if_id) {
                        if (other_q.value === q.show_if_value) {
                            // make sure that the question we depend on is also visible
                            return $scope.should_show_question(other_q);
                        } else if (other_q.value instanceof Array
                                    && other_q.value.indexOf(q.show_if_value) != -1) {
                                    // if value is an array (for checkboxes)
                                    // make sure that the question we depend on is also visible
                                    return $scope.should_show_question(other_q);
                                } else {
                                    return false;
                                }
                            }
                        }
                    }
                    return true;
                } else if ('show_if_value_not' in q) {
                    for (var page of $scope.survey) {
                        for (var other_q of page) {

                            if (other_q.id === q.show_if_id) {
                                if (other_q.value == null) {
                                    // other question hasn't been answered yet
                                    return false;
                                } else if ((!(other_q.value instanceof Array) && other_q.value !== q.show_if_value_not) ||
                                    (other_q.value instanceof Array
                                        && other_q.value.indexOf(q.show_if_value_not) == -1)) {
                                    // make sure that the question we depend on is also visible
                                    return $scope.should_show_question(other_q);
                                } else {
                                    return false;
                                }
                            }
                        }
                    }
                    return true;
                }

                return true;
            };

            $scope.toggleCheckboxSelection = function (qIndex, option) {
                if ($scope.survey[$scope.page - 1][qIndex].type != 'checkbox') {
                    return;
                } else if (!$scope.survey[$scope.page - 1][qIndex].value) {
                    $scope.survey[$scope.page - 1][qIndex].value = [];
                }

                var idx = $scope.survey[$scope.page - 1][qIndex].value.indexOf(option);

                if (idx > -1) {
                    $scope.survey[$scope.page - 1][qIndex].value.splice(idx, 1);
                } else {
                    $scope.survey[$scope.page - 1][qIndex].value.push(option);
                }
            };

            // pagination
            $scope.page = 1;
            $scope.last_page = $scope.survey.length;
            $scope.next_page = function () {
                if ($scope.page != $scope.last_page && $scope.canProceed())
                    $scope.page++;
            };
            $scope.previous_page = function () {
                if ($scope.page != 1) $scope.page--;
            };
        }]);