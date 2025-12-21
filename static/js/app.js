const API_BASE = '';
const WS_BASE = `ws://${window.location.host}/ws`;

class App {
    constructor() {
        this.dom = {};
        this.state = {
            backends: [],
            stats: {},
            tasks: { pending: [], dispatched: [] }
        };
        this.ws = null;
        this.reconnectTimer = null;
    }

    init() {
        this.cacheDOM();
        this.bindEvents();
        this.connectWebSocket();
        this.fetchInitialData();

        // Tab handling
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.currentTarget));
        });
    }

    cacheDOM() {
        this.dom = {
            stats: {
                total: document.getElementById('stat-total'),
                healthy: document.getElementById('stat-healthy'),
                idle: document.getElementById('stat-idle'),
                pending: document.getElementById('stat-pending'),
                dispatched: document.getElementById('stat-dispatched')
            },
            lists: {
                backend: document.getElementById('backend-list'),
                pendingTasks: document.getElementById('pending-tasks'),
                dispatchedTasks: document.getElementById('dispatched-tasks')
            },
            kong: {
                status: document.getElementById('kong-status'),
                statusText: document.getElementById('kong-status-text'),
                lists: {
                    services: document.getElementById('kong-services-list'),
                    consumers: document.getElementById('kong-consumers-list')
                },
                stats: {
                    services: document.getElementById('kong-services-count'),
                    routes: document.getElementById('kong-routes-count'),
                    plugins: document.getElementById('kong-plugins-count'),
                    consumers: document.getElementById('kong-consumers-count')
                }
            }
        };
    }

    bindEvents() {
        // Strategy buttons
        document.getElementById('strategy-selector')?.addEventListener('click', (e) => {
            if (e.target.matches('.strategy-btn')) {
                this.updateStrategy(e.target.dataset.strategy);
            }
        });
    }

    connectWebSocket() {
        this.ws = new WebSocket(WS_BASE);

        this.ws.onopen = () => {
            console.log('Connected to WebSocket');
            this.showToast('WebSocket Connected', 'success');
            if (this.reconnectTimer) clearInterval(this.reconnectTimer);
        };

        this.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                this.handleWebSocketMessage(msg);
            } catch (e) {
                console.error('Invalid WS message:', e);
            }
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected, retrying in 3s...');
            this.reconnectTimer = setTimeout(() => this.connectWebSocket(), 3000);
        };
    }

    handleWebSocketMessage(msg) {
        switch (msg.type) {
            case 'stats_update':
                this.updateStats(msg.data);
                break;
            case 'backend_update':
                this.refreshBackends(); // Or update specific backend if payload has details
                break;
            case 'queue_update':
                this.updateQueue(msg.data);
                break;
            case 'task_update':
                // Optional: show specific task notification
                break;
        }
    }

    async fetchInitialData() {
        try {
            const [stats, tasks, backends] = await Promise.all([
                fetch(`${API_BASE}/lb/stats`).then(r => r.json()),
                fetch(`${API_BASE}/lb/tasks`).then(r => r.json()),
                fetch(`${API_BASE}/lb/backends`).then(r => r.json())
            ]);

            this.updateStats(stats);
            this.updateQueue(tasks.queue_status); // Assuming queue_status structure
            this.renderBackends(stats.backends); // stats endpoint usually includes backends

            // If backend list is separate
            // this.renderBackends(backends); 

            // Load Kong data if tab is active (or just load it)
            this.refreshKong();
        } catch (e) {
            console.error('Failed to fetch initial data:', e);
            this.showToast('Failed to load data', 'error');
        }
    }

    updateStats(stats) {
        if (!stats) return;
        this.dom.stats.total.textContent = stats.total_backends ?? '-';
        this.dom.stats.healthy.textContent = stats.healthy_backends ?? '-';
        this.dom.stats.idle.textContent = stats.idle_backends ?? '-';
        this.dom.stats.pending.textContent = stats.queue_status?.pending ?? '-';
        this.dom.stats.dispatched.textContent = stats.queue_status?.dispatched ?? '-';

        if (stats.backends) {
            this.renderBackends(stats.backends);
        }
    }

    updateQueue(queueData) {
        // Since we might just get counts or full lists depending on implementation
        // For now assuming we might need to re-fetch full lists if we only get counts
        // Or the WS sends the full top 10 list.
        // Let's assume we re-fetch tasks for list accuracy for now
        this.refreshTasks();
    }

    async refreshTasks() {
        try {
            const tasks = await fetch(`${API_BASE}/lb/tasks`).then(r => r.json());
            this.renderTaskList(this.dom.lists.pendingTasks, tasks.pending, 'pending');
        } catch (e) {
            console.error(e);
        }
    }

    async refreshBackends() {
        try {
            const stats = await fetch(`${API_BASE}/lb/stats`).then(r => r.json());
            this.renderBackends(stats.backends);
        } catch (e) {
            console.error(e);
        }
    }

    renderBackends(backends) {
        if (!backends || !this.dom.lists.backend) return;

        this.dom.lists.backend.innerHTML = backends.map(b => `
            <div class="list-item">
                <div class="flex items-center gap-3">
                    <div class="status-dot" style="background-color: ${b.status === 'healthy' ? 'var(--success)' : 'var(--danger)'}"></div>
                    <div>
                        <div class="font-semibold">${b.name}</div>
                        <div class="text-xs text-secondary">${b.base_url}</div>
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <div class="text-sm">Queue: ${b.queue_pending + b.queue_running}</div>
                    <div class="flex gap-2">
                        <button class="btn btn-secondary text-xs" onclick="app.toggleBackend('${b.name}', ${!b.enabled})">
                            ${b.enabled ? 'Pause' : 'Resume'}
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderTaskList(container, tasks, type) {
        if (!container) return;
        if (!tasks || tasks.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-secondary">No tasks</div>';
            return;
        }

        container.innerHTML = tasks.slice(0, 10).map(t => `
            <div class="list-item">
                <div>
                    <div class="font-mono text-sm">${t.id.substring(0, 8)}...</div>
                    <div class="text-xs text-secondary">${new Date(t.created_at).toLocaleTimeString()}</div>
                </div>
                <span class="badge ${type}">${type}</span>
            </div>
        `).join('');
    }

    async toggleBackend(name, enabled) {
        try {
            await fetch(`${API_BASE}/lb/backends/${name}/${enabled ? 'enable' : 'disable'}`, { method: 'POST' });
            this.showToast(`Backend ${enabled ? 'enabled' : 'disabled'}`, 'success');
            // Optimistic update
            this.refreshBackends();
        } catch (e) {
            this.showToast('Action failed', 'error');
        }
    }

    switchTab(btn) {
        // UI logic to switch tabs
        const targetId = btn.dataset.tab;

        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
        document.getElementById(`tab-${targetId}`).style.display = 'block';

        if (targetId === 'kong') {
            this.refreshKong();
        }
    }

    // --- Kong Methods ---

    async refreshKong() {
        try {
            const status = await fetch(`${API_BASE}/kong/status`).then(r => r.json());
            this.updateKongStatus(status);

            if (status.connected) {
                // Fetch all data
                const [services, routes, consumers, plugins] = await Promise.all([
                    fetch(`${API_BASE}/kong/services`).then(r => r.json()),
                    fetch(`${API_BASE}/kong/routes`).then(r => r.json()),
                    fetch(`${API_BASE}/kong/consumers`).then(r => r.json()),
                    fetch(`${API_BASE}/kong/plugins`).then(r => r.json())
                ]);

                // Update Stats
                this.dom.kong.stats.services.textContent = services.data.length;
                this.dom.kong.stats.routes.textContent = routes.data.length;
                this.dom.kong.stats.consumers.textContent = consumers.data.length;
                this.dom.kong.stats.plugins.textContent = plugins.data.length;

                // Render Master-Detail Views
                this.renderKongServices(services.data, routes.data);
                this.renderKongConsumers(consumers.data, plugins.data);

                // Update Selects
                this.updateSelect('route-service-select', services.data, 'name', 'id');
                this.updateSelect('plugin-service-select', services.data, 'name', 'id');
                this.updateSelect('plugin-consumer-select', consumers.data, 'username', 'id', true); // true for optional empty option

            }
        } catch (e) {
            console.error('Failed to refresh Kong:', e);
            this.updateKongStatus({ connected: false, error: e.message });
        }
    }

    updateKongStatus(status) {
        const dot = this.dom.kong.status.querySelector('.status-dot');
        const text = this.dom.kong.statusText;

        if (status.connected) {
            dot.style.backgroundColor = 'var(--success)';
            text.textContent = `Connected (${status.version})`;
            this.dom.kong.status.parentElement.parentElement.classList.remove('border-red-500'); // if we had error class
        } else {
            dot.style.backgroundColor = 'var(--danger)';
            text.textContent = `Disconnected: ${status.error || 'Unknown error'}`;
        }
    }

    renderKongServices(services, routes) {
        const container = this.dom.kong.lists.services;
        if (!services || services.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-secondary">No services found</div>';
            return;
        }

        container.innerHTML = services.map(service => {
            // Find routes for this service (assuming route.service.id matches service.id)
            const serviceRoutes = routes.filter(r => r.service && r.service.id === service.id);

            const routesHtml = serviceRoutes.map(route => `
                <div class="nested-item">
                     <div class="flex items-center justify-between">
                        <div>
                            <div class="font-mono text-xs text-accent-primary">🛤️ ${(route.paths || []).join(', ')}</div>
                            <div class="text-xs text-secondary">${route.name || route.id}</div>
                        </div>
                        <button class="btn btn-secondary text-xs" onclick="app.deleteKongItem('route', '${route.id}')">Delete</button>
                     </div>
                </div>
            `).join('');

            return `
            <div class="list-item master-item">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="font-semibold text-lg">🔌 ${service.name}</div>
                        <div class="text-xs text-secondary">${service.host}:${service.port}${service.path || ''}</div>
                    </div>
                    <div class="flex gap-2">
                         <button class="btn btn-sm btn-primary" onclick="app.openRouteForm('${service.id}', '${service.name}')">+ Route</button>
                         <button class="btn btn-sm btn-secondary" onclick="app.deleteKongItem('service', '${service.id}')">Delete</button>
                    </div>
                </div>
                <div class="nested-container">
                    ${routesHtml}
                </div>
            </div>
            `;
        }).join('');
    }

    renderKongConsumers(consumers, plugins) {
        const container = this.dom.kong.lists.consumers;
        if (!consumers || consumers.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-secondary">No consumers found</div>';
            return;
        }

        container.innerHTML = consumers.map(consumer => {
            // Find plugins for this consumer (assuming plugin.consumer.id matches consumer.id)
            // Note: Plugin structure usually has consumer: { id: ... } if it's consumer-scoped.
            const consumerPlugins = plugins.filter(p => p.consumer && p.consumer.id === consumer.id);

            const pluginsHtml = consumerPlugins.map(plugin => `
                 <div class="nested-item">
                     <div class="flex items-center justify-between">
                        <div>
                            <div class="font-mono text-xs text-accent-secondary">🔌 ${plugin.name}</div>
                            <div class="text-xs text-secondary">${plugin.enabled ? 'Enabled' : 'Disabled'}</div>
                        </div>
                        <button class="btn btn-secondary text-xs" onclick="app.deleteKongItem('plugin', '${plugin.id}')">Delete</button>
                     </div>
                </div>
            `).join('');

            return `
            <div class="list-item master-item">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="font-semibold text-lg">👤 ${consumer.username || consumer.custom_id}</div>
                        <div class="text-xs text-secondary">${consumer.id}</div>
                    </div>
                    <div class="flex gap-2">
                        <button class="btn btn-sm btn-primary" onclick="app.openPluginForm('${consumer.id}', '${consumer.username}')">+ Plugin</button>
                        <button class="btn btn-sm btn-secondary" onclick="app.deleteKongItem('consumer', '${consumer.id}')">Delete</button>
                    </div>
                </div>
                 <div class="nested-container">
                    ${pluginsHtml}
                </div>
            </div>
            `;
        }).join('');
    }

    async refreshKongServices() {
        const data = await fetch(`${API_BASE}/kong/services`).then(r => r.json());
        this.dom.kong.stats.services.textContent = data.data.length;
        this.renderKongList(this.dom.kong.lists.services, data.data, 'service');
        this.updateSelect('route-service-select', data.data, 'name', 'id');
        this.updateSelect('plugin-service-select', data.data, 'name', 'id');
    }

    async refreshKongRoutes() {
        const data = await fetch(`${API_BASE}/kong/routes`).then(r => r.json());
        this.dom.kong.stats.routes.textContent = data.data.length;
        this.renderKongList(this.dom.kong.lists.routes, data.data, 'route');
    }

    async refreshKongConsumers() {
        const data = await fetch(`${API_BASE}/kong/consumers`).then(r => r.json());
        this.dom.kong.stats.consumers.textContent = data.data.length;
        this.renderKongList(this.dom.kong.lists.consumers, data.data, 'consumer');
        this.updateSelect('plugin-consumer-select', data.data, 'username', 'id', true);
    }

    async refreshKongPlugins() {
        const data = await fetch(`${API_BASE}/kong/plugins`).then(r => r.json());
        this.dom.kong.stats.plugins.textContent = data.data.length;
        this.renderKongList(this.dom.kong.lists.plugins, data.data, 'plugin');
    }

    renderKongList(container, items, type) {
        if (!items || items.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-secondary">No items found</div>';
            return;
        }

        container.innerHTML = items.map(item => {
            let title = item.name || item.username || item.id;
            let subtitle = '';

            if (type === 'service') subtitle = `${item.host}:${item.port}${item.path || ''}`;
            if (type === 'route') subtitle = (item.paths || []).join(', ');
            if (type === 'plugin') {
                title = item.name;
                subtitle = item.enabled ? 'Enabled' : 'Disabled';
            }

            return `
            <div class="list-item">
                <div>
                    <div class="font-semibold">${title}</div>
                    <div class="text-xs text-secondary">${subtitle}</div>
                </div>
                <button class="btn btn-secondary text-xs" onclick="app.deleteKongItem('${type}', '${item.id}')">Delete</button>
            </div>
            `;
        }).join('');
    }

    // --- Form Openers ---
    openServiceForm() {
        this.toggleForm('service-form');
    }

    openConsumerForm() {
        this.toggleForm('consumer-form');
    }

    openRouteForm(serviceId, serviceName) {
        if (serviceId) document.getElementById('route-service-select').value = serviceId;
        document.getElementById('route-service-name-disp').textContent = serviceName || 'New Route';
        document.getElementById('route-form').classList.remove('hidden');
    }

    openPluginForm(consumerId, consumerName) {
        if (consumerId) document.getElementById('plugin-consumer-select').value = consumerId;
        document.getElementById('plugin-consumer-name-disp').textContent = consumerName || 'Global/Service';
        document.getElementById('plugin-form').classList.remove('hidden');
    }

    async createService() {
        const name = document.getElementById('service-name').value;
        const url = document.getElementById('service-url').value;
        if (!name || !url) return this.showToast('Name and URL required', 'error');

        try {
            await fetch(`${API_BASE}/kong/services`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, url })
            });
            this.showToast('Service created', 'success');
            this.toggleForm('service-form');
            this.refreshKong();
        } catch (e) {
            this.showToast('Failed to create service', 'error');
        }
    }

    async createRoute() {
        const serviceId = document.getElementById('route-service-select').value;
        if (!serviceId) return this.showToast('Service is required', 'error');
        const name = document.getElementById('route-name').value;
        const path = document.getElementById('route-path').value;

        try {
            await fetch(`${API_BASE}/kong/services/${serviceId}/routes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, paths: [path] })
            });
            this.showToast('Route created', 'success');
            this.toggleForm('route-form');
            // Removed refreshKongRoutes as we refresh all
            this.refreshKong();
        } catch (e) {
            this.showToast('Failed to create route', 'error');
        }
    }

    async createConsumer() {
        const username = document.getElementById('consumer-username').value;
        try {
            await fetch(`${API_BASE}/kong/consumers`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username })
            });
            this.showToast('Consumer created', 'success');
            this.toggleForm('consumer-form');
            this.refreshKongConsumers();
        } catch (e) {
            this.showToast('Failed to create consumer', 'error');
        }
    }

    async createPlugin() {
        const name = document.getElementById('plugin-name').value;
        const consumerId = document.getElementById('plugin-consumer-select').value;
        const serviceId = document.getElementById('plugin-service-select').value;

        let url = `${API_BASE}/kong/plugins`;
        // If associated with a consumer, we might want to POST to /consumers/:id/plugins 
        // OR /plugins with consumer_id in body. 
        // Kong Admin API supports POST /plugins with consumer={id: ...} or service={id: ...} in body
        // or POST /consumers/:id/plugins or POST /services/:id/plugins

        let body = { name };
        if (consumerId) body.consumer = { id: consumerId };
        if (serviceId) body.service = { id: serviceId };

        try {
            await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            this.showToast('Plugin created', 'success');
            this.toggleForm('plugin-form');
            this.refreshKong();
        } catch (e) {
            console.error(e);
            this.showToast('Failed to create plugin', 'error');
        }
    }

    // Generic helpers
    toggleForm(id) {
        const el = document.getElementById(id);
        if (el.classList.contains('hidden')) {
            el.classList.remove('hidden');
        } else {
            el.classList.add('hidden');
        }
    }

    updateSelect(id, items, textKey, valueKey, allowEmpty = false) {
        const select = document.getElementById(id);
        if (!select) return;
        let html = allowEmpty ? '<option value="">(None)</option>' : '';
        html += items.map(i => `<option value="${i[valueKey]}">${i[textKey] || i.username || i.id}</option>`).join('');
        select.innerHTML = html;
    }

    async deleteKongItem(type, id) {
        if (!confirm('Are you sure?')) return;
        try {
            const endpoint = type === 'plugin' ? 'plugins' : `${type}s`; // crude pluralization
            await fetch(`${API_BASE}/kong/${endpoint}/${id}`, { method: 'DELETE' });
            this.showToast('Deleted', 'success');
            this.refreshKong();
        } catch (e) {
            this.showToast('Delete failed', 'error');
        }
    }

    showToast(msg, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = msg;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
}

const app = new App();
document.addEventListener('DOMContentLoaded', () => app.init());
// Expose for inline handlers
window.app = app;
