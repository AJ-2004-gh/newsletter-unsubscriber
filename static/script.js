/**
 * Newsletter Unsubscriber - Client-side JavaScript with Multi-Account Support
 * Handles all UI interactions and API calls
 */

// Global state
let newsletters = [];
let selectedNewsletters = new Set();
let currentFilter = 'all';
let accounts = [];
let selectedAccount = null;
let inboxStats = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Newsletter Unsubscriber initialized - Multi-Account Edition');
    
    // Initialize Bootstrap tooltips
    initializeTooltips();
    
    // Load accounts first
    loadAccounts();
    
    // Fetch whitelist count
    fetchWhitelistCount();
    
    // Set up event listeners
    setupEventListeners();
    
    // Check for cached scan results
    loadCachedResults();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Fetch whitelist count
 */
async function fetchWhitelistCount() {
    try {
        const response = await fetch('/whitelist');
        const data = await response.json();
        if (data.success) {
            document.getElementById('whitelistedBadge').textContent = data.count;
        }
    } catch (error) {
        console.error('Error fetching whitelist:', error);
    }
}

/**
 * Set up all event listeners
 */
function setupEventListeners() {
    // Scan button
    document.getElementById('scanButton').addEventListener('click', handleScan);
    
    // Account selection
    document.getElementById('accountSelect').addEventListener('change', handleAccountChange);
    
    // Account management
    document.getElementById('addAccountBtn').addEventListener('click', handleAddAccount);
    
    // Checkbox handlers
    document.getElementById('selectAllCheckbox').addEventListener('change', handleSelectAll);
    document.getElementById('selectAllBtn').addEventListener('click', () => selectAll(true));
    document.getElementById('deselectAllBtn').addEventListener('click', () => selectAll(false));
    document.getElementById('selectAutoBtn').addEventListener('click', selectAutoOnly);
    
    // Action buttons
    document.getElementById('unsubscribeBtn').addEventListener('click', handleUnsubscribeClick);
    document.getElementById('whitelistBtn').addEventListener('click', handleWhitelistSelected);
    document.getElementById('confirmUnsubscribeBtn').addEventListener('click', handleConfirmUnsubscribe);
    
    // Filter tabs - prevent default Bootstrap behavior and use custom filtering
    document.querySelectorAll('#filterTabs button').forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Update active tab manually
            document.querySelectorAll('#filterTabs button').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Set current filter and apply
            currentFilter = this.id.replace('-tab', '');
            filterNewsletters();
        });
    });
}

/**
 * Load accounts from API
 */
async function loadAccounts() {
    try {
        const response = await fetch('/accounts');
        const data = await response.json();
        
        if (data.success) {
            accounts = data.accounts;
            updateAccountSelect();
            updateAccountsModal();
            
            if (accounts.length > 0) {
                selectedAccount = accounts[0];
                console.log(`Loaded ${accounts.length} account(s), selected: ${selectedAccount}`);
            } else {
                showToast('No accounts found. Please add a Gmail account.', 'info');
            }
        }
    } catch (error) {
        console.error('Error loading accounts:', error);
        showToast('Failed to load accounts', 'error');
    }
}

/**
 * Update account select dropdown
 */
function updateAccountSelect() {
    const select = document.getElementById('accountSelect');
    select.innerHTML = '';
    
    if (accounts.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No accounts - Click "Accounts" to add one';
        select.appendChild(option);
        select.disabled = true;
    } else {
        accounts.forEach(account => {
            const option = document.createElement('option');
            option.value = account;
            option.textContent = account;
            select.appendChild(option);
        });
        select.disabled = false;
        
        // Select the current account
        if (selectedAccount) {
            select.value = selectedAccount;
        }
    }
}

/**
 * Update accounts modal list
 */
function updateAccountsModal() {
    const list = document.getElementById('accountsList');
    list.innerHTML = '';
    
    if (accounts.length === 0) {
        list.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="fas fa-inbox fa-2x mb-2"></i>
                <div>No accounts added yet</div>
                <small>Add your first Gmail account below</small>
            </div>
        `;
    } else {
        accounts.forEach(account => {
            const item = document.createElement('div');
            item.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center');
            item.innerHTML = `
                <div>
                    <i class="fas fa-envelope me-2 text-primary"></i>
                    <strong>${account}</strong>
                </div>
                <button class="btn btn-sm btn-outline-danger" onclick="removeAccount('${account}')">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            list.appendChild(item);
        });
    }
}

/**
 * Handle account selection change
 */
function handleAccountChange(event) {
    selectedAccount = event.target.value;
    console.log(`Account changed to: ${selectedAccount}`);
    
    // Clear current results
    newsletters = [];
    selectedNewsletters.clear();
    document.getElementById('filterSection').style.display = 'none';
    document.getElementById('bulkActionBar').style.display = 'none';
    document.getElementById('statsCards').style.display = 'none';
    document.getElementById('inboxStats').style.display = 'none';
}

/**
 * Handle add account button click
 */
async function handleAddAccount() {
    const emailInput = document.getElementById('newAccountEmail');
    const email = emailInput.value.trim();
    
    if (!email) {
        showToast('Please enter an email address', 'error');
        return;
    }
    
    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showToast('Please enter a valid email address', 'error');
        return;
    }
    
    // Show progress
    document.getElementById('addAccountProgress').style.display = 'block';
    document.getElementById('addAccountError').style.display = 'none';
    document.getElementById('addAccountBtn').disabled = true;
    
    try {
        const response = await fetch('/accounts/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`Successfully added ${data.email}`, 'success');
            emailInput.value = '';
            
            // Reload accounts
            await loadAccounts();
            
            // Select the new account
            selectedAccount = data.email;
            document.getElementById('accountSelect').value = selectedAccount;
            
        } else {
            throw new Error(data.message || 'Failed to add account');
        }
    } catch (error) {
        console.error('Error adding account:', error);
        document.getElementById('addAccountError').style.display = 'block';
        document.getElementById('addAccountErrorText').textContent = error.message;
    } finally {
        document.getElementById('addAccountProgress').style.display = 'none';
        document.getElementById('addAccountBtn').disabled = false;
    }
}

/**
 * Remove account
 */
async function removeAccount(email) {
    if (!confirm(`Remove authentication for ${email}?`)) {
        return;
    }
    
    try {
        const response = await fetch('/accounts/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`Removed ${email}`, 'success');
            
            // Reload accounts
            await loadAccounts();
            
            // If removed account was selected, select first available
            if (selectedAccount === email) {
                selectedAccount = accounts.length > 0 ? accounts[0] : null;
                if (selectedAccount) {
                    document.getElementById('accountSelect').value = selectedAccount;
                }
            }
        } else {
            throw new Error(data.message || 'Failed to remove account');
        }
    } catch (error) {
        console.error('Error removing account:', error);
        showToast('Failed to remove account', 'error');
    }
}

/**
 * Handle scan button click
 */
async function handleScan() {
    const scanButton = document.getElementById('scanButton');
    const scanProgressSection = document.getElementById('scanProgressSection');
    const scanProgressText = document.getElementById('scanProgressText');
    const scanLimitSelect = document.getElementById('scanLimitSelect');
    
    // Check if account is selected
    if (!selectedAccount) {
        showToast('Please select or add a Gmail account first', 'error');
        return;
    }
    
    // Get scan limit
    const scanLimit = scanLimitSelect.value;
    
    // Disable button and show loading
    scanButton.disabled = true;
    scanProgressSection.style.display = 'block';
    scanProgressText.textContent = `Scanning ${selectedAccount}... this may take a minute`;
    
    // Hide previous results
    document.getElementById('filterSection').style.display = 'none';
    document.getElementById('bulkActionBar').style.display = 'none';
    document.getElementById('statsCards').style.display = 'none';
    
    try {
        const url = `/scan?account=${encodeURIComponent(selectedAccount)}&max_results=${scanLimit}`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            newsletters = data.newsletters;
            selectedAccount = data.account; // Update with verified account
            inboxStats = data.inbox_stats;
            
            // Cache results for 5 minutes
            cacheResults(newsletters);
            
            // Update inbox stats display
            if (inboxStats) {
                document.getElementById('statsTotal').textContent = inboxStats.total_emails.toLocaleString();
                document.getElementById('statsEstimated').textContent = inboxStats.estimated_newsletters.toLocaleString();
                document.getElementById('statsRecommended').textContent = inboxStats.recommended_limit;
                document.getElementById('inboxStats').style.display = 'block';
            }
            
            // Update UI
            updateStatsCards(data);
            populateTable(newsletters);
            
            // Apply current filter (default is 'all')
            filterNewsletters();
            
            // Show results or empty state
            if (newsletters.length === 0) {
                showEmptyState();
            } else {
                document.getElementById('filterSection').style.display = 'block';
                document.getElementById('bulkActionBar').style.display = 'block';
            }
            
            // Hide scan progress
            scanProgressSection.style.display = 'none';
            
            showToast(`Scan complete! Found ${data.total_found} newsletters (scanned ${data.total_scanned} emails)`, 'success');
        } else {
            throw new Error(data.message || 'Scan failed');
        }
    } catch (error) {
        console.error('Scan error:', error);
        showToast(error.message || 'Failed to scan. Please check Gmail authentication.', 'error');
        scanProgressSection.style.display = 'none';
    } finally {
        scanButton.disabled = false;
    }
}

/**
 * Update stats cards
 */
function updateStatsCards(data) {
    const autoCount = (data.categories.easy || 0) + (data.categories.medium || 0);
    const manualCount = data.categories.hard || 0;
    const whitelistedCount = data.categories.whitelisted || 0;
    
    // Safely update elements (check if they exist)
    const totalCountEl = document.getElementById('totalCount');
    const autoCountEl = document.getElementById('autoCount');
    const manualCountEl = document.getElementById('manualCount');
    
    if (totalCountEl) totalCountEl.textContent = data.count;
    if (autoCountEl) autoCountEl.textContent = autoCount;
    if (manualCountEl) manualCountEl.textContent = manualCount;
    
    // Update filter badges
    const allBadgeEl = document.getElementById('allBadge');
    const autoBadgeEl = document.getElementById('autoBadge');
    const manualBadgeEl = document.getElementById('manualBadge');
    const whitelistedBadgeEl = document.getElementById('whitelistedBadge');
    
    if (allBadgeEl) allBadgeEl.textContent = data.count;
    if (autoBadgeEl) autoBadgeEl.textContent = autoCount;
    if (manualBadgeEl) manualBadgeEl.textContent = manualCount;
    if (whitelistedBadgeEl) whitelistedBadgeEl.textContent = whitelistedCount;
    
    // Show stats cards
    const statsCardsEl = document.getElementById('statsCards');
    if (statsCardsEl) statsCardsEl.style.display = 'flex';
}

/**
 * Populate table with newsletters
 */
function populateTable(newslettersToShow) {
    const tbody = document.getElementById('newslettersTableBody');
    tbody.innerHTML = '';
    
    newslettersToShow.forEach(newsletter => {
        const row = createNewsletterRow(newsletter);
        tbody.appendChild(row);
    });
    
    // Show/hide empty state
    document.getElementById('emptyState').style.display = newslettersToShow.length === 0 ? 'block' : 'none';
}

/**
 * Create a table row for a newsletter
 */
function createNewsletterRow(newsletter) {
    const row = document.createElement('tr');
    row.dataset.id = newsletter.id;
    row.dataset.difficulty = newsletter.difficulty;
    row.dataset.whitelisted = newsletter.whitelisted || false;
    
    // Apply row styling based on category
    if (newsletter.whitelisted || newsletter.difficulty === 'whitelisted') {
        row.classList.add('table-secondary');
    } else if (newsletter.difficulty === 'easy') {
        row.classList.add('table-success');
    } else if (newsletter.difficulty === 'hard') {
        row.classList.add('table-warning');
    }
    
    // Checkbox
    const checkboxCell = document.createElement('td');
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.classList.add('form-check-input', 'newsletter-checkbox');
    checkbox.dataset.id = newsletter.id;
    checkbox.addEventListener('change', handleCheckboxChange);
    checkboxCell.appendChild(checkbox);
    
    // Sender name
    const senderCell = document.createElement('td');
    senderCell.textContent = newsletter.sender_name || 'Unknown';
    
    // Email (hidden on mobile)
    const emailCell = document.createElement('td');
    emailCell.classList.add('d-none', 'd-md-table-cell');
    emailCell.textContent = newsletter.sender_email || '';
    
    // Subject (hidden on mobile, truncated on desktop)
    const subjectCell = document.createElement('td');
    subjectCell.classList.add('d-none', 'd-lg-table-cell');
    const subject = newsletter.subject || 'No subject';
    if (subject.length > 50) {
        subjectCell.textContent = subject.substring(0, 50) + '...';
        subjectCell.title = subject;
        subjectCell.setAttribute('data-bs-toggle', 'tooltip');
    } else {
        subjectCell.textContent = subject;
    }
    
    // Category badge
    const categoryCell = document.createElement('td');
    const badge = createCategoryBadge(newsletter.difficulty);
    categoryCell.appendChild(badge);
    
    // Date (hidden on mobile)
    const dateCell = document.createElement('td');
    dateCell.classList.add('d-none', 'd-md-table-cell');
    dateCell.textContent = formatDate(newsletter.date);
    
    // Actions
    const actionsCell = document.createElement('td');
    actionsCell.appendChild(createWhitelistButton(newsletter));
    if (newsletter.difficulty === 'hard' && newsletter.unsubscribe_link) {
        actionsCell.appendChild(createOpenLinkButton(newsletter));
    }
    
    row.appendChild(checkboxCell);
    row.appendChild(senderCell);
    row.appendChild(emailCell);
    row.appendChild(subjectCell);
    row.appendChild(categoryCell);
    row.appendChild(dateCell);
    row.appendChild(actionsCell);
    
    return row;
}

/**
 * Create category badge
 */
function createCategoryBadge(difficulty) {
    const badge = document.createElement('span');
    badge.classList.add('badge');
    
    if (difficulty === 'easy') {
        badge.classList.add('bg-success');
        badge.innerHTML = '🟢 Auto';
        badge.title = 'Can be automatically unsubscribed';
    } else if (difficulty === 'medium') {
        badge.classList.add('bg-info');
        badge.innerHTML = '🔵 Auto';
        badge.title = 'Can be automatically unsubscribed with browser automation';
    } else if (difficulty === 'hard') {
        badge.classList.add('bg-warning');
        badge.innerHTML = '🟡 Manual';
        badge.title = 'Requires manual action (login, CAPTCHA, etc.)';
    } else {
        badge.classList.add('bg-secondary');
        badge.innerHTML = '⚪ Unknown';
    }
    
    badge.setAttribute('data-bs-toggle', 'tooltip');
    return badge;
}

/**
 * Create whitelist button
 */
function createWhitelistButton(newsletter) {
    const btn = document.createElement('button');
    btn.classList.add('btn', 'btn-sm', 'btn-outline-warning', 'me-1');
    btn.innerHTML = '<i class="far fa-star"></i>';
    btn.title = 'Add to whitelist (won\'t be scanned again)';
    btn.setAttribute('data-bs-toggle', 'tooltip');
    btn.addEventListener('click', () => toggleWhitelist(newsletter, btn));
    return btn;
}

/**
 * Create open link button for manual newsletters
 */
function createOpenLinkButton(newsletter) {
    const btn = document.createElement('button');
    btn.classList.add('btn', 'btn-sm', 'btn-outline-primary');
    btn.innerHTML = '<i class="fas fa-external-link-alt"></i>';
    btn.title = `Open ${newsletter.sender_name}'s unsubscribe page`;
    btn.setAttribute('data-bs-toggle', 'tooltip');
    btn.addEventListener('click', () => openUnsubscribeLink(newsletter));
    return btn;
}

/**
 * Toggle whitelist status
 */
async function toggleWhitelist(newsletter, button) {
    try {
        const response = await fetch('/whitelist/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sender_email: newsletter.sender_email,
                sender_name: newsletter.sender_name
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update button state
            button.innerHTML = '<i class="fas fa-star"></i>';
            button.classList.remove('btn-outline-warning');
            button.classList.add('btn-warning');
            
            // Gray out row
            const row = button.closest('tr');
            row.classList.add('table-secondary');
            
            showToast('Added to whitelist', 'success');
            fetchWhitelistCount();
        }
    } catch (error) {
        console.error('Whitelist error:', error);
        showToast('Failed to add to whitelist', 'error');
    }
}

/**
 * Open unsubscribe link in new tab
 */
function openUnsubscribeLink(newsletter) {
    if (newsletter.unsubscribe_link) {
        window.open(newsletter.unsubscribe_link, '_blank');
        showToast(`Opened unsubscribe page for ${newsletter.sender_name}`, 'info');
    }
}

/**
 * Handle checkbox change
 */
function handleCheckboxChange(event) {
    const id = event.target.dataset.id;
    if (event.target.checked) {
        selectedNewsletters.add(id);
    } else {
        selectedNewsletters.delete(id);
    }
    updateSelectionUI();
}

/**
 * Handle select all checkbox
 */
function handleSelectAll(event) {
    selectAll(event.target.checked);
}

/**
 * Select/deselect all visible newsletters
 */
function selectAll(checked) {
    const checkboxes = document.querySelectorAll('.newsletter-checkbox');
    checkboxes.forEach(checkbox => {
        const row = checkbox.closest('tr');
        if (row.style.display !== 'none') {
            checkbox.checked = checked;
            if (checked) {
                selectedNewsletters.add(checkbox.dataset.id);
            } else {
                selectedNewsletters.delete(checkbox.dataset.id);
            }
        }
    });
    updateSelectionUI();
}

/**
 * Select only auto-unsubscribe newsletters
 */
function selectAutoOnly() {
    selectedNewsletters.clear();
    const checkboxes = document.querySelectorAll('.newsletter-checkbox');
    checkboxes.forEach(checkbox => {
        const row = checkbox.closest('tr');
        const difficulty = row.dataset.difficulty;
        if ((difficulty === 'easy' || difficulty === 'medium') && row.style.display !== 'none') {
            checkbox.checked = true;
            selectedNewsletters.add(checkbox.dataset.id);
        } else {
            checkbox.checked = false;
        }
    });
    updateSelectionUI();
}

/**
 * Update selection UI
 */
function updateSelectionUI() {
    const count = selectedNewsletters.size;
    document.getElementById('selectionCount').textContent = `${count} selected`;
    document.getElementById('unsubscribeBtn').disabled = count === 0;
    document.getElementById('whitelistBtn').disabled = count === 0;
}

/**
 * Filter newsletters based on current tab
 */
function filterNewsletters() {
    const rows = document.querySelectorAll('#newslettersTableBody tr');
    console.log(`Filtering with: ${currentFilter}, Total rows: ${rows.length}`);
    
    let visibleCount = 0;
    
    rows.forEach(row => {
        const difficulty = row.dataset.difficulty;
        const isWhitelisted = row.dataset.whitelisted === 'true' || difficulty === 'whitelisted';
        let show = false;
        
        switch(currentFilter) {
            case 'all':
                show = true;
                break;
            case 'auto':
                show = !isWhitelisted && (difficulty === 'easy' || difficulty === 'medium');
                break;
            case 'manual':
                show = !isWhitelisted && difficulty === 'hard';
                break;
            case 'whitelisted':
                show = isWhitelisted;
                break;
        }
        
        if (show) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    console.log(`Visible rows after filter: ${visibleCount}`);
    
    // Show/hide empty state
    const emptyState = document.getElementById('emptyState');
    if (visibleCount === 0) {
        emptyState.style.display = 'block';
        emptyState.innerHTML = `
            <i class="fas fa-filter fa-3x text-muted mb-3"></i>
            <h4>No newsletters in this category</h4>
            <p class="text-muted">Try selecting a different filter</p>
        `;
    } else {
        emptyState.style.display = 'none';
    }
    
    updateSelectionUI();
}

/**
 * Handle unsubscribe button click
 */
function handleUnsubscribeClick() {
    if (selectedNewsletters.size === 0) return;
    
    // Count auto vs manual
    const selected = Array.from(selectedNewsletters).map(id => 
        newsletters.find(n => n.id === id)
    );
    
    const autoCount = selected.filter(n => n.difficulty === 'easy' || n.difficulty === 'medium').length;
    const manualCount = selected.filter(n => n.difficulty === 'hard').length;
    
    // Show confirmation modal
    document.getElementById('confirmCount').textContent = selectedNewsletters.size;
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    confirmModal.show();
}

/**
 * Handle confirmed unsubscribe
 */
async function handleConfirmUnsubscribe() {
    // Close confirmation modal
    bootstrap.Modal.getInstance(document.getElementById('confirmModal')).hide();
    
    // Show results modal with progress
    const resultsModal = new bootstrap.Modal(document.getElementById('resultsModal'));
    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('successSection').style.display = 'none';
    document.getElementById('manualSection').style.display = 'none';
    document.getElementById('failedSection').style.display = 'none';
    resultsModal.show();
    
    // Get selected newsletters
    const selected = Array.from(selectedNewsletters).map(id => 
        newsletters.find(n => n.id === id)
    );
    
    try {
        const response = await fetch('/unsubscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                account: selectedAccount,
                newsletters: selected 
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayResults(data);
        } else {
            throw new Error(data.message || 'Unsubscribe failed');
        }
    } catch (error) {
        console.error('Unsubscribe error:', error);
        document.getElementById('progressSection').style.display = 'none';
        showToast('Failed to unsubscribe. Please try again.', 'error');
        resultsModal.hide();
    }
}

/**
 * Display unsubscribe results
 */
function displayResults(data) {
    document.getElementById('progressSection').style.display = 'none';
    
    // Success section
    if (data.auto_success > 0) {
        document.getElementById('successSection').style.display = 'block';
        document.getElementById('successCount').textContent = data.auto_success;
        
        // Remove successful newsletters from table
        data.details.filter(d => d.status === 'auto_success').forEach(detail => {
            const row = document.querySelector(`tr[data-id="${detail.id}"]`);
            if (row) row.remove();
            selectedNewsletters.delete(detail.id);
        });
    }
    
    // Manual action section
    if (data.manual_required > 0) {
        document.getElementById('manualSection').style.display = 'block';
        document.getElementById('manualResultCount').textContent = data.manual_required;
        
        const manualList = document.getElementById('manualList');
        manualList.innerHTML = '';
        
        data.details.filter(d => d.status === 'manual_required').forEach(detail => {
            const item = document.createElement('div');
            item.classList.add('list-group-item');
            item.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${detail.sender_name}</strong>
                        <br><small class="text-muted">${detail.message}</small>
                    </div>
                    <button class="btn btn-sm btn-primary" onclick="window.open('${detail.unsubscribe_url}', '_blank')">
                        <i class="fas fa-external-link-alt"></i> Open Link
                    </button>
                </div>
            `;
            manualList.appendChild(item);
        });
    }
    
    // Failed section
    if (data.failed > 0) {
        document.getElementById('failedSection').style.display = 'block';
        document.getElementById('failedCount').textContent = data.failed;
        
        const failedList = document.getElementById('failedList');
        failedList.innerHTML = '';
        
        data.details.filter(d => d.status === 'failed').forEach(detail => {
            const item = document.createElement('div');
            item.classList.add('list-group-item');
            item.innerHTML = `
                <strong>${detail.sender_name}</strong>
                <br><small class="text-danger">${detail.message}</small>
            `;
            failedList.appendChild(item);
        });
    }
    
    // Update stats
    updateStatsAfterUnsubscribe();
    updateSelectionUI();
    
    // Show summary toast
    showToast(`✓ ${data.auto_success} unsubscribed, ⚠ ${data.manual_required} need manual action, ✗ ${data.failed} failed`, 'info', 5000);
}

/**
 * Handle whitelist selected
 */
async function handleWhitelistSelected() {
    const selected = Array.from(selectedNewsletters).map(id => 
        newsletters.find(n => n.id === id)
    );
    
    for (const newsletter of selected) {
        try {
            await fetch('/whitelist/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sender_email: newsletter.sender_email,
                    sender_name: newsletter.sender_name
                })
            });
        } catch (error) {
            console.error('Whitelist error:', error);
        }
    }
    
    showToast(`Added ${selected.length} newsletters to whitelist`, 'success');
    fetchWhitelistCount();
    selectedNewsletters.clear();
    updateSelectionUI();
}

/**
 * Update stats after unsubscribe
 */
function updateStatsAfterUnsubscribe() {
    const remainingCount = document.querySelectorAll('#newslettersTableBody tr').length;
    document.getElementById('totalCount').textContent = remainingCount;
    document.getElementById('allBadge').textContent = remainingCount;
    
    if (remainingCount === 0) {
        showEmptyState();
    }
}

/**
 * Show empty state
 */
function showEmptyState() {
    document.getElementById('emptyState').style.display = 'block';
    document.getElementById('emptyState').innerHTML = `
        <i class="fas fa-check-circle fa-3x text-success mb-3"></i>
        <h4>All done! No newsletters remaining</h4>
        <p class="text-muted">Your inbox is clean 🎉</p>
    `;
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info', duration = 3000) {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.classList.add('toast', 'align-items-center', 'border-0');
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    let bgClass = 'bg-info';
    let icon = 'fa-info-circle';
    
    if (type === 'success') {
        bgClass = 'bg-success';
        icon = 'fa-check-circle';
    } else if (type === 'error') {
        bgClass = 'bg-danger';
        icon = 'fa-times-circle';
    }
    
    toast.classList.add(bgClass, 'text-white');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas ${icon} me-2"></i>${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: duration });
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

/**
 * Create toast container
 */
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.classList.add('toast-container', 'position-fixed', 'top-0', 'end-0', 'p-3');
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

/**
 * Format date
 */
function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

/**
 * Cache scan results
 */
function cacheResults(data) {
    const cache = {
        data: data,
        timestamp: Date.now()
    };
    localStorage.setItem('scanResults', JSON.stringify(cache));
}

/**
 * Load cached results
 */
function loadCachedResults() {
    const cached = localStorage.getItem('scanResults');
    if (cached) {
        const cache = JSON.parse(cached);
        const age = Date.now() - cache.timestamp;
        
        // Cache valid for 5 minutes
        if (age < 5 * 60 * 1000) {
            newsletters = cache.data;
            if (newsletters.length > 0) {
                // Restore UI from cache
                console.log('Loaded cached results');
            }
        }
    }
}
