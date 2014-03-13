// Line graph for a single parameter over time
        (function() {
            var csvfile = '/data/int_RH.csv';
            var time_format = "%Y-%m-%d-%H-%M-%S"; // CSV is only to minutes
            var yLabel = " Internal Humidity (%)"
            var xParameter = "date";
            var yParameter = "val";
            
            var margin = {top: 10, right: 40, bottom: 50, left: 40},
                width = $(window).width() - margin.left - margin.right,
                height = $(window).height() - margin.top - margin.bottom;
            var parseDate = d3.time.format(time_format).parse; 
            
            var x = d3.time.scale()
                .range([0, width]);
            
            var y = d3.scale.linear()
                .range([height, 0]);
            
            var color = d3.scale.category10();
            
            var xAxis = d3.svg.axis()
                .scale(x)
                .orient("bottom");
            
            var yAxis = d3.svg.axis()
                .scale(y)
                .orient("left");
            
            var line = d3.svg.line()
                .interpolate("basis")
                .x(function(d) { return x(d[xParameter]); })
                .y(function(d) { return y(d[yParameter]); });
            
            // add the graph canvas to the body of the webpage
            var svg = d3.select("center").append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .append("g")
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
            
            // Load data
            d3.csv(csvfile, function(error, data) {
                color.domain(d3.keys(data[0]).filter(function(key) { return key !== "date"; }));
                data.forEach(function(d) {
                    d.date = parseDate(d.date);
                });
                var hives = color.domain().map(function(name) {
                    return {
                        name: name,
                        values: data.map(function(d) {
                            return {date: d.date, val: +d[name]};
                        })
                    };
                });
                x.domain(d3.extent(data, function(d) { return d.date; }));
                y.domain([
                    d3.min(hives, function(c) { return d3.min(c.values, function(v) { return v.val; }); }),
                    d3.max(hives, function(c) { return d3.max(c.values, function(v) { return v.val; }); })
                ]);
                svg.append("g")
                    .attr("class", "x axis")
                    .attr("transform", "translate(0," + height + ")")
                    .call(xAxis);
                svg.append("g")
                    .attr("class", "y axis")
                    .call(yAxis)
                    .append("text")
                    .attr("transform", "rotate(-90)")
                    .attr("y", 6)
                    .attr("dy", ".71em")
                    .style("text-anchor", "end")
                    .text(yLabel);
                var hive = svg.selectAll(".hive")
                    .data(hives)
                    .enter().append("g")
                    .attr("class", "hive");
                hive.append("path")
                    .attr("class", "line")
                    .attr("d", function(d) { return line(d.values); })
                    .style("stroke", function(d) { return color(d.name); });
                });
            })();
