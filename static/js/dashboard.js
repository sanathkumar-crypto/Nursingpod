// Dashboard JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the dashboard
    initializeDashboard();
    
    // Set up event listeners
    setupEventListeners();
    
    // Load initial data
    loadInitialData();
});

function initializeDashboard() {
    console.log('Nursing Pod Quality Dashboard initialized');
    
    // Inject global style for hospital dropdown height limit - VERY AGGRESSIVE
    if (!document.getElementById('hospital-dropdown-limit-style')) {
        const style = document.createElement('style');
        style.id = 'hospital-dropdown-limit-style';
        style.textContent = `
            /* Target hospital dropdown specifically */
            .select2-dropdown.hospital-select2-dropdown {
                max-height: 280px !important;
                overflow: hidden !important;
            }
            .select2-dropdown.hospital-select2-dropdown .select2-results,
            .select2-dropdown.hospital-select2-dropdown .select2-results__options {
                max-height: 240px !important;
                overflow-y: auto !important;
                overflow-x: hidden !important;
            }
            /* Also target any Select2 dropdown that appears when hospital filter is focused */
            body > .select2-dropdown:not(.select2-dropdown--above) {
                max-height: 280px !important;
            }
            body > .select2-dropdown .select2-results__options {
                max-height: 240px !important;
                overflow-y: auto !important;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Initialize Select2 for hospital multi-select dropdown
    const hospitalSelect = $('#hospital-filter');
    if (hospitalSelect.length) {
        hospitalSelect.select2({
            theme: 'bootstrap-5',
            width: '100%',
            placeholder: 'Select hospitals...',
            allowClear: false,
            closeOnSelect: false,
            maximumSelectionLength: null, // Allow selecting all
            dropdownCssClass: 'hospital-select2-dropdown'
        });
        
        // Add a class to the Select2 container for easier CSS targeting
        const select2Container = hospitalSelect.next('.select2-container');
        if (select2Container.length) {
            select2Container.addClass('hospital-filter-container');
        }
        
        // Use MutationObserver to watch for dropdown creation
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 && node.classList) {
                        // Check if it's any Select2 dropdown, then check if it's for hospital filter
                        if (node.classList.contains('select2-dropdown')) {
                            // Check if it's the hospital dropdown by checking if it's near the hospital filter
                            const isHospitalDropdown = node.classList.contains('hospital-select2-dropdown') ||
                                (document.getElementById('hospital-filter') && 
                                 node.querySelector('.select2-results__options') &&
                                 document.getElementById('hospital-filter').offsetParent);
                            
                            if (isHospitalDropdown) {
                                console.log('Hospital dropdown detected, applying height limit');
                                applyHeightLimitToDropdown(node);
                            }
                        }
                    }
                });
            });
        });
        
        // Start observing the document body for new elements
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // Function to apply height limit - VERY AGGRESSIVE
        function applyHeightLimitToDropdown(dropdown) {
            if (!dropdown) return;
            
            console.log('Applying height limit to dropdown', dropdown);
            
            // Set height on dropdown itself - use both methods
            dropdown.style.maxHeight = '280px';
            dropdown.style.overflow = 'hidden';
            dropdown.style.setProperty('max-height', '280px', 'important');
            dropdown.style.setProperty('overflow', 'hidden', 'important');
            
            // Find and limit results container
            const resultsContainer = dropdown.querySelector('.select2-results');
            if (resultsContainer) {
                console.log('Found results container, setting height');
                resultsContainer.style.maxHeight = '240px';
                resultsContainer.style.overflowY = 'auto';
                resultsContainer.style.overflowX = 'hidden';
                resultsContainer.style.setProperty('max-height', '240px', 'important');
                resultsContainer.style.setProperty('overflow-y', 'auto', 'important');
                resultsContainer.style.setProperty('overflow-x', 'hidden', 'important');
            } else {
                console.log('Results container not found');
            }
            
            // Find and limit results options - THIS IS THE KEY ELEMENT
            const results = dropdown.querySelector('.select2-results__options');
            if (results) {
                console.log('Found results options, setting height', results);
                results.style.maxHeight = '240px';
                results.style.overflowY = 'auto';
                results.style.overflowX = 'hidden';
                results.style.setProperty('max-height', '240px', 'important');
                results.style.setProperty('overflow-y', 'auto', 'important');
                results.style.setProperty('overflow-x', 'hidden', 'important');
                
                // Also try setting height directly
                results.style.height = '240px';
            } else {
                console.log('Results options not found - checking dropdown structure:', dropdown.innerHTML.substring(0, 200));
            }
        }
        
        // Force dropdown height limit when opened - multiple approaches
        hospitalSelect.on('select2:open', function() {
            console.log('Hospital filter opened, applying height limits');
            
            function findAndLimitDropdown() {
                // Try multiple selectors - be very aggressive
                let dropdown = document.querySelector('.select2-dropdown.hospital-select2-dropdown');
                if (!dropdown) {
                    // Try finding any Select2 dropdown
                    dropdown = document.querySelector('.select2-dropdown:not(.select2-dropdown--above)');
                }
                if (!dropdown) {
                    dropdown = document.querySelector('.select2-dropdown');
                }
                
                if (dropdown) {
                    console.log('Found dropdown, applying limits', dropdown);
                    applyHeightLimitToDropdown(dropdown);
                    return true;
                } else {
                    console.log('Dropdown not found yet');
                }
                return false;
            }
            
            // Try immediately and with multiple delays
            findAndLimitDropdown();
            setTimeout(findAndLimitDropdown, 0);
            setTimeout(findAndLimitDropdown, 10);
            setTimeout(findAndLimitDropdown, 50);
            setTimeout(findAndLimitDropdown, 100);
            setTimeout(findAndLimitDropdown, 200);
            setTimeout(findAndLimitDropdown, 500);
        });
        
        // Also try on focus/click as backup
        hospitalSelect.on('focus', function() {
            setTimeout(function() {
                const dropdown = document.querySelector('.select2-dropdown');
                if (dropdown) {
                    console.log('Dropdown found on focus, applying limits');
                    applyHeightLimitToDropdown(dropdown);
                }
            }, 100);
        });
        
        // Continuous monitoring - check every 100ms when dropdown might be open
        setInterval(function() {
            const dropdown = document.querySelector('.select2-dropdown.hospital-select2-dropdown, .select2-dropdown');
            if (dropdown && dropdown.style.display !== 'none') {
                const results = dropdown.querySelector('.select2-results__options');
                if (results) {
                    const currentHeight = results.style.maxHeight || window.getComputedStyle(results).maxHeight;
                    if (currentHeight !== '240px' && currentHeight !== '240px !important') {
                        console.log('Forcing height limit on dropdown');
                        applyHeightLimitToDropdown(dropdown);
                    }
                }
            }
        }, 100);
        
        // Close dropdown when clicking outside
        $(document).on('click', function(e) {
            if (!$(e.target).closest('.select2-container').length && 
                !$(e.target).closest('.select2-dropdown').length) {
                if (hospitalSelect.data('select2')) {
                    hospitalSelect.select2('close');
                }
            }
        });
        
        // Hide selected hospital tags/chips display
        function hideSelectedHospitalTags() {
            // Find the Select2 container for hospital filter
            const select2Container = hospitalSelect.next('.select2-container');
            if (select2Container.length) {
                // Add class for CSS targeting
                select2Container.addClass('hospital-filter-container');
                // Hide all selected choice tags using multiple methods
                const choices = select2Container.find('.select2-selection__choice');
                choices.hide();
                choices.css({
                    'display': 'none !important',
                    'visibility': 'hidden',
                    'opacity': '0',
                    'width': '0',
                    'height': '0',
                    'padding': '0',
                    'margin': '0'
                });
            }
        }
        
        // Hide tags after Select2 initializes
        setTimeout(hideSelectedHospitalTags, 100);
        setTimeout(hideSelectedHospitalTags, 300);
        
        // Hide tags whenever selection changes
        hospitalSelect.on('select2:select select2:unselect change select2:close', function() {
            setTimeout(hideSelectedHospitalTags, 10);
            setTimeout(hideSelectedHospitalTags, 50);
        });
        
        // Also use MutationObserver to hide tags when they're added
        const tagObserver = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 && node.classList && 
                        (node.classList.contains('select2-selection__choice') || 
                         node.querySelector && node.querySelector('.select2-selection__choice'))) {
                        hideSelectedHospitalTags();
                    }
                });
            });
        });
        
        // Observe the Select2 container for new tags
        setTimeout(function() {
            const select2Container = hospitalSelect.next('.select2-container');
            if (select2Container.length) {
                tagObserver.observe(select2Container[0], {
                    childList: true,
                    subtree: true
                });
            }
        }, 200);
        
        // Auto-select all hospitals by default (excluding the "all" option)
        const allHospitals = Array.from(hospitalSelect[0].options)
            .map(option => option.value)
            .filter(value => value !== 'all');
        hospitalSelect.val(allHospitals);
        hospitalSelect.trigger('change.select2');
        
        // Hide tags after initial selection
        setTimeout(hideSelectedHospitalTags, 200);
        
        // Handle "All Hospitals" option selection
        hospitalSelect.on('select2:select', function(e) {
            const selectedValue = e.params.data.id;
            if (selectedValue === 'all') {
                // Select all hospitals (excluding "all" option)
                const allHospitalValues = Array.from(hospitalSelect[0].options)
                    .map(option => option.value)
                    .filter(value => value !== 'all');
                hospitalSelect.val(allHospitalValues);
                hospitalSelect.trigger('change.select2');
            }
        });
        
        // Add event listener for hospital filter changes (after setting initial values)
        hospitalSelect.on('change', function() {
            applyFilters();
        });
    }
    
    // Set up any initial configurations
    const filterStatus = document.getElementById('filter-status');
    if (filterStatus) {
        filterStatus.textContent = 'Ready to filter data';
    }
}

function setupEventListeners() {
    // Apply filters button
    const applyFiltersBtn = document.getElementById('apply-filters');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    // Reset filters button
    const resetFiltersBtn = document.getElementById('reset-filters');
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', resetFilters);
    }
    
    // Escalation filter change - trigger chart update
    const escalationFilter = document.getElementById('escalation-filter');
    if (escalationFilter) {
        escalationFilter.addEventListener('change', applyFilters);
    }
    
    // Email filter change - trigger chart update
    const emailFilter = document.getElementById('email-filter');
    if (emailFilter) {
        emailFilter.addEventListener('change', applyFilters);
    }
    
    // Date range change events
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    
    if (startDateInput) {
        startDateInput.addEventListener('change', applyFilters);
    }
    if (endDateInput) {
        endDateInput.addEventListener('change', applyFilters);
    }
    
    // Exclude Camera Annotations checkbox
    const excludeCameraCheckbox = document.getElementById('exclude-camera-annotations');
    if (excludeCameraCheckbox) {
        excludeCameraCheckbox.addEventListener('change', applyFilters);
    }
    
    // Select All Hospitals button
    const selectAllHospitalsBtn = document.getElementById('select-all-hospitals');
    if (selectAllHospitalsBtn) {
        selectAllHospitalsBtn.addEventListener('click', function() {
            const hospitalSelect = $('#hospital-filter');
            if (hospitalSelect.length) {
                // Get all hospital values (excluding "all" option)
                const allHospitals = Array.from(hospitalSelect[0].options)
                    .map(option => option.value)
                    .filter(value => value !== 'all');
                // Select all
                hospitalSelect.val(allHospitals);
                hospitalSelect.trigger('change');
                console.log('All hospitals selected');
            }
        });
    }
    
    // Clear All Hospitals button
    const unselectAllHospitalsBtn = document.getElementById('unselect-all-hospitals');
    if (unselectAllHospitalsBtn) {
        unselectAllHospitalsBtn.addEventListener('click', function() {
            const hospitalSelect = $('#hospital-filter');
            if (hospitalSelect.length) {
                // Clear all selections
                hospitalSelect.val(null);
                hospitalSelect.trigger('change');
                console.log('All hospitals cleared');
            }
        });
    }
}

function loadInitialData() {
    // Load data with default filters (all)
    applyFilters();
}

function applyFilters() {
    // Get filter values
    const escalation = document.getElementById('escalation-filter').value;
    const email = document.getElementById('email-filter').value;
    
    // Handle multiple hospital selections (works with Select2)
    const hospitalSelect = $('#hospital-filter');
    const selectedHospitals = hospitalSelect.val() || [];
    // Filter out 'all' option from selected hospitals
    const actualSelectedHospitals = selectedHospitals.filter(h => h !== 'all');
    const allOptions = Array.from(hospitalSelect[0].options)
        .map(opt => opt.value)
        .filter(opt => opt !== 'all'); // Exclude 'all' option from count
    
    // If all hospitals are selected (or most of them), send 'all' to avoid huge SQL queries
    const hospital = (actualSelectedHospitals.length === 0 || 
                     actualSelectedHospitals.length === allOptions.length ||
                     actualSelectedHospitals.length > 100) ? 'all' : actualSelectedHospitals.join(',');
    
    // Handle date range
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const dateRange = startDate && endDate ? `${startDate},${endDate}` : 'all';
    
    // Check if exclude camera annotations checkbox is checked
    const excludeCameraCheckbox = document.getElementById('exclude-camera-annotations');
    const excludeCamera = excludeCameraCheckbox && excludeCameraCheckbox.checked ? 'true' : 'false';
    
    // Debug logging
    console.log('=== Apply Filters ===');
    console.log('Escalation:', escalation);
    console.log('Email:', email);
    console.log('Hospital:', hospital);
    console.log('Date Range:', dateRange);
    console.log('Exclude Camera Annotations:', excludeCamera);
    
    // Show loading state
    showLoadingState();
    
    // Update filter status
    updateFilterStatus(escalation, email, selectedHospitals, startDate, endDate);
    
    // Make API calls for both table and charts
    const params = new URLSearchParams({
        escalation: escalation,
        email: email,
        hospital: hospital,
        date: dateRange,
        exclude_camera: excludeCamera
    });
    
    console.log('API URL:', `/api/charts?${params}`);
    
    // Fetch table data
    fetch(`/api/filter?${params}`, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => {
            if (!response.ok) {
                // If redirect to login, try to reload the page
                if (response.status === 401 || response.status === 302) {
                    console.warn('Authentication required, reloading page...');
                    window.location.reload();
                    return Promise.reject(new Error('Authentication required'));
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Update table
            updateDataTable(data.table_html);
            
            // Update data count
            updateDataCount(data.row_count);
            
            console.log(`Loaded ${data.row_count} rows with ${data.columns.length} columns`);
        })
        .catch(error => {
            console.error('Error loading filtered data:', error);
            console.error('Error details:', error.message);
            showErrorState();
        });
    
    // Fetch chart data
    fetch(`/api/charts?${params}`, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => {
            console.log('Chart API response status:', response.status);
            if (!response.ok) {
                // If redirect to login, try to reload the page
                if (response.status === 401 || response.status === 302) {
                    console.warn('Authentication required, reloading page...');
                    window.location.reload();
                    return Promise.reject(new Error('Authentication required'));
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Check if there's an error in the response
            if (data.error) {
                console.error('Chart API returned error:', data.error);
                hideLoadingState();
                return;
            }
            
            // Update monthly trend chart
            const monthlyTrendData = JSON.parse(data.monthly_trend);
            
            // Debug: Log what escalation types are in the data
            const escalationTypes = monthlyTrendData.data.map(trace => trace.name);
            console.log('Escalation types in monthly trend:', escalationTypes);
            console.log('Number of traces:', escalationTypes.length);
            
            // Ensure layout has proper sizing
            if (!monthlyTrendData.layout.height) {
                monthlyTrendData.layout.height = 500;
            }
            if (!monthlyTrendData.layout.autosize) {
                monthlyTrendData.layout.autosize = true;
            }
            Plotly.react('monthly-trend-chart', monthlyTrendData.data, monthlyTrendData.layout, {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['toImage']
            });
            
            // Update escalation distribution chart
            const escalationDistData = JSON.parse(data.escalation_dist);
            
            // Debug: Log pie chart data
            if (escalationDistData.data && escalationDistData.data[0] && escalationDistData.data[0].labels) {
                console.log('Escalation types in distribution:', escalationDistData.data[0].labels);
            }
            
            // Ensure layout has proper sizing
            if (!escalationDistData.layout.height) {
                escalationDistData.layout.height = 500;
            }
            if (!escalationDistData.layout.autosize) {
                escalationDistData.layout.autosize = true;
            }
            Plotly.react('escalation-distribution-chart', escalationDistData.data, escalationDistData.layout, {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['toImage']
            });
            
            // Handle nurse-wise trend chart (for Camera Annotation Events and Educating nurses)
            const escalation = document.getElementById('escalation-filter').value;
            const nurseWiseTrendRow = document.getElementById('nurse-wise-trend-row');
            const nurseWiseTrendChart = document.getElementById('nurse-wise-trend-chart');
            
            // Show/hide nurse-wise trend chart based on escalation type
            if ((escalation === 'Camera Annotation Events' || escalation === 'Educating nurses') && data.nurse_wise_trend) {
                // Show the nurse-wise trend chart row
                if (nurseWiseTrendRow) {
                    nurseWiseTrendRow.style.display = 'block';
                }
                
                try {
                    // Update nurse-wise trend chart
                    const nurseWiseTrendData = JSON.parse(data.nurse_wise_trend);
                    
                    // Verify chart data is valid
                    if (nurseWiseTrendData && nurseWiseTrendData.data && nurseWiseTrendData.layout) {
                        // Ensure layout has proper sizing
                        if (!nurseWiseTrendData.layout.height) {
                            nurseWiseTrendData.layout.height = 500;
                        }
                        if (!nurseWiseTrendData.layout.autosize) {
                            nurseWiseTrendData.layout.autosize = true;
                        }
                        
                        // Wait a bit to ensure the DOM element is ready
                        setTimeout(() => {
                            if (nurseWiseTrendChart) {
                                Plotly.react('nurse-wise-trend-chart', nurseWiseTrendData.data, nurseWiseTrendData.layout, {
                                    responsive: true,
                                    displayModeBar: true,
                                    modeBarButtonsToRemove: ['toImage']
                                });
                                console.log('Nurse-wise trend chart updated successfully');
                            } else {
                                console.warn('Nurse-wise trend chart element not found');
                            }
                        }, 100);
                    } else {
                        console.warn('Invalid nurse-wise trend data structure:', nurseWiseTrendData);
                    }
                } catch (parseError) {
                    console.error('Error parsing nurse-wise trend data:', parseError);
                    console.error('Raw data:', data.nurse_wise_trend);
                }
            } else {
                // Hide the nurse-wise trend chart row for other escalation types
                if (nurseWiseTrendRow) {
                    nurseWiseTrendRow.style.display = 'none';
                }
                console.log('Nurse-wise trend chart hidden (escalation:', escalation, ', has data:', !!data.nurse_wise_trend, ')');
            }
            
            // Hide loading state
            hideLoadingState();
            
            console.log('Charts updated successfully');
        })
        .catch(error => {
            console.error('Error loading chart data:', error);
            console.error('Error details:', error.message);
            hideLoadingState();
        });
}

function resetFilters() {
    // Reset all filter dropdowns to 'all'
    document.getElementById('escalation-filter').value = 'all';
    document.getElementById('email-filter').value = 'all';
    
    // Reset hospital multi-select to select all hospitals (works with Select2)
    const hospitalSelect = $('#hospital-filter');
    const allHospitals = Array.from(hospitalSelect[0].options)
        .map(option => option.value)
        .filter(value => value !== 'all'); // Exclude 'all' option
    hospitalSelect.val(allHospitals).trigger('change');
    
    // Reset date range inputs
    document.getElementById('start-date').value = '';
    document.getElementById('end-date').value = '';
    
    // Reset exclude camera annotations checkbox
    const excludeCameraCheckbox = document.getElementById('exclude-camera-annotations');
    if (excludeCameraCheckbox) {
        excludeCameraCheckbox.checked = false;
    }
    
    // Apply the reset filters
    applyFilters();
}

function updateFilterStatus(escalation, email, hospitals, startDate, endDate) {
    const filterStatus = document.getElementById('filter-status');
    const activeFilters = [];
    
    if (escalation !== 'all') activeFilters.push(`Escalation: ${escalation}`);
    if (email !== 'all') activeFilters.push(`Nurse: ${email.split('@')[0]}`);
    
    // Handle multiple hospitals
    if (hospitals && hospitals.length > 0 && !hospitals.includes('all')) {
        if (hospitals.length === 1) {
            activeFilters.push(`Hospital: ${hospitals[0]}`);
        } else if (hospitals.length <= 3) {
            activeFilters.push(`Hospitals: ${hospitals.join(', ')}`);
        } else {
            activeFilters.push(`Hospitals: ${hospitals.slice(0, 2).join(', ')} +${hospitals.length - 2} more`);
        }
    }
    
    // Handle date range
    if (startDate && endDate) {
        activeFilters.push(`Date Range: ${startDate} to ${endDate}`);
    } else if (startDate) {
        activeFilters.push(`From: ${startDate}`);
    } else if (endDate) {
        activeFilters.push(`Until: ${endDate}`);
    }
    
    if (activeFilters.length === 0) {
        filterStatus.textContent = 'Showing all data';
    } else {
        filterStatus.textContent = `Active filters: ${activeFilters.join(', ')}`;
    }
}

function updateDataTable(tableHtml) {
    const tableContainer = document.getElementById('data-table-container');
    if (tableContainer) {
        tableContainer.innerHTML = tableHtml;
        
        // Add custom styling to the table
        const table = tableContainer.querySelector('table');
        if (table) {
            table.classList.add('table', 'table-striped', 'table-hover');
            table.id = 'data-table';
        }
    }
}

function updateDataCount(count) {
    const dataCount = document.getElementById('data-count');
    if (dataCount) {
        dataCount.textContent = `${count} records found`;
    }
}

function showLoadingState() {
    const tableContainer = document.getElementById('data-table-container');
    if (tableContainer) {
        tableContainer.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading filtered data...</p>
            </div>
        `;
    }
    
    // Disable filter buttons during loading
    const applyBtn = document.getElementById('apply-filters');
    const resetBtn = document.getElementById('reset-filters');
    
    if (applyBtn) applyBtn.disabled = true;
    if (resetBtn) resetBtn.disabled = true;
}

function hideLoadingState() {
    // Re-enable filter buttons
    const applyBtn = document.getElementById('apply-filters');
    const resetBtn = document.getElementById('reset-filters');
    
    if (applyBtn) applyBtn.disabled = false;
    if (resetBtn) resetBtn.disabled = false;
}

function showErrorState() {
    const tableContainer = document.getElementById('data-table-container');
    if (tableContainer) {
        tableContainer.innerHTML = `
            <div class="text-center text-danger">
                <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                <h4>Error Loading Data</h4>
                <p>There was an error loading the filtered data. Please try again.</p>
                <button class="btn btn-primary" onclick="applyFilters()">Retry</button>
            </div>
        `;
    }
    
    hideLoadingState();
}

// Utility function to format dates
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Utility function to format timestamps
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Function to handle table cell content formatting
function formatTableCell(content, columnName) {
    if (!content || content === 'NaN' || content === '') {
        return '<span class="text-muted">-</span>';
    }
    
    // Format specific column types
    if (columnName === 'timestamp') {
        return formatTimestamp(content);
    } else if (columnName === 'patient_link' && content !== '-') {
        return `<a href="${content}" target="_blank" class="btn btn-sm btn-outline-primary">View Patient</a>`;
    } else if (columnName === 'recommend_icu_move' || columnName === 'patient_moved_to_icu') {
        const value = content.toLowerCase();
        if (value === 'yes') {
            return '<span class="badge bg-success">Yes</span>';
        } else if (value === 'no') {
            return '<span class="badge bg-danger">No</span>';
        } else {
            return content;
        }
    } else if (columnName === 'intervention_status') {
        const value = content.toLowerCase();
        if (value === 'followed') {
            return '<span class="badge bg-success">Followed</span>';
        } else if (value === 'not followed') {
            return '<span class="badge bg-danger">Not Followed</span>';
        } else {
            return content;
        }
    }
    
    return content;
}

// Export functions for global access
window.applyFilters = applyFilters;
window.resetFilters = resetFilters;
window.formatDate = formatDate;
window.formatTimestamp = formatTimestamp;
window.formatTableCell = formatTableCell;
