// Analytics dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Function to create the GPU utilization heatmap
    function createGPUUtilizationHeatmap() {
        const heatmapContainer = document.querySelector('#heatmap-visualization');
        const loadingIndicator = document.querySelector('#heatmap-loading');
        const heatmapNoData = document.querySelector('#heatmap-no-data');
        const heatmapContent = document.querySelector('#heatmap-container');
        const serverStatusList = document.querySelector('#server-status-list');
        const lastUpdatedSpan = document.querySelector('#last-updated');
        const refreshButton = document.querySelector('#refresh-heatmap');
        
        if (!heatmapContainer) return;
        
        // Function to format the timestamp
        function formatTimestamp(timestamp) {
            const date = new Date(timestamp);
            return date.toLocaleTimeString();
        }
        
        // Function to determine color based on utilization percentage
        function getUtilizationColor(percentage) {
            if (percentage < 50) {
                // Green gradient (0-50%)
                const intensity = Math.min(1.0, percentage / 50);
                return `rgba(0, 200, 83, ${0.2 + intensity * 0.8})`;
            } else if (percentage < 80) {
                // Yellow gradient (50-80%)
                const intensity = Math.min(1.0, (percentage - 50) / 30);
                return `rgba(255, 193, 7, ${0.6 + intensity * 0.4})`;
            } else {
                // Red gradient (80-100%)
                const intensity = Math.min(1.0, (percentage - 80) / 20);
                return `rgba(244, 67, 54, ${0.8 + intensity * 0.2})`;
            }
        }
        
        // Function to fetch GPU utilization data from the API
        async function fetchGPUUtilizationData() {
            try {
                loadingIndicator.style.display = 'flex';
                heatmapContent.style.display = 'none';
                heatmapNoData.style.display = 'none';
                
                const response = await fetch('/api/gpu/utilization');
                const data = await response.json();
                
                if (data.status === 'success') {
                    if (data.data.length === 0) {
                        // No GPU servers available
                        heatmapNoData.style.display = 'block';
                    } else {
                        // Create the heatmap visualization
                        createHeatmapVisualization(data.data);
                        updateServerStatusList(data.data);
                        heatmapContent.style.display = 'block';
                    }
                    
                    // Update the last updated timestamp
                    lastUpdatedSpan.textContent = `Last updated: ${formatTimestamp(data.timestamp)}`;
                } else {
                    console.error('Error fetching GPU utilization data:', data.message);
                    heatmapNoData.style.display = 'block';
                    heatmapNoData.querySelector('.alert').textContent = `Error: ${data.message}`;
                }
            } catch (error) {
                console.error('Error fetching GPU utilization data:', error);
                heatmapNoData.style.display = 'block';
                heatmapNoData.querySelector('.alert').textContent = `Error: ${error.message}`;
            } finally {
                loadingIndicator.style.display = 'none';
            }
        }
        
        // Function to create the heatmap visualization
        function createHeatmapVisualization(data) {
            // Clear previous content
            heatmapContainer.innerHTML = '';
            
            // Create a wrapper div with responsive width
            const wrapper = document.createElement('div');
            wrapper.className = 'h-100 d-flex flex-column';
            
            // Create a header row with server names
            const headerRow = document.createElement('div');
            headerRow.className = 'mb-2 d-flex';
            
            // Add an empty cell for the time labels
            const emptyCell = document.createElement('div');
            emptyCell.style.width = '80px';
            headerRow.appendChild(emptyCell);
            
            // Add server name headers
            data.forEach(server => {
                const serverHeader = document.createElement('div');
                serverHeader.className = 'px-2 text-center';
                serverHeader.style.flex = '1';
                serverHeader.textContent = server.server_name;
                headerRow.appendChild(serverHeader);
            });
            
            wrapper.appendChild(headerRow);
            
            // Create the heatmap grid
            const heatmapGrid = document.createElement('div');
            heatmapGrid.className = 'flex-grow-1 d-flex flex-column';
            
            // Create rows for the grid
            const gridRows = [
                { label: 'GPU', dataKey: 'gpu_utilization', maxValue: 100 },
                { label: 'Memory', dataKey: 'gpu_memory_used', formatter: (server) => (server.gpu_memory_used / server.gpu_memory_total) * 100 },
                { label: 'CPU', dataKey: 'cpu_utilization', maxValue: 100 },
                { label: 'Queue', dataKey: 'queue_depth', formatter: (server) => Math.min(100, (server.queue_depth / 10) * 100) } // Normalize to 100%
            ];
            
            gridRows.forEach(row => {
                const gridRow = document.createElement('div');
                gridRow.className = 'd-flex align-items-center mb-2';
                
                // Add the row label
                const rowLabel = document.createElement('div');
                rowLabel.style.width = '80px';
                rowLabel.className = 'text-end pe-2';
                rowLabel.textContent = row.label;
                gridRow.appendChild(rowLabel);
                
                // Add cells for each server
                data.forEach(server => {
                    const cell = document.createElement('div');
                    cell.className = 'm-1 rounded';
                    cell.style.flex = '1';
                    cell.style.height = '50px';
                    
                    // Calculate the percentage value
                    let percentage;
                    if (row.formatter) {
                        percentage = row.formatter(server);
                    } else {
                        percentage = server[row.dataKey];
                    }
                    
                    // Set the background color based on utilization
                    cell.style.backgroundColor = getUtilizationColor(percentage);
                    
                    // Add a tooltip with the exact value
                    cell.title = `${percentage.toFixed(1)}%`;
                    
                    // Display the percentage in the cell
                    cell.innerHTML = `<div class="h-100 d-flex align-items-center justify-content-center fw-bold">${percentage.toFixed(0)}%</div>`;
                    
                    gridRow.appendChild(cell);
                });
                
                heatmapGrid.appendChild(gridRow);
            });
            
            wrapper.appendChild(heatmapGrid);
            heatmapContainer.appendChild(wrapper);
        }
        
        // Function to update the server status list
        function updateServerStatusList(data) {
            // Clear previous content
            serverStatusList.innerHTML = '';
            
            if (data.length === 0) {
                const noServers = document.createElement('p');
                noServers.className = 'text-muted';
                noServers.textContent = 'No active GPU servers';
                serverStatusList.appendChild(noServers);
                return;
            }
            
            // Create a list of server statuses
            const serverList = document.createElement('ul');
            serverList.className = 'list-unstyled';
            
            data.forEach(server => {
                const listItem = document.createElement('li');
                listItem.className = 'mb-3';
                
                // Determine status badge class
                let statusBadgeClass = 'bg-secondary';
                if (server.health_status === 'healthy') {
                    statusBadgeClass = 'bg-success';
                } else if (server.health_status === 'unhealthy') {
                    statusBadgeClass = 'bg-danger';
                }
                
                listItem.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span>${server.server_name}</span>
                        <span class="badge ${statusBadgeClass}">${server.health_status}</span>
                    </div>
                    <div class="small text-muted">
                        <div>Active Requests: ${server.active_requests}</div>
                        <div>GPU Memory: ${server.gpu_memory_used.toFixed(1)}/${server.gpu_memory_total} GB</div>
                    </div>
                `;
                
                serverList.appendChild(listItem);
            });
            
            serverStatusList.appendChild(serverList);
        }
        
        // Set up auto-refresh (every 10 seconds)
        let refreshInterval;
        
        function startAutoRefresh() {
            // Initial fetch
            fetchGPUUtilizationData();
            
            // Set up auto-refresh interval
            refreshInterval = setInterval(fetchGPUUtilizationData, 10000);
        }
        
        function stopAutoRefresh() {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
        }
        
        // Add event listener for the refresh button
        if (refreshButton) {
            refreshButton.addEventListener('click', fetchGPUUtilizationData);
        }
        
        // Add event listener for the seed demo data button
        const seedDemoButton = document.querySelector('#seed-demo-data');
        if (seedDemoButton) {
            seedDemoButton.addEventListener('click', async function() {
                try {
                    seedDemoButton.disabled = true;
                    seedDemoButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Seeding...';
                    
                    const response = await fetch('/api/gpu/seed-demo-data');
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        // Show success message
                        const successAlert = document.createElement('div');
                        successAlert.className = 'alert alert-success alert-dismissible fade show';
                        successAlert.innerHTML = `
                            <strong>Success!</strong> ${data.message}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        `;
                        
                        // Find a good place to insert the alert
                        const container = document.querySelector('#gpu-utilization-heatmap').parentNode;
                        container.insertBefore(successAlert, container.firstChild);
                        
                        // Fetch updated data
                        fetchGPUUtilizationData();
                        
                        // Auto-dismiss the alert after 5 seconds
                        setTimeout(() => {
                            successAlert.classList.remove('show');
                            setTimeout(() => successAlert.remove(), 300);
                        }, 5000);
                    } else {
                        console.error('Error seeding demo data:', data.message);
                        alert(`Error seeding demo data: ${data.message}`);
                    }
                } catch (error) {
                    console.error('Error seeding demo data:', error);
                    alert(`Error seeding demo data: ${error.message}`);
                } finally {
                    seedDemoButton.disabled = false;
                    seedDemoButton.innerHTML = '<i class="bi bi-database"></i> Seed Demo Data';
                }
            });
        }
        
        // Start auto-refresh when the page loads
        startAutoRefresh();
        
        // Clean up interval when navigating away
        window.addEventListener('beforeunload', stopAutoRefresh);
    }
    
    // Example function to create a line chart for query volume over time
    function createQueryVolumeChart() {
        const chartContainer = document.querySelector('#query-volume-chart');
        if (!chartContainer) return;
        
        // This would be replaced with real data from an API
        const noDataMessage = document.createElement('p');
        noDataMessage.className = 'text-muted text-center';
        noDataMessage.textContent = 'No query data available yet. Data will appear here as users interact with the LLM platform.';
        chartContainer.appendChild(noDataMessage);
        
        // With real data, we would create a chart like this:
        /*
        const ctx = document.createElement('canvas').getContext('2d');
        chartContainer.appendChild(ctx.canvas);
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'],
                datasets: [{
                    label: 'Queries',
                    data: [12, 19, 3, 5, 2, 3, 7],
                    borderColor: '#00c0ff',
                    tension: 0.3,
                    fill: {
                        target: 'origin',
                        above: 'rgba(0, 192, 255, 0.1)'
                    }
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        */
    }
    
    // Example function to create a pie chart for model usage
    function createModelUsageChart() {
        const chartContainer = document.querySelector('#model-usage-chart');
        if (!chartContainer) return;
        
        // This would be replaced with real data from an API
        const noDataMessage = document.createElement('p');
        noDataMessage.className = 'text-muted text-center';
        noDataMessage.textContent = 'No model usage data available yet. Data will appear here as users interact with different models.';
        chartContainer.appendChild(noDataMessage);
        
        // With real data, we would create a chart like this:
        /*
        const ctx = document.createElement('canvas').getContext('2d');
        chartContainer.appendChild(ctx.canvas);
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Mistral-7B', 'LLaMA 3-8B', 'Gemma-7B', 'Fine-tuned Models'],
                datasets: [{
                    data: [40, 30, 20, 10],
                    backgroundColor: [
                        '#00c0ff',
                        '#4758a8',
                        '#8a56ac',
                        '#5bc8af'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
        */
    }
    
    // Initialize the components
    createGPUUtilizationHeatmap();
    createQueryVolumeChart();
    createModelUsageChart();
    
    // Add event listener for date range selector (if any)
    const dateRangeSelector = document.querySelector('#date-range-selector');
    if (dateRangeSelector) {
        dateRangeSelector.addEventListener('change', function() {
            // In a real implementation, we would fetch new data for the selected date range
            alert('Date range changed! In a real implementation, this would refresh the analytics data.');
        });
    }
    
    // Add event listener for data export button
    const exportButtons = document.querySelectorAll('button.btn-outline-secondary:not(#refresh-heatmap):not(#view-all-queries)');
    if (exportButtons.length > 0) {
        exportButtons.forEach(button => {
            button.addEventListener('click', function() {
                try {
                    // Create a timestamp for the filename
                    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                    const filename = `focal-platform-data-export-${timestamp}.csv`;
                    
                    // Create a sample CSV content (this will be replaced with real data)
                    let csvContent = "data:text/csv;charset=utf-8,";
                    
                    // Get currently visible data - for demo, we'll create sample data
                    // In production, this would come from the actual data source
                    csvContent += "Timestamp,Server,GPU Utilization,Memory Used,Memory Total,CPU Utilization,Active Requests,Queue Depth\n";
                    
                    // Add some sample rows - in production these would be real data points
                    const now = new Date();
                    csvContent += `${now.toISOString()},default-gpu-server,78.5,18.2,24.0,45.0,12,3\n`;
                    csvContent += `${now.toISOString()},secondary-gpu-server,35.2,6.8,16.0,28.0,4,0\n`;
                    
                    // Create a download link
                    const encodedUri = encodeURI(csvContent);
                    const link = document.createElement("a");
                    link.setAttribute("href", encodedUri);
                    link.setAttribute("download", filename);
                    document.body.appendChild(link);
                    
                    // Trigger the download
                    link.click();
                    
                    // Clean up
                    document.body.removeChild(link);
                    
                    // Success message
                    const successAlert = document.createElement('div');
                    successAlert.className = 'alert alert-success alert-dismissible fade show mt-3';
                    successAlert.innerHTML = `
                        <strong>Success!</strong> Data exported to ${filename}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    `;
                    
                    // Find a good place to insert the alert
                    const alertContainer = document.querySelector('.card-body');
                    if (alertContainer) {
                        alertContainer.insertBefore(successAlert, alertContainer.firstChild);
                        
                        // Auto-dismiss after 5 seconds
                        setTimeout(() => {
                            successAlert.classList.remove('show');
                            setTimeout(() => successAlert.remove(), 300);
                        }, 5000);
                    }
                } catch (error) {
                    console.error('Error exporting data:', error);
                    alert(`Error exporting data: ${error.message}`);
                }
            });
        });
    }
    
    // Add event listener for View All Queries button
    const viewAllQueriesButton = document.querySelector('#view-all-queries');
    if (viewAllQueriesButton) {
        viewAllQueriesButton.addEventListener('click', function() {
            // In a production implementation, this would:
            // 1. Fetch all queries from the API
            // 2. Display them in a modal or new page
            
            // Create a Bootstrap modal to display all queries
            const modalHTML = `
                <div class="modal fade" id="allQueriesModal" tabindex="-1" aria-labelledby="allQueriesModalLabel" aria-hidden="true">
                    <div class="modal-dialog modal-xl">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="allQueriesModalLabel">All Queries</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="table-responsive">
                                    <table class="table table-striped table-hover">
                                        <thead>
                                            <tr>
                                                <th>Time</th>
                                                <th>User</th>
                                                <th>Query</th>
                                                <th>Model</th>
                                                <th>Response Time</th>
                                                <th>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <!-- Sample data for demonstration purposes only -->
                                            <tr>
                                                <td>${new Date().toLocaleString()}</td>
                                                <td>admin</td>
                                                <td>Explain the benefits of on-premises LLM deployment</td>
                                                <td>Mistral-7B</td>
                                                <td>1250ms</td>
                                                <td><span class="badge bg-success">Completed</span></td>
                                            </tr>
                                            <tr>
                                                <td>${new Date(Date.now() - 10*60000).toLocaleString()}</td>
                                                <td>john.doe</td>
                                                <td>Generate a SQL query to find the top 10 customers by revenue</td>
                                                <td>LLaMA 3-8B</td>
                                                <td>872ms</td>
                                                <td><span class="badge bg-success">Completed</span></td>
                                            </tr>
                                            <tr>
                                                <td>${new Date(Date.now() - 25*60000).toLocaleString()}</td>
                                                <td>sarah.jones</td>
                                                <td>Summarize the latest quarterly earnings report</td>
                                                <td>Gemma-7B</td>
                                                <td>1645ms</td>
                                                <td><span class="badge bg-success">Completed</span></td>
                                            </tr>
                                            <tr>
                                                <td>${new Date(Date.now() - 40*60000).toLocaleString()}</td>
                                                <td>robert.smith</td>
                                                <td>How can we optimize our current GPU utilization?</td>
                                                <td>Mistral-7B</td>
                                                <td>1120ms</td>
                                                <td><span class="badge bg-success">Completed</span></td>
                                            </tr>
                                            <tr>
                                                <td>${new Date(Date.now() - 55*60000).toLocaleString()}</td>
                                                <td>emily.wilson</td>
                                                <td>Create a Python script to process our customer feedback data</td>
                                                <td>Claude-3</td>
                                                <td>2145ms</td>
                                                <td><span class="badge bg-warning text-dark">Cached</span></td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                                <button type="button" class="btn btn-primary" id="export-all-queries">
                                    <i class="bi bi-download"></i> Export All
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Append the modal to the body
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            // Initialize the modal
            const modal = new bootstrap.Modal(document.getElementById('allQueriesModal'));
            modal.show();
            
            // Add event listener for the Export All button
            document.getElementById('export-all-queries').addEventListener('click', function() {
                try {
                    // Create a timestamp for the filename
                    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                    const filename = `focal-platform-all-queries-${timestamp}.csv`;
                    
                    // Create a CSV content
                    let csvContent = "data:text/csv;charset=utf-8,";
                    
                    // Headers
                    csvContent += "Timestamp,User,Query,Model,Response Time (ms),Status\n";
                    
                    // Sample data
                    csvContent += `${new Date().toISOString()},admin,"Explain the benefits of on-premises LLM deployment",Mistral-7B,1250,Completed\n`;
                    csvContent += `${new Date(Date.now() - 10*60000).toISOString()},john.doe,"Generate a SQL query to find the top 10 customers by revenue",LLaMA 3-8B,872,Completed\n`;
                    csvContent += `${new Date(Date.now() - 25*60000).toISOString()},sarah.jones,"Summarize the latest quarterly earnings report",Gemma-7B,1645,Completed\n`;
                    csvContent += `${new Date(Date.now() - 40*60000).toISOString()},robert.smith,"How can we optimize our current GPU utilization?",Mistral-7B,1120,Completed\n`;
                    csvContent += `${new Date(Date.now() - 55*60000).toISOString()},emily.wilson,"Create a Python script to process our customer feedback data",Claude-3,2145,Cached\n`;
                    
                    // Create a download link
                    const encodedUri = encodeURI(csvContent);
                    const link = document.createElement("a");
                    link.setAttribute("href", encodedUri);
                    link.setAttribute("download", filename);
                    document.body.appendChild(link);
                    
                    // Trigger the download
                    link.click();
                    
                    // Clean up
                    document.body.removeChild(link);
                    
                    // Show success toast
                    const toastContainer = document.createElement('div');
                    toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
                    toastContainer.style.zIndex = '5';
                    toastContainer.innerHTML = `
                        <div id="exportToast" class="toast hide" role="alert" aria-live="assertive" aria-atomic="true">
                            <div class="toast-header">
                                <i class="bi bi-check-circle-fill text-success me-2"></i>
                                <strong class="me-auto">Export Successful</strong>
                                <small>${new Date().toLocaleTimeString()}</small>
                                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                            </div>
                            <div class="toast-body">
                                All queries have been exported to ${filename}
                            </div>
                        </div>
                    `;
                    
                    document.body.appendChild(toastContainer);
                    const toast = new bootstrap.Toast(document.getElementById('exportToast'));
                    toast.show();
                    
                    // Clean up toast after it's hidden
                    document.getElementById('exportToast').addEventListener('hidden.bs.toast', function () {
                        document.body.removeChild(toastContainer);
                    });
                } catch (error) {
                    console.error('Error exporting queries:', error);
                    alert(`Error exporting queries: ${error.message}`);
                }
            });
            
            // Clean up modal when it's hidden
            document.getElementById('allQueriesModal').addEventListener('hidden.bs.modal', function () {
                document.body.removeChild(document.getElementById('allQueriesModal'));
            });
        });
    }
});