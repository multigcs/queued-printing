! function(t) {
    function e(n) {
        if (r[n]) return r[n].exports;
        var o = r[n] = {
            i: n,
            l: !1,
            exports: {}
        };
        return t[n].call(o.exports, o, o.exports, e), o.l = !0, o.exports
    }
    var r = {};
    return e.m = t, e.c = r, e.i = function(t) {
        return t
    }, e.d = function(t, e, r) {
        Object.defineProperty(t, e, {
            configurable: !1,
            enumerable: !0,
            get: r
        })
    }, e.n = function(t) {
        var r = t && t.__esModule ? function() {
            return t["default"]
        } : function() {
            return t
        };
        return e.d(r, "a", r), r
    }, e.o = function(t, e) {
        return Object.prototype.hasOwnProperty.call(t, e)
    }, e.p = "", e(e.s = 22)
}([function(t, e, r) {
    "use strict";
    e["default"] = {
        props: {
            beginzero: {
                type: Boolean,
                "default": function() {
                    return !1
                }
            },
            max: {
                type: Number,
                "default": function() {
                    return 300
                }
            },
            stepsize: {
                type: Number,
                "default": function() {
                    return 50
                }
            },
            datalabel: {
                type: String,
                "default": function() {
                    return "My dataset"
                }
            },
            labels: {
                type: Array,
                "default": function() {
                    return ["first", "second", "third", "fourth"]
                }
            },
            data: {
                type: Array,
                "default": function() {
                    return [40, 60, 45, 70]
                }
            },
            width: {
                type: Number,
                "default": function() {
                    return null
                }
            },
            height: {
                type: Number,
                "default": function() {
                    return null
                }
            },
            bordercolor: {
                "default": function() {
                    return "rgba(75,192,192,1)"
                }
            },
            backgroundcolor: {
                "default": function() {
                    return "rgba(75,192,192,0.4)"
                }
            },
            scalesdisplay: {
                type: Boolean,
                "default": function() {
                    return !0
                }
            },
            target: {
                type: String,
                "default": function() {
                    return null
                }
            },
            datasets: {
                type: Array,
                "default": function() {
                    return null
                }
            },
            option: {
                type: Object,
                "default": function() {
                    return null
                }
            },
            bind: {
                type: Boolean,
                "default": function() {
                    return !1
                }
            }
        },
        data: function() {
            return {
                isDatasetsOverride: !1,
                isOptionOverride: !1,
                type: null,
                canvas: null,
                context: null,
                chart: null,
                chart_data: {
                    labels: this.labels,
                    datasets: this.datasets
                },
                options: {
                    legend: {
                       display: false
                    },
                    animation: false,
                    responsive: !1,
                    maintainAspectRatio: !1,
                    scales: {
                        yAxes: [{
                            display: this.scalesdisplay,
                            ticks: {
                                min: 0,
                                max: this.max,
                                stepSize: this.stepsize,
                                beginAtZero: this.beginzero
                            }
                        }]
                    }
                }
            }
        },
        watch: {
            data: {
                handler: function(t, e) {
                    !this.isDatasetsOverride && this.bind && (this.chart_data.datasets[0].data = this.data, this.renderChart())
                },
                deep: !0
            },
            labels: {
                handler: function(t, e) {
                    this.bind && (this.chart_data.labels = t, this.renderChart())
                },
                deep: !0
            },
            datasets: {
                handler: function(t, e) {
                    var r = this;
                    this.isDatasetsOverride && this.bind && (this.cleanChart(), this.sleep(5).then(function() {
                        r.renderChart()
                    }))
                },
                deep: !0
            }
        },
        methods: {
            sleep: function(t) {
                return new Promise(function(e) {
                    return setTimeout(e, t)
                })
            },
            setDatasets: function() {
                this.chart_data.datasets = this.datasets
            },
            setOption: function() {
                this.options = this.option
            },
            initTargetCanvas: function() {
                null == this.target ? (this.canvas = this.$refs.canvas, this.context = this.$refs.canvas.getContext("2d"), this.renderChart()) : (this.canvas = document.getElementById(this.target), this.context = document.getElementById(this.target).getContext("2d"), "undefined" == typeof datasets && (window.datasets = []), "undefined" == typeof datasets[this.target] && (window.datasets[this.target] = []), this.appendChart())
            },
            cleanChart: function() {
                null != this.chart && this.chart.destroy()
            },
            checkOverride: function() {
                null != this.datasets && (this.setDatasets(), this.isDatasetsOverride = !0), null != this.option && (this.setOption(), this.isOptionOverride = !0)
            },
            renderChart: function() {
                this.cleanChart(), this.chart = new Chart(this.context, {
                    type: this.type,
                    data: this.chart_data,
                    options: this.options
                })
            },
            appendChart: function() {
                window.datasets[this.target].push(this.chart_data.datasets[0]), this.chart_data.datasets = window.datasets[this.target], document.getElementById(this.target).getAttribute("count") == this.chart_data.datasets.length && this.renderChart()
            },
            checkSize: function() {
                null != this.width && null != this.height || this.isOptionOverride || (this.options.responsive = !0, this.options.maintainAspectRatio = !0)
            }
        },
        mounted: function() {
            this.checkOverride(), this.checkSize(), this.initTargetCanvas()
        },
        beforeDestroy: function() {
            this.cleanChart()
        }
    }
}, function(t, e, r) {
    var n, o;
    n = r(8);
    var a = r(15);
    o = n = n || {}, "object" != typeof n["default"] && "function" != typeof n["default"] || (o = n = n["default"]), "function" == typeof o && (o = o.options), o.render = a.render, o.staticRenderFns = a.staticRenderFns, t.exports = n
}, function(t, e, r) {
    var n, o;
    n = r(9);
    var a = r(18);
    o = n = n || {}, "object" != typeof n["default"] && "function" != typeof n["default"] || (o = n = n["default"]), "function" == typeof o && (o = o.options), o.render = a.render, o.staticRenderFns = a.staticRenderFns, t.exports = n
}, function(t, e, r) {
    var n, o;
    n = r(10);
    var a = r(21);
    o = n = n || {}, "object" != typeof n["default"] && "function" != typeof n["default"] || (o = n = n["default"]), "function" == typeof o && (o = o.options), o.render = a.render, o.staticRenderFns = a.staticRenderFns, t.exports = n
}, function(t, e, r) {
    var n, o;
    n = r(11);
    var a = r(20);
    o = n = n || {}, "object" != typeof n["default"] && "function" != typeof n["default"] || (o = n = n["default"]), "function" == typeof o && (o = o.options), o.render = a.render, o.staticRenderFns = a.staticRenderFns, t.exports = n
}, function(t, e, r) {
    var n, o;
    n = r(12);
    var a = r(16);
    o = n = n || {}, "object" != typeof n["default"] && "function" != typeof n["default"] || (o = n = n["default"]), "function" == typeof o && (o = o.options), o.render = a.render, o.staticRenderFns = a.staticRenderFns, t.exports = n
}, function(t, e, r) {
    var n, o;
    n = r(13);
    var a = r(19);
    o = n = n || {}, "object" != typeof n["default"] && "function" != typeof n["default"] || (o = n = n["default"]), "function" == typeof o && (o = o.options), o.render = a.render, o.staticRenderFns = a.staticRenderFns, t.exports = n
}, function(t, e, r) {
    var n, o;
    n = r(14);
    var a = r(17);
    o = n = n || {}, "object" != typeof n["default"] && "function" != typeof n["default"] || (o = n = n["default"]), "function" == typeof o && (o = o.options), o.render = a.render, o.staticRenderFns = a.staticRenderFns, t.exports = n
}, function(t, e, r) {
    "use strict";
    e["default"] = {
        mixins: [VueCharts.core["default"]],
        data: function() {
            return {
                type: "bar",
                chart_data: {
                    labels: this.labels,
                    datasets: [{
                        type: "bar",
                        label: this.datalabel,
                        backgroundColor: this.backgroundcolor,
                        borderColor: this.bordercolor,
                        borderWidth: 1,
                        data: this.data
                    }]
                }
            }
        }
    }
}, function(t, e, r) {
    "use strict";
    e["default"] = {
        mixins: [VueCharts.core["default"]],
        props: {
            backgroundcolor: {
                "default": function() {
                    return ["#FF6384", "#36A2EB", "#FFCE56", "#00A600"]
                }
            },
            hoverbackgroundcolor: {
                "default": function() {
                    return ["#FF6384", "#36A2EB", "#FFCE56", "#00A600"]
                }
            },
            bordercolor: {
                "default": function() {
                    return "#fff"
                }
            },
            hoverbordercolor: {
                "default": function() {
                    return ""
                }
            }
        },
        data: function() {
            return {
                type: "doughnut",
                chart_data: {
                    labels: this.labels,
                    datasets: [{
                        label: this.datalabel,
                        backgroundColor: this.backgroundcolor,
                        borderColor: this.bordercolor,
                        hoverBackgroundColor: this.hoverbackgroundcolor,
                        hoverBorderColor: this.hoverbackgroundcolor,
                        data: this.data
                    }]
                },
                options: {
                    scale: {
                        reverse: !0,
                        ticks: {
                            beginAtZero: this.beginzero
                        }
                    }
                }
            }
        }
    }
}, function(t, e, r) {
    "use strict";
    e["default"] = {
        mixins: [VueCharts.core["default"]],
        data: function() {
            return {
                type: "horizontalBar",
                chart_data: {
                    labels: this.labels,
                    datasets: [{
                        type: "horizontalBar",
                        label: this.datalabel,
                        backgroundColor: this.backgroundcolor,
                        borderColor: this.bordercolor,
                        borderWidth: 1,
                        data: this.data
                    }]
                },
                options: {
                    scales: {
                        yAxes: [{
                            stacked: !1
                        }],
                        xAxes: [{
                            stacked: !0
                        }]
                    }
                }
            }
        }
    }
}, function(t, e, r) {
    "use strict";
    e["default"] = {
        mixins: [VueCharts.core["default"]],
        props: {
            beginzero: {
                type: Boolean,
                "default": !1
            },
            fill: {
                type: Boolean,
                "default": !1
            },
            linetension: {
                type: Number,
                "default": function() {
                    return .2
                }
            },
            pointbordercolor: {
                type: String,
                "default": function() {
                    return "rgba(75,192,192,1)"
                }
            },
            pointbackgroundcolor: {
                type: String,
                "default": function() {
                    return "#fff"
                }
            },
            pointhoverbackgroundcolor: {
                type: String,
                "default": function() {
                    return "rgba(75,192,192,1)"
                }
            },
            pointhoverbordercolor: {
                type: String,
                "default": function() {
                    return "rgba(220,220,220,1)"
                }
            },
            pointborderwidth: {
                type: Number,
                "default": function() {
                    return 1
                }
            },
            pointhoverborderwidth: {
                type: Number,
                "default": function() {
                    return 2
                }
            }
        },
        data: function() {
            return {
                type: "line",
                chart_data: {
                    labels: this.labels,
                    datasets: [{
                        type: "line",
                        label: this.datalabel,
                        fill: this.fill,
                        lineTension: this.linetension,
                        backgroundColor: this.backgroundcolor,
                        borderColor: this.bordercolor,
                        borderCapStyle: "butt",
                        borderDash: [],
                        borderDashOffset: 0,
                        borderJoinStyle: "miter",
                        pointBorderColor: this.pointbordercolor,
                        pointBackgroundColor: this.pointbackgroundcolor,
                        pointBorderWidth: this.pointborderwidth,
                        pointHoverRadius: 5,
                        pointHoverBackgroundColor: this.pointhoverbackgroundcolor,
                        pointHoverBorderColor: this.pointhoverbordercolor,
                        pointHoverBorderWidth: this.pointhoverborderwidth,
                        pointRadius: 1,
                        pointHitRadius: 10,
                        data: this.data,
                        spanGaps: !1
                    }]
                }
            }
        }
    }
}, function(t, e, r) {
    "use strict";
    e["default"] = {
        mixins: [VueCharts.core["default"]],
        props: {
            backgroundcolor: {
                "default": function() {
                    return ["#FF6384", "#36A2EB", "#FFCE56", "#00A600"]
                }
            },
            hoverbackgroundcolor: {
                "default": function() {
                    return ["#FF6384", "#36A2EB", "#FFCE56", "#00A600"]
                }
            },
            bordercolor: {
                "default": function() {
                    return "#fff"
                }
            },
            hoverbordercolor: {
                "default": function() {
                    return ""
                }
            }
        },
        data: function() {
            return {
                type: "pie",
                chart_data: {
                    labels: this.labels,
                    datasets: [{
                        label: this.datalabel,
                        backgroundColor: this.backgroundcolor,
                        borderColor: this.bordercolor,
                        hoverBackgroundColor: this.hoverbackgroundcolor,
                        hoverBorderColor: this.hoverbackgroundcolor,
                        data: this.data
                    }]
                },
                options: {
                    scale: {
                        reverse: !0,
                        ticks: {
                            beginAtZero: this.beginzero,
                        }
                    }
                }
            }
        }
    }
}, function(t, e, r) {
    "use strict";
    e["default"] = {
        mixins: [VueCharts.core["default"]],
        props: {
            hoverbackgroundcolor: {
                "default": function() {
                    return "rgba(75,192,192,0.6)"
                }
            },
            hoverbordercolor: {
                "default": function() {
                    return "rgba(179,181,198,1)"
                }
            }
        },
        data: function() {
            return {
                type: "polarArea",
                chart_data: {
                    labels: this.labels,
                    datasets: [{
                        label: this.datalabel,
                        backgroundColor: this.backgroundcolor,
                        borderColor: this.bordercolor,
                        hoverBackgroundColor: this.hoverbackgroundcolor,
                        hoverBorderColor: this.hoverbackgroundcolor,
                        data: this.data
                    }]
                }
            }
        }
    }
}, function(t, e, r) {
    "use strict";
    e["default"] = {
        mixins: [VueCharts.core["default"]],
        props: {
            pointbordercolor: {
                "default": function() {
                    return "#fff"
                }
            },
            pointbackgroundcolor: {
                "default": function() {
                    return "rgba(179,181,198,1)"
                }
            }
        },
        data: function() {
            return {
                type: "radar",
                chart_data: {
                    labels: this.labels,
                    datasets: [{
                        label: this.datalabel,
                        backgroundColor: this.backgroundcolor,
                        borderColor: this.bordercolor,
                        pointBackgroundColor: this.pointbackgroundcolor,
                        pointBorderColor: this.pointbordercolor,
                        pointHoverBackgroundColor: "#fff",
                        pointHoverBorderColor: "rgba(179,181,198,1)",
                        data: this.data
                    }]
                },
                options: {
                    scale: {
                        reverse: !1,
                        ticks: {
                            beginAtZero: this.beginzero
                        }
                    }
                }
            }
        }
    }
}, function(t, e) {
    t.exports = {
        render: function() {
            var t = this,
                e = t.$createElement,
                r = t._self._c || e;
            return r("div", [t.target ? t._e() : r("canvas", {
                ref: "canvas",
                attrs: {
                    width: t.width,
                    height: t.height
                }
            })])
        },
        staticRenderFns: []
    }
}, function(t, e) {
    t.exports = {
        render: function() {
            var t = this,
                e = t.$createElement,
                r = t._self._c || e;
            return r("div", [t.target ? t._e() : r("canvas", {
                ref: "canvas",
                attrs: {
                    width: t.width,
                    height: t.height
                }
            })])
        },
        staticRenderFns: []
    }
}, function(t, e) {
    t.exports = {
        render: function() {
            var t = this,
                e = t.$createElement,
                r = t._self._c || e;
            return r("div", [t.target ? t._e() : r("canvas", {
                ref: "canvas",
                attrs: {
                    width: t.width,
                    height: t.height
                }
            })])
        },
        staticRenderFns: []
    }
}, function(t, e) {
    t.exports = {
        render: function() {
            var t = this,
                e = t.$createElement,
                r = t._self._c || e;
            return r("div", [t.target ? t._e() : r("canvas", {
                ref: "canvas",
                attrs: {
                    width: t.width,
                    height: t.height
                }
            })])
        },
        staticRenderFns: []
    }
}, function(t, e) {
    t.exports = {
        render: function() {
            var t = this,
                e = t.$createElement,
                r = t._self._c || e;
            return r("div", [t.target ? t._e() : r("canvas", {
                ref: "canvas",
                attrs: {
                    width: t.width,
                    height: t.height
                }
            })])
        },
        staticRenderFns: []
    }
}, function(t, e) {
    t.exports = {
        render: function() {
            var t = this,
                e = t.$createElement,
                r = t._self._c || e;
            return r("div", [t.target ? t._e() : r("canvas", {
                ref: "canvas",
                attrs: {
                    width: t.width,
                    height: t.height
                }
            })])
        },
        staticRenderFns: []
    }
}, function(t, e) {
    t.exports = {
        render: function() {
            var t = this,
                e = t.$createElement,
                r = t._self._c || e;
            return r("div", [t.target ? t._e() : r("canvas", {
                ref: "canvas",
                attrs: {
                    width: t.width,
                    height: t.height
                }
            })])
        },
        staticRenderFns: []
    }
}, function(t, e, r) {
    if ("undefined" == typeof Chart) throw "ChartJS is undefined";
    window.VueCharts = {}, VueCharts.core = r(0), VueCharts.install = function(t) {
        t.component("chartjs-line", r(4)), t.component("chartjs-bar", r(1)), t.component("chartjs-horizontal-bar", r(3)), t.component("chartjs-radar", r(7)), t.component("chartjs-polar-area", r(6)), t.component("chartjs-pie", r(5)), t.component("chartjs-doughnut", r(2))
    }
}]);
