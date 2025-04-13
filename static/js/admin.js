document.addEventListener('DOMContentLoaded', function() {
    // Handle responsive behavior for admin panel
    const handleResponsiveUI = () => {
        const isMobile = window.innerWidth < 768;
        const tableHeaders = document.querySelectorAll('table th:nth-child(n+4)');
        const tableCells = document.querySelectorAll('table td:nth-child(n+4)');

        // On mobile, we can dynamically adjust table columns
        if (isMobile) {
            tableHeaders.forEach(th => {
                if (!th.dataset.originalDisplay) {
                    th.dataset.originalDisplay = th.style.display;
                }
                // Keep only essential columns on mobile
                if (th.textContent.trim() === 'Actions') {
                    th.style.display = 'table-cell';
                } else {
                    th.style.display = 'none';
                }
            });

            tableCells.forEach(td => {
                if (!td.dataset.originalDisplay) {
                    td.dataset.originalDisplay = td.style.display;
                }
                // Keep only action buttons visible on mobile
                if (td.querySelector('.btn')) {
                    td.style.display = 'table-cell';
                } else {
                    td.style.display = 'none';
                }
            });
        } else {
            // Restore original display on desktop
            tableHeaders.forEach(th => {
                if (th.dataset.originalDisplay) {
                    th.style.display = th.dataset.originalDisplay;
                }
            });

            tableCells.forEach(td => {
                if (td.dataset.originalDisplay) {
                    td.style.display = td.dataset.originalDisplay;
                }
            });
        }
    };

    // Initialize responsive behavior
    handleResponsiveUI();
    window.addEventListener('resize', handleResponsiveUI);

    // Demo data loading for the admin interface
    const loadServerData = async () => {
        try {
            const response = await fetch('/api/gpu/seed-demo-data');
            const data = await response.json();

            if (data.status === 'success') {
                // Update server table with demo data
                updateServerTable(data.servers);
            }
        } catch (error) {
            console.error('Error loading demo data:', error);
        }
    };

    // Update server table with data
    const updateServerTable = (servers) => {
        const serverTableBody = document.querySelector('#llm-servers table tbody');
        if (!serverTableBody) return;

        // Clear "no servers" message if it exists
        if (serverTableBody.querySelector('td[colspan]')) {
            serverTableBody.innerHTML = '';
        }

        // Add server rows
        servers.forEach(server => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${server.id}</td>
                <td>${server.name}</td>
                <td>localhost</td>
                <td>4</td>
                <td><span class="badge bg-success">Active</span></td>
                <td><div class="progress" style="height: 6px;"><div class="progress-bar bg-info" style="width: 65%"></div></div></td>
                <td>
                    <button class="btn btn-sm btn-outline-secondary">Edit</button>
                    <button class="btn btn-sm btn-outline-danger">Stop</button>
                </td>
            `;
            serverTableBody.appendChild(row);
        });
    };

    // Initialize demo data if we're on the admin page
    if (document.querySelector('#llm-servers')) {
        loadServerData();
    }

    // Form validation for the new user form
    const newUserForm = document.getElementById('newUserForm');
    if (newUserForm) {
        const validateForm = () => {
            const username = document.getElementById('username').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;

            const isValid = username.length >= 3 && 
                          email.includes('@') && 
                          password.length >= 6;

            document.querySelector('#newUserModal .btn-primary').disabled = !isValid;
        };

        // Add validation listeners
        newUserForm.querySelectorAll('input, select').forEach(input => {
            input.addEventListener('input', validateForm);
        });
    }

    // Seed Data button click handler
    const seedDataBtn = document.getElementById('seedDataBtn');
    if (seedDataBtn) {
        seedDataBtn.addEventListener('click', async function() {
            if (!confirm('This will create a large amount of sample data for all aspects of the application. Proceed?')) {
                return;
            }

            try {
                seedDataBtn.disabled = true;
                seedDataBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Seeding data...';

                const response = await fetch('/api/seed-all-data');
                const data = await response.json();

                if (data.status === 'success') {
                    // Show success message
                    const successAlert = document.createElement('div');
                    successAlert.className = 'alert alert-success alert-dismissible fade show';
                    successAlert.innerHTML = `
                        <strong>Success!</strong> ${data.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    `;

                    // Insert the alert at the top of the page
                    const container = document.querySelector('.row.mb-4');
                    container.insertBefore(successAlert, container.firstChild);

                    // Auto-dismiss the alert after 5 seconds
                    setTimeout(() => {
                        successAlert.classList.remove('show');
                        setTimeout(() => successAlert.remove(), 300);
                    }, 5000);

                    // Reload the page after a short delay to show new data
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    console.error('Error seeding data:', data.message);
                    alert(`Error seeding data: ${data.message}`);
                }
            } catch (error) {
                console.error('Error seeding data:', error);
                alert(`Error seeding data: ${error.message}`);
            } finally {
                seedDataBtn.disabled = false;
                seedDataBtn.innerHTML = '<i class="bi bi-database-fill"></i> Seed Demo Data';
            }
        });
    }
});