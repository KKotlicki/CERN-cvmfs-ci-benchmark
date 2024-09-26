document.addEventListener("DOMContentLoaded", () => {
	// Fetch configurations and populate dropdowns
	fetch("/api/configurations")
		.then((response) => response.json())
		.then((configurationData) => {
			// Use names as values in the dropdowns
			const clientConfigSelect = document.getElementById(
				"client-config-select",
			);
			for (const config of configurationData.client_configs) {
				const option = document.createElement("option");
				option.value = config.config_name;
				option.text = config.config_name;
				clientConfigSelect.add(option);
			}

			// Populate commands
			const commandSelect = document.getElementById("command-select");
			for (const cmd of configurationData.commands) {
				const option = document.createElement("option");
				option.value = cmd.command_name;
				option.text = cmd.command_name;
				commandSelect.add(option);
			}

			// Populate metrics
			const metricSelect = document.getElementById("metric-select");
			for (const metric of configurationData.metrics) {
				const option = document.createElement("option");
				option.value = metric.metric_name;
				option.text = metric.metric_name;
				metricSelect.add(option);
			}

			// Store configuration data for later use
			window.configurationData = configurationData;

			// Create overview plots
			createOverviewPlots(configurationData);
		})
		.catch((error) => console.error("Error fetching configurations:", error));

	// Handle Add Plot button click
	document.getElementById("add-plot-btn").addEventListener("click", () => {
		const plotType = document.getElementById("plot-type").value;
		const numCommits = document.getElementById("num-commits-select").value;
		const clientConfigName = document.getElementById(
			"client-config-select",
		).value;
		const commandName = document.getElementById("command-select").value;
		const metricName = document.getElementById("metric-select").value;

		// Create a unique plot container
		const plotContainer = document.createElement("div");
		plotContainer.classList.add("plot-box");

		// Create a remove button
		const removeButton = document.createElement("button");
		removeButton.classList.add("remove-plot-btn");
		removeButton.innerHTML = "&times;";
		removeButton.addEventListener("click", () => {
			plotContainer.remove();
		});

		plotContainer.appendChild(removeButton);

		// Add plot title
		const plotTitle = document.createElement("div");
		plotTitle.classList.add("plot-title");
		plotTitle.textContent = `${
			plotType.charAt(0).toUpperCase() + plotType.slice(1)
		} Plot - ${commandName}`;
		plotContainer.appendChild(plotTitle);

		// Create plot div
		const plotDiv = document.createElement("div");
		plotDiv.classList.add("benchmark-plot-box");
		plotContainer.appendChild(plotDiv);

		// Append to plots container
		document.getElementById("plots-container").appendChild(plotContainer);

		// Create the plot
		if (plotType === "line") {
			createLinePlotCustom(
				plotDiv,
				clientConfigName,
				commandName,
				metricName,
				numCommits,
				window.configurationData,
			);
		} else if (plotType === "box") {
			createBoxPlotCustom(
				plotDiv,
				clientConfigName,
				commandName,
				metricName,
				numCommits,
				window.configurationData,
			);
		}
	});

	fetch("/api/commits_list")
		.then((response) => response.json())
		.then((commitsData) => {
			const commitSelect = document.getElementById("commit-select");
			for (const commit of commitsData) {
				const option = document.createElement("option");
				option.value = commit.commit;
				const formattedDate = formatDateTime(commit.commit_datetime);
				option.text = `${commit.commit.slice(0, 7)} - ${formattedDate}`;
				commitSelect.add(option);
			}

			// Load results for the first commit by default
			if (commitsData.length > 0) {
				displayCommitResults(commitsData[0].commit);
			}
		})
		.catch((error) => console.error("Error fetching commits list:", error));

	// Handle commit selection change
	document
		.getElementById("commit-select")
		.addEventListener("change", (event) => {
			const selectedCommit = event.target.value;
			displayCommitResults(selectedCommit);
		});

	// Handle CSV download button click
	document.getElementById("download-csv-btn").addEventListener("click", () => {
		const selectedCommit = document.getElementById("commit-select").value;
		downloadCSV(selectedCommit);
	});
});

function createLinePlotCustom(
	plotElement,
	clientConfigName,
	commandName,
	metricName,
	numCommits,
	configurationData,
) {
	// Fetch benchmark results
	fetch(
		`/api/commits_data_by_names?client_config_name=${encodeURIComponent(
			clientConfigName,
		)}&command_name=${encodeURIComponent(
			commandName,
		)}&metric_name=${encodeURIComponent(metricName)}&num_commits=${numCommits}`,
	)
		.then((response) => response.json())
		.then((data) => {
			if (data.error) {
				console.error("Error fetching data:", data.error);
				plotElement.innerHTML = "<p>Error fetching data.</p>";
				return;
			}

			if (data.length === 0) {
				plotElement.innerHTML = "<p>No data available for this selection.</p>";
				return;
			}

			// Prepare the data for the plot
			const traces = [];
			const x_ticks = data.map((entry) => entry.commit.slice(0, 7)).reverse(); // Shortened commit SHA
			const customData = data
				.map((entry) => [entry.commit, formatDateTime(entry.commit_datetime)])
				.reverse();

			const colors = ["#1f77b4", "#ff7f0e", "#d62728"];
			const cache_types = ["cold_cache", "warm_cache", "hot_cache"];
			const cache_labels = ["Cold Cache", "Warm Cache", "Hot Cache"];

			// For each cache type, create a trace with medians
			cache_types.forEach((type, i) => {
				const y_values = data.map((entry) => entry[`${type}_median`]).reverse();

				traces.push({
					x: x_ticks,
					y: y_values,
					name: cache_labels[i],
					mode: "lines+markers",
					line: { color: colors[i] },
					hovertemplate:
						"<b>%{y}</b><br>Commit: %{customdata[0]}<br>Date: %{customdata[1]}<extra></extra>",
					customdata: customData, // Add commit SHA and formatted date to hover data
				});
			});

			const yAxisTitles = {
				user: "User Time (s)",
				system: "System Time (s)",
				real: "Real Time (s)",
				"catalog_mgr.n_lookup_path": "Catalog Mgr: #Path lookups",
			};

			const layout = {
				yaxis: {
					title: yAxisTitles[metricName] || metricName,
				},
				xaxis: {
					title: "Commits",
					tickvals: x_ticks,
					ticktext: x_ticks,
				},
				showlegend: true,
				height: 600,
				hovermode: "closest",
			};

			Plotly.newPlot(plotElement, traces, layout, {
				responsive: true,
				modeBarButtonsToRemove: [
					"select2d",
					"lasso2d",
					"zoomIn2d",
					"zoomOut2d",
					"autoScale2d",
				],
			});

			// Add event listener to copy the commit SHA on click
			plotElement.on("plotly_click", (eventData) => {
				const commitSHA = eventData.points[0].customdata[0];
				const tempInput = document.createElement("textarea");
				tempInput.value = commitSHA;
				document.body.appendChild(tempInput);
				tempInput.select();
				document.execCommand("copy");
				document.body.removeChild(tempInput);
				alert(`Commit ${commitSHA} copied to clipboard!`);
			});
		})
		.catch((error) => {
			console.error("Error creating plot:", error);
			plotElement.innerHTML = "<p>Error creating plot.</p>";
		});
}

function createBoxPlotCustom(
	plotElement,
	clientConfigName,
	commandName,
	metricName,
	numCommits,
	configurationData,
) {
	// Fetch benchmark results
	fetch(
		`/api/commits_data_by_names?client_config_name=${encodeURIComponent(
			clientConfigName,
		)}&command_name=${encodeURIComponent(
			commandName,
		)}&metric_name=${encodeURIComponent(metricName)}&num_commits=${numCommits}`,
	)
		.then((response) => response.json())
		.then((data) => {
			if (data.error) {
				console.error("Error fetching data:", data.error);
				plotElement.innerHTML = "<p>Error fetching data.</p>";
				return;
			}

			if (data.length === 0) {
				plotElement.innerHTML = "<p>No data available for this selection.</p>";
				return;
			}

			// Prepare the data for the plot
			const traces = [];
			const x_ticks = data.map((entry) => entry.commit.slice(0, 7)).reverse(); // Shortened commit SHA
			const colors = ["#1f77b4", "#ff7f0e", "#d62728"];
			const cache_types = ["cold_cache", "warm_cache", "hot_cache"];
			const cache_labels = ["Cold Cache", "Warm Cache", "Hot Cache"];

			// For each cache type, create a trace
			cache_types.forEach((type, i) => {
				const y_values = [];
				const x_values = [];

				data
					.slice()
					.reverse()
					.forEach((entry, index) => {
						y_values.push(
							entry[`${type}_min_val`],
							entry[`${type}_first_quartile`],
							entry[`${type}_median`],
							entry[`${type}_third_quartile`],
							entry[`${type}_max_val`],
						);

						x_values.push(
							x_ticks[index],
							x_ticks[index],
							x_ticks[index],
							x_ticks[index],
							x_ticks[index],
						);
					});

				traces.push({
					x: x_values,
					y: y_values,
					name: cache_labels[i],
					marker: { color: colors[i] },
					type: "box",
					hoverinfo: "y",
				});
			});

			const yAxisTitles = {
				user: "User Time (s)",
				system: "System Time (s)",
				real: "Real Time (s)",
				"catalog_mgr.n_lookup_path": "Catalog Mgr: #Path lookups",
			};

			const layout = {
				yaxis: {
					title: yAxisTitles[metricName] || metricName,
				},
				xaxis: {
					title: "Commits",
					tickvals: x_ticks,
					ticktext: x_ticks,
				},
				showlegend: true,
				height: 600,
				boxmode: "group",
				hovermode: "closest",
			};

			Plotly.newPlot(plotElement, traces, layout, {
				responsive: true,
				modeBarButtonsToRemove: [
					"select2d",
					"lasso2d",
					"zoomIn2d",
					"zoomOut2d",
					"autoScale2d",
				],
			});

			plotElement.on("plotly_click", (eventData) => {
				const commitSHA = eventData.points[0].customdata;
				const tempInput = document.createElement("textarea");
				tempInput.value = commitSHA;
				document.body.appendChild(tempInput);
				tempInput.select();
				document.execCommand("copy");
				document.body.removeChild(tempInput);
				alert(`Commit ${commitSHA} copied to clipboard!`);
			});
		})
		.catch((error) => {
			console.error("Error creating boxplot:", error);
			plotElement.innerHTML = "<p>Error creating boxplot.</p>";
		});
}

function createOverviewPlots(configurationData) {
	const overviewContainer = document.getElementById("overview-plots");

	// Use names instead of IDs
	const plotInfoList = [
		{ clientConfigName: "default", commandName: "root", metricName: "system" },
		{ clientConfigName: "default", commandName: "root", metricName: "real" },
	];

	for (const plotInfo of plotInfoList) {
		// Create plot container
		const plotContainer = document.createElement("div");
		plotContainer.classList.add("plot-box");

		// Add plot title
		const plotTitle = document.createElement("div");
		plotTitle.classList.add("plot-title");

		plotTitle.textContent = `${plotInfo.commandName}`;
		plotContainer.appendChild(plotTitle);

		// Create plot div
		const plotDiv = document.createElement("div");
		plotDiv.classList.add("benchmark-plot-box");
		plotContainer.appendChild(plotDiv);

		// Append to overview container
		overviewContainer.appendChild(plotContainer);

		// Create the plot
		createLinePlotCustom(
			plotDiv,
			plotInfo.clientConfigName,
			plotInfo.commandName,
			plotInfo.metricName,
			12,
			configurationData,
		);
	}
}

// Function to display commit results
function displayCommitResults(commit) {
	// Fetch benchmark results for the selected commit
	fetch(`/api/results_by_commit?commit=${encodeURIComponent(commit)}`)
		.then((response) => response.json())
		.then((data) => {
			if (data.error) {
				console.error("Error fetching commit results:", data.error);
				return;
			}

			// Display commit info
			const commitInfoDiv = document.getElementById("commit-info");
			commitInfoDiv.innerHTML = `
                <p><strong>Commit:</strong> ${data.commit_info.commit}</p>
                <p><strong>Date:</strong> ${formatDateTime(data.commit_info.commit_datetime)}</p>
                <p><strong>Build Type:</strong> ${data.commit_info.build_type}</p>
                <p><strong>Version:</strong> ${data.commit_info.version}</p>
            `;

			// Populate the results table
			populateResultsTable(data.results);
		})
		.catch((error) => console.error("Error displaying commit results:", error));
}

// Function to populate the results table
function populateResultsTable(results) {
    const table = document.getElementById("results-table");
    table.innerHTML = ""; // Clear existing content

    if (results.length === 0) {
        table.innerHTML = "<tr><td>No results available for this commit.</td></tr>";
        return;
    }

    // Create table headers with data types
    const headers = [
        { text: "Command", type: "string" },
        { text: "Client Config", type: "string" },
        { text: "Metric", type: "string" },
        { text: "Cold Cache Min", type: "number" },
        { text: "Cold Cache Q1", type: "number" },
        { text: "Cold Cache Median", type: "number" },
        { text: "Cold Cache Q3", type: "number" },
        { text: "Cold Cache Max", type: "number" },
        { text: "Warm Cache Min", type: "number" },
        { text: "Warm Cache Q1", type: "number" },
        { text: "Warm Cache Median", type: "number" },
        { text: "Warm Cache Q3", type: "number" },
        { text: "Warm Cache Max", type: "number" },
        { text: "Hot Cache Min", type: "number" },
        { text: "Hot Cache Q1", type: "number" },
        { text: "Hot Cache Median", type: "number" },
        { text: "Hot Cache Q3", type: "number" },
        { text: "Hot Cache Max", type: "number" },
    ];

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");

    // Initialize sort directions per column
    const sortDirections = {};

    headers.forEach((header, index) => {
        const th = document.createElement("th");
        th.textContent = header.text;

        // Initialize sort direction for each column
        sortDirections[index] = true; // true for ascending, false for descending

        // Add click event listener for sorting
        th.addEventListener("click", () => {
            sortTableByColumn(table, index, header.type, sortDirections);
            // Toggle sort direction after sorting
            sortDirections[index] = !sortDirections[index];
        });

        headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Create table body
    const tbody = document.createElement("tbody");
    for (const result of results) {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>${escapeHTML(result.command_name)}</td>
            <td>${escapeHTML(result.client_config_name)}</td>
            <td>${escapeHTML(result.metric_name)}</td>
            <td>${result.cold_cache_min_val}</td>
            <td>${result.cold_cache_first_quartile}</td>
            <td>${result.cold_cache_median}</td>
            <td>${result.cold_cache_third_quartile}</td>
            <td>${result.cold_cache_max_val}</td>
            <td>${result.warm_cache_min_val}</td>
            <td>${result.warm_cache_first_quartile}</td>
            <td>${result.warm_cache_median}</td>
            <td>${result.warm_cache_third_quartile}</td>
            <td>${result.warm_cache_max_val}</td>
            <td>${result.hot_cache_min_val}</td>
            <td>${result.hot_cache_first_quartile}</td>
            <td>${result.hot_cache_median}</td>
            <td>${result.hot_cache_third_quartile}</td>
            <td>${result.hot_cache_max_val}</td>
        `;

        tbody.appendChild(row);
    }

    table.appendChild(tbody);
}

// Function to sort the table by a given column index and type
function sortTableByColumn(table, columnIndex, type, sortDirections) {
    const tbody = table.querySelector("tbody");
    const rows = Array.from(tbody.querySelectorAll("tr"));

    rows.sort((a, b) => {
        const cellA = a.children[columnIndex].innerText.trim();
        const cellB = b.children[columnIndex].innerText.trim();

        let comparison = 0;

        if (type === "number") {
            const numA = Number.parseFloat(cellA);
            const numB = Number.parseFloat(cellB);

            // Handle NaN values by pushing them to the end
            if (Number.isNaN(numA) && Number.isNaN(numB)) {
                comparison = 0;
            } else if (Number.isNaN(numA)) {
                comparison = 1;
            } else if (Number.isNaN(numB)) {
                comparison = -1;
            } else {
                comparison = numA - numB;
            }
        } else if (type === "string") {
            const strA = cellA.toLowerCase();
            const strB = cellB.toLowerCase();

            if (strA < strB) comparison = -1;
            else if (strA > strB) comparison = 1;
            else comparison = 0;
        }

        // Determine sort direction
        return sortDirections[columnIndex] ? comparison : -comparison;
    });

    // Re-append sorted rows
    for (const row of rows) {
        tbody.appendChild(row);
    }
}

// Function to download the results as a CSV file
function downloadCSV(commit) {
	fetch(`/api/results_by_commit_csv?commit=${encodeURIComponent(commit)}`)
		.then((response) => response.text())
		.then((csvContent) => {
			const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
			const link = document.createElement("a");
			link.href = URL.createObjectURL(blob);
			link.download = `results-${commit.slice(0, 6)}.csv`;
			link.style.display = "none";
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
		})
		.catch((error) => console.error("Error downloading CSV:", error));
}

function formatDateTime(datetimeStr) {
	// datetimeStr is in the format YYYYMMDDHHMMSS
	const year = datetimeStr.substring(0, 4);
	const month = datetimeStr.substring(4, 6);
	const day = datetimeStr.substring(6, 8);
	const hours = datetimeStr.substring(8, 10);
	const minutes = datetimeStr.substring(10, 12);
	const seconds = datetimeStr.substring(12, 14);

	return `${day}.${month}.${year}  ${hours}:${minutes}:${seconds}`;
}

// Function to safely escape HTML to prevent XSS
function escapeHTML(str) {
    if (typeof str !== "string") return str;
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
