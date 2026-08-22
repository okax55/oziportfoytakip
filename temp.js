
        const API_URL = 'http://127.0.0.1:5000/api';

        function toggleTheme() {
            const html = document.documentElement;
            html.classList.toggle('dark');
            const isDark = html.classList.contains('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            document.getElementById('themeIcon').className = isDark ? 'fa-solid fa-moon text-lg' : 'fa-solid fa-sun text-lg';
            
            // Re-render charts for theme colors
            Chart.defaults.color = isDark ? '#94a3b8' : '#64748b';
            if (document.getElementById('view-monthly').classList.contains('block')) renderMonthlyChart();
            if (document.getElementById('view-compare').classList.contains('block')) renderCompareView();
        }
        
        // Initial load
        if (localStorage.getItem('theme') === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
            document.addEventListener("DOMContentLoaded", () => {
                const i = document.getElementById('themeIcon');
                if(i) i.className = 'fa-solid fa-moon text-lg';
            });
        } else {
            document.documentElement.classList.remove('dark');
            document.addEventListener("DOMContentLoaded", () => {
                const i = document.getElementById('themeIcon');
                if(i) i.className = 'fa-solid fa-sun text-lg';
            });
        }

        const chartColors = ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#ef4444", "#06b6d4"];

        let appState = {
            portfoliosData: {}, // { "2026-08": [ {id, name, assets} ] }
            benchmarksData: {}, // { "2026-08": { "ALTIN": 2500, "XU100.IS": 10000 } }
            frozenMonths: {},   // { "2026-08": false }
            activeBenchmarks: [],
            
            // UI State
            currentViewMonth: "",
            currentPortfolioId: "",
            monthlyChartType: 'line',
            deleteQueue: { type: null, pId: null, aId: null }
        };

        let mChart = null;
        let cChart = null;

        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = 'Inter';

        window.onload = initApp;

        async function initApp() {
            try {
                const res = await fetch(`${API_URL}/load`);
                const data = await res.json();
                
                const d = new Date();
                const actualMonth = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2, '0')}`;
                
                if (data.status === "empty" || !data.data.portfoliosData) {
                    appState.portfoliosData[actualMonth] = [];
                    appState.benchmarksData[actualMonth] = {};
                    appState.frozenMonths[actualMonth] = false;
                } else {
                    appState = { ...appState, ...data.data };
                    
                    const months = Object.keys(appState.portfoliosData).sort();
                    if(months.length > 0) {
                        const lastMonth = months[months.length - 1];
                        if (lastMonth < actualMonth) {
                            appState.frozenMonths[lastMonth] = true;
                            appState.portfoliosData[actualMonth] = JSON.parse(JSON.stringify(appState.portfoliosData[lastMonth]));
                            appState.benchmarksData[actualMonth] = JSON.parse(JSON.stringify(appState.benchmarksData[lastMonth] || {}));
                            appState.frozenMonths[actualMonth] = false;
                            await saveState();
                        }
                    } else {
                        appState.portfoliosData[actualMonth] = [];
                        appState.benchmarksData[actualMonth] = {};
                        appState.frozenMonths[actualMonth] = false;
                    }
                }
                
                appState.currentViewMonth = actualMonth;
                
                if (!appState.activeBenchmarks || appState.activeBenchmarks.length === 0) {
                    appState.activeBenchmarks = ['ALTIN', 'XU100.IS'];
                }

                if(appState.portfoliosData[appState.currentViewMonth].length > 0){
                    appState.currentPortfolioId = appState.portfoliosData[appState.currentViewMonth][0].id;
                }
                
                initDropdowns();
                updateAllViews();
                
                // İlk açılışta güncel ay donuk değilse fiyatları çek
                if(!appState.frozenMonths[appState.currentViewMonth]) {
                    refreshPrices();
                }
                
            } catch (e) {
                console.error(e);
                alert("Backend'e ulaşılamadı. Lütfen 'python server.py' komutunun çalıştığından emin olun.");
            }
        }

        async function saveState() {
            // UI statelerini ayırıp kaydetmek daha temiz olabilir ama şimdilik bütünü atıyoruz
            try {
                await fetch(`${API_URL}/save`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(appState)
                });
            } catch(e) { console.error("Kayıt hatası", e); }
        }

        async function refreshPrices() {
            if (appState.frozenMonths[appState.currentViewMonth]) {
                alert("Bu ay kilitli! Fiyatları canlı çekmek için önce sağ üstten kilidi açın.");
                return;
            }
            
            const btn = document.getElementById('btnRefresh');
            if(btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i>Güncelleniyor...';
            
            try {
                let symbols = new Set(['ALTIN', 'XU100.IS', 'NASDAQ', 'SP500']);
                const ports = appState.portfoliosData[appState.currentViewMonth] || [];
                ports.forEach(p => p.assets.forEach(a => {
                    let fetchName = a.name.includes('.') ? a.name : a.name + '.IS';
                    symbols.add(fetchName);
                }));
                
                const res = await fetch(`${API_URL}/prices`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({symbols: Array.from(symbols)})
                });
                
                const data = await res.json();
                if (data.status === "success") {
                    const prices = data.prices;
                    
                    const todayStr = new Date().toISOString().split('T')[0];
                    ports.forEach(p => {
                        p.assets.forEach(a => {
                            let fetchName = a.name.includes('.') ? a.name : a.name + '.IS';
                            if (prices[fetchName]) {
                                a.price = prices[fetchName];
                            }
                        });
                        const stats = getPortfolioStats(p);
                        if (!p.dailyHistory) p.dailyHistory = {};
                        p.dailyHistory[todayStr] = stats.totalChange;
                    });
                    
                    if (!appState.benchmarksData[appState.currentViewMonth]) appState.benchmarksData[appState.currentViewMonth] = {};
                    ['ALTIN', 'XU100.IS', 'NASDAQ', 'SP500'].forEach(bk => {
                        if (prices[bk]) {
                            appState.benchmarksData[appState.currentViewMonth][bk] = prices[bk];
                            if (!appState.benchmarksHistory) appState.benchmarksHistory = {};
                            if (!appState.benchmarksHistory[bk]) appState.benchmarksHistory[bk] = {};
                            appState.benchmarksHistory[bk][todayStr] = prices[bk];
                        }
                    });
                    
                    await saveState();
                    updateAllViews();
                }
            } catch (e) {
                console.error(e);
            }
            
            if(btn) btn.innerHTML = '<i class="fa-solid fa-bolt mr-2"></i>Canlı Fiyatları Çek';
        }

        async function fetchHistory() {
            if (appState.frozenMonths[appState.currentViewMonth]) {
                alert("Bu ay kilitli! Geçmiş verileri çekmek için önce kilidi açın.");
                return;
            }
            
            const btn = document.getElementById('btnFetchHistory');
            if(btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i>Çekiliyor...';
            
            try {
                let symbols = new Set(['ALTIN', 'XU100.IS', 'NASDAQ', 'SP500']);
                const ports = appState.portfoliosData[appState.currentViewMonth] || [];
                ports.forEach(p => p.assets.forEach(a => {
                    let fetchName = a.name.includes('.') ? a.name : a.name + '.IS';
                    symbols.add(fetchName);
                }));
                
                const res = await fetch(`${API_URL}/history`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({symbols: Array.from(symbols), period: "1mo"})
                });
                
                const data = await res.json();
                if (data.status === "success" && data.history) {
                    const history = data.history;
                    
                    if (!appState.benchmarksHistory) appState.benchmarksHistory = {};
                    ['ALTIN', 'XU100.IS', 'NASDAQ', 'SP500'].forEach(bk => {
                        if (history[bk]) {
                            appState.benchmarksHistory[bk] = Object.assign(appState.benchmarksHistory[bk] || {}, history[bk]);
                        }
                    });
                    
                    ports.forEach(p => {
                        if (!p.dailyHistory) p.dailyHistory = {};
                        
                        const [year, month] = appState.currentViewMonth.split('-');
                        let daysInMonth = new Date(year, month, 0).getDate();
                        const today = new Date();
                        if (today.getFullYear() === parseInt(year) && (today.getMonth() + 1) === parseInt(month)) {
                            daysInMonth = today.getDate();
                        }
                        
                        for (let d = 1; d <= daysInMonth; d++) {
                            const dateStr = `${year}-${month}-${String(d).padStart(2, '0')}`;
                            let totalValue = 0;
                            let totalCost = 0;
                            let hasAnyData = false;
                            
                            p.assets.forEach(a => {
                                let fetchName = a.name.includes('.') ? a.name : a.name + '.IS';
                                let assetHist = history[fetchName] || {};
                                
                                let price = assetHist[dateStr];
                                if (!price) {
                                    for (let offset = 1; offset <= 7; offset++) {
                                        const prevD = new Date(year, parseInt(month)-1, d - offset);
                                        const prevStr = `${prevD.getFullYear()}-${String(prevD.getMonth()+1).padStart(2, '0')}-${String(prevD.getDate()).padStart(2, '0')}`;
                                        if (assetHist[prevStr]) {
                                            price = assetHist[prevStr];
                                            break;
                                        }
                                    }
                                }
                                
                                if (price) {
                                    totalValue += (a.amount * price);
                                    totalCost += (a.amount * a.cost);
                                    hasAnyData = true;
                                } else {
                                    totalValue += (a.amount * (a.price || a.cost));
                                    totalCost += (a.amount * a.cost);
                                }
                            });
                            
                            if (hasAnyData && totalCost > 0) {
                                p.dailyHistory[dateStr] = ((totalValue - totalCost) / totalCost) * 100;
                            }
                        }
                    });
                    
                    await saveState();
                    updateAllViews();
                }
            } catch (e) {
                console.error(e);
                alert("Geçmiş veri çekilirken hata oluştu.");
            }
            
            if(btn) btn.innerHTML = '<i class="fa-solid fa-clock-rotate-left mr-2"></i>Geçmiş Verileri Çek';
        }

        async function toggleLock() {
            appState.frozenMonths[appState.currentViewMonth] = !appState.frozenMonths[appState.currentViewMonth];
            await saveState();
            updateLockUI();
        }

        function updateLockUI() {
            const isFrozen = appState.frozenMonths[appState.currentViewMonth];
            const btn = document.getElementById('btnToggleLock');
            const icon = document.getElementById('lockIcon');
            const txt = document.getElementById('lockText');
            
            if (isFrozen) {
                btn.className = "px-4 py-2 text-sm font-medium rounded-lg border transition-colors shadow-sm flex items-center bg-white dark:bg-slate-800 border-rose-500/50 text-rose-400 hover:bg-slate-700";
                icon.className = "fa-solid fa-lock mr-2";
                txt.textContent = "Kilitli (Salt Okunur)";
            } else {
                btn.className = "px-4 py-2 text-sm font-medium rounded-lg border transition-colors shadow-sm flex items-center bg-white dark:bg-slate-800 border-emerald-500/50 text-emerald-400 hover:bg-slate-700";
                icon.className = "fa-solid fa-lock-open mr-2";
                txt.textContent = "Açık (Düzenlenebilir)";
            }
        }

        function switchTab(tabId) {
            const tabs = ['monthly', 'compare', 'manage'];
            tabs.forEach(t => {
                const btn = document.getElementById(`tab-${t}`);
                const view = document.getElementById(`view-${t}`);
                if (t === tabId) {
                    btn.classList.add('tab-active');
                    btn.classList.remove('text-slate-500', 'dark:text-slate-400', 'border-transparent');
                    view.classList.remove('hidden');
                } else {
                    btn.classList.remove('tab-active');
                    btn.classList.add('text-slate-500', 'dark:text-slate-400', 'border-transparent');
                    view.classList.add('hidden');
                }
            });
        }

        function initDropdowns() {
            const mSelector = document.getElementById('monthSelector');
            mSelector.innerHTML = '';
            
            const trMonths = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
            
            const months = Object.keys(appState.portfoliosData).sort().reverse();
            months.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m; 
                
                const [yyyy, mm] = m.split('-');
                opt.textContent = `${trMonths[parseInt(mm) - 1]} ${yyyy}`;
                
                if(m === appState.currentViewMonth) opt.selected = true;
                mSelector.appendChild(opt);
            });
            mSelector.onchange = (e) => { 
                appState.currentViewMonth = e.target.value; 
                // Portföy id'si yeni ayda yoksa ilkini seç
                const ports = appState.portfoliosData[appState.currentViewMonth];
                if(ports && ports.length > 0) {
                    if(!ports.find(p=>p.id === appState.currentPortfolioId)) {
                        appState.currentPortfolioId = ports[0].id;
                    }
                }
                updateAllViews(); 
            };
            
            updatePortfolioDropdown();
        }

        function updatePortfolioDropdown() {
            const pSelector = document.getElementById('portfolioSelector');
            pSelector.innerHTML = '';
            const currentPorts = appState.portfoliosData[appState.currentViewMonth] || [];
            
            currentPorts.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id; opt.textContent = p.name;
                if(p.id === appState.currentPortfolioId) opt.selected = true;
                pSelector.appendChild(opt);
            });
            pSelector.onchange = (e) => { appState.currentPortfolioId = e.target.value; renderMonthlyView(); };
        }

        function toggleChartType(type) {
            appState.monthlyChartType = type;
            const btnLine = document.getElementById('btnLineChart');
            const btnBar = document.getElementById('btnBarChart');
            if (type === 'line') {
                btnLine.className = "px-4 py-1.5 text-sm font-medium rounded-md bg-brand-500 text-white shadow transition-colors";
                btnBar.className = "px-4 py-1.5 text-sm font-medium rounded-md text-slate-500 dark:text-slate-400 hover:text-white transition-colors";
            } else {
                btnBar.className = "px-4 py-1.5 text-sm font-medium rounded-md bg-brand-500 text-white shadow transition-colors";
                btnLine.className = "px-4 py-1.5 text-sm font-medium rounded-md text-slate-500 dark:text-slate-400 hover:text-white transition-colors";
            }
            renderMonthlyChart();
        }

        function getPortfolioStats(portfolio) {
            let totalCost = 0; let totalValue = 0;
            if(!portfolio || !portfolio.assets) return { totalCost:0, totalValue:0, totalChange:0, assetsWithStats:[] };

            portfolio.assets.forEach(a => {
                totalCost += (a.amount * a.cost);
                totalValue += (a.amount * (a.price || a.cost)); // Fiyat yoksa maliyet üzerinden
            });

            let assetsWithStats = portfolio.assets.map(a => {
                let p = a.price || a.cost;
                let val = a.amount * p;
                let cst = a.amount * a.cost;
                let change = cst > 0 ? ((val - cst) / cst) * 100 : 0;
                let weight = totalValue > 0 ? (val / totalValue) * 100 : 0;
                return { ...a, price: p, currentValue: val, totalCost: cst, change, weight };
            });

            assetsWithStats.sort((a,b) => b.weight - a.weight);
            let totalChange = totalCost > 0 ? ((totalValue - totalCost) / totalCost) * 100 : 0;

            return { totalCost, totalValue, totalChange, assetsWithStats };
        }

        function formatMoney(amount) {
            return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(amount);
        }

        function renderMonthlyView() {
            updateLockUI();
            renderMonthlyChart();
            renderMonthlyTable();
        }

        const monthNames = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];

        function getTradingDays(yearMonth) {
            const [year, month] = yearMonth.split('-').map(Number);
            const today = new Date();
            let daysInMonth = new Date(year, month, 0).getDate();
            
            if (today.getFullYear() === year && (today.getMonth() + 1) === month) {
                daysInMonth = today.getDate();
            }

            const labels = [];
            for (let i = 1; i <= daysInMonth; i++) {
                const d = new Date(year, month - 1, i);
                const dayOfWeek = d.getDay();
                if (dayOfWeek !== 0 && dayOfWeek !== 6) {
                    labels.push(`${i} ${monthNames[month - 1]}`);
                }
            }
            if (labels.length === 0) labels.push(`1 ${monthNames[month - 1]}`);
            return labels;
        }

        function generateHistoryPath(portfolio, yearMonth, labels, finalChange, finalProfit) {
            if (labels.length === 0) return { data: [], profitData: [] };
            if (labels.length === 1) return { data: [finalChange], profitData: [finalProfit] };
            
            const [year, month] = yearMonth.split('-');
            
            let knownPoints = [];
            
            for (let i = 0; i < labels.length; i++) {
                const dayMatch = labels[i].match(/\d+/);
                if (!dayMatch) continue;
                const day = parseInt(dayMatch[0]);
                const dateStr = `${year}-${month}-${String(day).padStart(2, '0')}`;
                
                if (portfolio.dailyHistory && portfolio.dailyHistory[dateStr] !== undefined) {
                    const dataPoint = portfolio.dailyHistory[dateStr];
                    const percentVal = typeof dataPoint === 'object' ? dataPoint.percent : dataPoint;
                    const profitVal = typeof dataPoint === 'object' ? dataPoint.profit : 0;
                    
                    const existingIdx = knownPoints.findIndex(k => k.index === i);
                    if (existingIdx >= 0) {
                        knownPoints[existingIdx].percent = percentVal;
                        knownPoints[existingIdx].profit = profitVal;
                    } else {
                        knownPoints.push({index: i, percent: percentVal, profit: profitVal});
                    }
                }
            }
            
            const lastIdx = labels.length - 1;
            const existingLastIdx = knownPoints.findIndex(k => k.index === lastIdx);
            if (existingLastIdx >= 0) {
                knownPoints[existingLastIdx].percent = finalChange;
                knownPoints[existingLastIdx].profit = finalProfit;
            } else {
                knownPoints.push({index: lastIdx, percent: finalChange, profit: finalProfit});
            }
            
            knownPoints.sort((a, b) => a.index - b.index);
            
            let data = [];
            let profitData = [];
            for (let i = 0; i < labels.length; i++) {
                let left = knownPoints[0];
                for (let kp of knownPoints) {
                    if (kp.index <= i) left = kp;
                }
                let right = knownPoints[knownPoints.length - 1];
                for (let kp of knownPoints) {
                    if (kp.index >= i) {
                        right = kp;
                        break;
                    }
                }
                
                if (left.index === right.index) {
                    data.push(left.percent);
                    profitData.push(left.profit);
                } else {
                    const ratio = (i - left.index) / (right.index - left.index);
                    const val = left.percent + ratio * (right.percent - left.percent);
                    const prof = left.profit + ratio * (right.profit - left.profit);
                    data.push(val);
                    profitData.push(prof);
                }
            }
            return { data, profitData };
        }

        function renderMonthlyChart() {
            const ctx = document.getElementById('monthlyChart').getContext('2d');
            const ports = appState.portfoliosData[appState.currentViewMonth] || [];
            const portfolio = ports.find(p => p.id === appState.currentPortfolioId);
            const stats = getPortfolioStats(portfolio);
            
            if (mChart) mChart.destroy();
            if (!portfolio) return;

            const isLine = appState.monthlyChartType === 'line';

            let chartLabels = [];
            let chartData = [];
            let profitData = [];
            let bgColors = [];
            let borderColors = [];

            if (isLine) {
                chartLabels = getTradingDays(appState.currentViewMonth);
                const pathObj = generateHistoryPath(portfolio, appState.currentViewMonth, chartLabels, stats.totalChange, stats.totalValue - stats.totalCost);
                chartData = pathObj.data;
                profitData = pathObj.profitData;
                
                let lineColor = '#3b82f6'; // Mavi
                if (stats.totalChange > 0.05) lineColor = '#10b981'; // Yeşil
                else if (stats.totalChange < -0.05) lineColor = '#ef4444'; // Kırmızı

                borderColors = lineColor;
                const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                gradient.addColorStop(0, lineColor);
                gradient.addColorStop(1, 'rgba(15, 23, 42, 0)');
                bgColors = gradient;
            } else {
                stats.assetsWithStats.forEach(a => {
                    chartLabels.push(a.name);
                    chartData.push(a.change.toFixed(2));
                    profitData.push(a.currentValue - a.totalCost);
                    let color = a.change >= 0 ? '#10b981' : '#ef4444';
                    bgColors.push(color);
                    borderColors.push(color);
                });
            }

            mChart = new Chart(ctx, {
                type: appState.monthlyChartType,
                data: {
                    labels: chartLabels,
                    datasets: [{
                        label: isLine ? portfolio.name + ' Kümülatif Getiri (%)' : 'Hisse Getirisi (%)',
                        data: chartData,
                        customProfits: profitData,
                        borderColor: borderColors,
                        backgroundColor: bgColors,
                        borderWidth: isLine ? 2 : 0,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        pointBackgroundColor: borderColors,
                        fill: true,
                        borderRadius: isLine ? 0 : 4,
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: { 
                        legend: { display: false }, 
                        tooltip: { 
                            enabled: true,
                            backgroundColor: 'rgba(15, 23, 42, 0.9)',
                            titleColor: '#fff',
                            bodyColor: '#cbd5e1',
                            borderColor: '#334155',
                            borderWidth: 1,
                            callbacks: {
                                title: function(context) {
                                    if (appState.monthlyChartType === 'line') {
                                        const label = context[0].label;
                                        const dayMatch = label.match(/\d+/);
                                        if (dayMatch) {
                                            const day = dayMatch[0];
                                            const [year, month] = appState.currentViewMonth.split('-');
                                            const trMonths = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
                                            return `${day} ${trMonths[parseInt(month) - 1]} ${year} Durumu`;
                                        }
                                    }
                                    return context[0].label + ' Durumu';
                                },
                                label: function(context) {
                                    const val = context.parsed.y;
                                    const sign = val > 0 ? '+' : '';
                                    const lines = [`Kümülatif Getiri: ${sign}%${val.toFixed(2)}`];
                                    
                                    if (appState.monthlyChartType === 'line' && context.dataIndex > 0) {
                                        const prevVal = context.dataset.data[context.dataIndex - 1];
                                        const diff = val - prevVal;
                                        const diffSign = diff > 0 ? '+' : '';
                                        lines.push(`Günlük Getiri: ${diffSign}%${diff.toFixed(2)}`);
                                    }
                                    
                                    return lines;
                                }
                            }
                        } 
                    },
                    scales: {
                        x: { display: true, grid: { color: '#334155', drawBorder: false }, ticks: { color: '#94a3b8', maxTicksLimit: 15 } },
                        y: { grid: { color: '#334155', drawBorder: false }, ticks: { callback: v => '%' + v, color: '#94a3b8' } }
                    }
                }
            });
        }

        function renderMonthlyTable() {
            const tbody = document.getElementById('assetsTableBody');
            const ports = appState.portfoliosData[appState.currentViewMonth] || [];
            const portfolio = ports.find(p => p.id === appState.currentPortfolioId);
            const stats = getPortfolioStats(portfolio);
            
            tbody.innerHTML = '';
            
            if(stats.assetsWithStats.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-500">Bu portföyde henüz hisse yok.</td></tr>`;
            }

            stats.assetsWithStats.forEach(asset => {
                const changeClass = asset.change >= 0 ? 'text-emerald-400' : 'text-rose-400';
                const changeIcon = asset.change >= 0 ? '<i class="fa-solid fa-arrow-trend-up mr-1"></i>' : '<i class="fa-solid fa-arrow-trend-down mr-1"></i>';
                const changeSign = asset.change > 0 ? '+' : '';
                const profitTL = asset.currentValue - asset.totalCost;
                const profitSign = profitTL > 0 ? '+' : '';

                tbody.innerHTML += `
                    <tr class="hover:bg-slate-700/30 transition-colors">
                        <td class="px-6 py-4 font-medium text-white flex items-center">
                            <div class="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold mr-3 border border-slate-300 dark:border-slate-600">
                                ${asset.name.substring(0,2)}
                            </div>
                            ${asset.name}
                        </td>
                        <td class="px-6 py-4 text-right">${asset.amount}</td>
                        <td class="px-6 py-4 text-right">${formatMoney(asset.cost)}</td>
                        <td class="px-6 py-4 text-right font-medium text-white">${formatMoney(asset.price)}</td>
                        <td class="px-6 py-4 text-center">
                            <div class="flex items-center justify-center">
                                <span class="mr-2 w-10 text-right">${asset.weight.toFixed(1)}%</span>
                                <div class="w-16 bg-slate-700 rounded-full h-1.5">
                                    <div class="bg-brand-500 h-1.5 rounded-full" style="width: ${asset.weight}%"></div>
                                </div>
                            </div>
                        </td>
                        <td class="px-6 py-4 text-right font-medium ${changeClass}">${profitSign}${formatMoney(profitTL)}</td>
                        <td class="px-6 py-4 text-right font-bold ${changeClass}">
                            ${changeIcon} ${changeSign}${asset.change.toFixed(2)}%
                        </td>
                    </tr>
                `;
            });

            document.getElementById('totalCost').textContent = formatMoney(stats.totalCost);
            document.getElementById('totalValue').textContent = formatMoney(stats.totalValue);
            
            const tEl = document.getElementById('totalChange');
            const totalProfitTL = stats.totalValue - stats.totalCost;
            const tSign = stats.totalChange > 0 ? '+' : '';
            const tColor = stats.totalChange >= 0 ? 'text-emerald-400' : 'text-rose-400';
            const pEl = document.getElementById('totalProfitTL');
            if (pEl) pEl.innerHTML = `<span class="${tColor}">${tSign}${formatMoney(totalProfitTL)}</span>`;
            
            tEl.innerHTML = `<span class="${tColor}">
                ${tSign}${stats.totalChange.toFixed(2)}%
            </span>`;
        }

        function toggleCompareChartType(type) {
            appState.compareChartType = type;
            const btnLine = document.getElementById('btnCompareLineChart');
            const btnBar = document.getElementById('btnCompareBarChart');
            if (type === 'line') {
                btnLine.className = "px-4 py-1.5 text-sm font-medium rounded-md bg-brand-500 text-white shadow transition-colors";
                btnBar.className = "px-4 py-1.5 text-sm font-medium rounded-md text-slate-500 dark:text-slate-400 hover:text-white transition-colors";
            } else {
                btnBar.className = "px-4 py-1.5 text-sm font-medium rounded-md bg-brand-500 text-white shadow transition-colors";
                btnLine.className = "px-4 py-1.5 text-sm font-medium rounded-md text-slate-500 dark:text-slate-400 hover:text-white transition-colors";
            }
            renderCompareView();
        }

        function renderCompareView() {
            if (!appState.compareChartType) appState.compareChartType = 'line';
            
            const container = document.getElementById('benchmarkToggles');
            container.innerHTML = '';
            
            const benchmarkColors = { "ALTIN": "#eab308", "XU100.IS": "#ef4444", "NASDAQ": "#3b82f6", "SP500": "#a855f7" };
            const benchmarkNames = { "ALTIN": "Altın (Gram)", "XU100.IS": "BIST 100", "NASDAQ": "NASDAQ", "SP500": "S&P 500" };
            
            const currentPorts = appState.portfoliosData[appState.currentViewMonth] || [];
            
            const allOptions = {};
            currentPorts.forEach(p => {
                allOptions[p.id] = { name: p.name, color: p.color, type: 'port', pData: p };
            });
            ['ALTIN', 'XU100.IS', 'NASDAQ', 'SP500'].forEach(b => {
                allOptions[b] = { name: benchmarkNames[b], color: benchmarkColors[b], type: 'bench' };
            });

            for (const [key, item] of Object.entries(allOptions)) {
                const isChecked = appState.activeBenchmarks.includes(key);
                const label = document.createElement('label');
                label.className = `cursor-pointer flex items-center px-4 py-2 rounded-full border transition-all select-none ${isChecked ? 'bg-slate-700 border-slate-500 text-white' : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:border-slate-500'}`;
                label.innerHTML = `
                    <input type="checkbox" value="${key}" class="hidden" ${isChecked ? 'checked' : ''} onchange="toggleBenchmark(this)">
                    <span class="w-3 h-3 rounded-full mr-2 inline-block" style="background-color: ${item.color}"></span>
                    <span class="text-sm font-medium">${item.name}</span>
                `;
                container.appendChild(label);
            }

            const ctx = document.getElementById('compareChart').getContext('2d');
            if (cChart) cChart.destroy();

            const datasets = [];
            const statsContainer = document.getElementById('comparisonStats');
            statsContainer.innerHTML = '';
            
            const isLine = appState.compareChartType === 'line';
            let chartLabels = [];
            if (isLine) {
                chartLabels = getTradingDays(appState.currentViewMonth);
            } else {
                appState.activeBenchmarks.forEach(key => {
                    const item = allOptions[key];
                    if(item) chartLabels.push(item.name);
                });
            }
            
            const barData = [];
            const barBackgroundColors = [];

            appState.activeBenchmarks.forEach(key => {
                const item = allOptions[key];
                if(!item) return;

                let dataPoints = [];
                let finalReturn = 0;
                
                if (isLine) {
                    const [year, month] = appState.currentViewMonth.split('-');
                    let firstBaseValue = null;
                    
                    chartLabels.forEach((label, i) => {
                        const dayMatch = label.match(/\d+/);
                        if (!dayMatch) return;
                        const dateStr = `${year}-${month}-${String(dayMatch[0]).padStart(2, '0')}`;
                        
                        if (item.type === 'bench') {
                            const val = (appState.benchmarksHistory && appState.benchmarksHistory[key]) ? appState.benchmarksHistory[key][dateStr] : undefined;
                            if (val !== undefined) {
                                if (firstBaseValue === null) firstBaseValue = val;
                                const ret = firstBaseValue > 0 ? ((val - firstBaseValue) / firstBaseValue) * 100 : 0;
                                dataPoints.push(ret);
                                finalReturn = ret;
                            } else {
                                dataPoints.push(dataPoints.length > 0 ? dataPoints[dataPoints.length - 1] : 0);
                            }
                        } else {
                            let pRet = 0;
                            if (item.pData.dailyHistory && item.pData.dailyHistory[dateStr] !== undefined) {
                                const dp = item.pData.dailyHistory[dateStr];
                                pRet = typeof dp === 'object' ? dp.percent : dp;
                            } else if (dataPoints.length > 0) {
                                pRet = dataPoints[dataPoints.length - 1];
                            }
                            dataPoints.push(pRet);
                            finalReturn = pRet;
                        }
                    });
                    
                    datasets.push({
                        label: item.name,
                        data: dataPoints,
                        borderColor: item.color,
                        backgroundColor: item.color,
                        borderWidth: 2,
                        pointRadius: 3,
                        tension: 0.3
                    });
                } else {
                    if (item.type === 'bench') {
                        const [year, month] = appState.currentViewMonth.split('-');
                        let firstVal = null, lastVal = null;
                        if (appState.benchmarksHistory && appState.benchmarksHistory[key]) {
                            const hist = appState.benchmarksHistory[key];
                            const days = Object.keys(hist).filter(d => d.startsWith(`${year}-${month}-`)).sort();
                            if (days.length > 0) {
                                firstVal = hist[days[0]];
                                lastVal = hist[days[days.length - 1]];
                            }
                        }
                        if (firstVal && firstVal > 0) {
                            finalReturn = ((lastVal - firstVal) / firstVal) * 100;
                        }
                    } else {
                        const stats = getPortfolioStats(item.pData);
                        finalReturn = stats.totalChange;
                    }
                    barData.push(finalReturn);
                    barBackgroundColors.push(item.color);
                }

                const statClass = finalReturn >= 0 ? 'text-emerald-400' : 'text-rose-400';
                statsContainer.innerHTML += `
                    <div class="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow flex flex-col justify-between">
                        <div class="flex items-center mb-2">
                            <span class="w-3 h-3 rounded-full mr-2" style="background-color: ${item.color}"></span>
                            <span class="text-sm text-slate-700 dark:text-slate-300 font-medium truncate">${item.name}</span>
                        </div>
                        <div class="text-2xl font-bold ${statClass}">${finalReturn > 0 ? '+' : ''}${finalReturn.toFixed(2)}%</div>
                        <div class="text-xs text-slate-500 mt-1">Aylık Getiri</div>
                    </div>
                `;
            });
            
            if (!isLine) {
                datasets.push({
                    label: 'Getiri (%)',
                    data: barData,
                    backgroundColor: barBackgroundColors,
                    borderWidth: 0,
                    borderRadius: 4
                });
            }

            cChart = new Chart(ctx, {
                type: isLine ? 'line' : 'bar',
                data: {
                    labels: chartLabels,
                    datasets: datasets
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { display: isLine },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.9)',
                            titleColor: '#fff',
                            bodyColor: '#cbd5e1',
                            borderColor: '#334155',
                            borderWidth: 1,
                            callbacks: {
                                title: function(context) {
                                    if (isLine) {
                                        const label = context[0].label;
                                        const dayMatch = label.match(/\d+/);
                                        if (dayMatch) {
                                            const day = dayMatch[0];
                                            const [year, month] = appState.currentViewMonth.split('-');
                                            const trMonths = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
                                            return `${day} ${trMonths[parseInt(month) - 1]} ${year} Durumu`;
                                        }
                                    }
                                    return context[0].label;
                                },
                                label: function(context) {
                                    const val = context.parsed.y;
                                    const sign = val > 0 ? '+' : '';
                                    return `${context.dataset.label || 'Getiri'}: ${sign}%${val.toFixed(2)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: { grid: { color: '#334155', drawBorder: false }, ticks: { color: '#94a3b8' } },
                        y: { grid: { color: '#334155', drawBorder: false }, ticks: { color: '#94a3b8' } }
                    }
                }
            });
        }

        window.toggleBenchmark = async function(checkbox) {
            const val = checkbox.value;
            if (checkbox.checked && !appState.activeBenchmarks.includes(val)) {
                appState.activeBenchmarks.push(val);
            } else {
                appState.activeBenchmarks = appState.activeBenchmarks.filter(b => b !== val);
            }
            await saveState();
            renderCompareView();
        };

        function renderManagementView() {
            const container = document.getElementById('portfoliosContainer');
            container.innerHTML = '';
            
            const isFrozen = appState.frozenMonths[appState.currentViewMonth];
            const ports = appState.portfoliosData[appState.currentViewMonth] || [];

            ports.forEach(p => {
                let trs = '';
                if(p.assets.length === 0) {
                    trs = `<tr><td colspan="4" class="py-4 text-center text-slate-500 text-sm">Varlık bulunamadı.</td></tr>`;
                } else {
                    p.assets.forEach(a => {
                        trs += `
                            <tr class="hover:bg-slate-700/30">
                                <td class="py-2 font-medium text-white">${a.name}</td>
                                <td class="py-2 text-right">${a.amount}</td>
                                <td class="py-2 text-right">${a.cost.toFixed(2)} ₺</td>
                                <td class="py-2 text-right">${(a.price || a.cost).toFixed(2)} ₺</td>
                                <td class="py-2 text-right">
                                    <button onclick="confirmDeleteAsset('${p.id}', '${a.id}')" class="${isFrozen ? 'hidden' : ''} text-rose-400 hover:text-rose-300 p-1"><i class="fa-solid fa-xmark"></i></button>
                                </td>
                            </tr>
                        `;
                    });
                }

                container.innerHTML += `
                    <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-lg overflow-hidden flex flex-col">
                        <div class="p-4 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 flex justify-between items-center">
                            <div class="flex items-center gap-2">
                                <span class="w-3 h-3 rounded-full" style="background-color: ${p.color}"></span>
                                <h3 class="text-lg font-bold text-slate-900 dark:text-white">${p.name}</h3>
                            </div>
                            <div class="flex gap-2 ${isFrozen ? 'hidden' : ''}">
                                <button onclick="openAssetModal('${p.id}')" class="text-sm bg-brand-500/20 text-brand-400 hover:bg-brand-500 hover:text-white px-3 py-1.5 rounded transition-colors" title="Hisse Ekle"><i class="fa-solid fa-plus"></i></button>
                                <button onclick="confirmDeletePortfolio('${p.id}')" class="text-sm bg-rose-500/20 text-rose-400 hover:bg-rose-500 hover:text-white px-3 py-1.5 rounded transition-colors" title="Portföyü Sil"><i class="fa-solid fa-trash"></i></button>
                            </div>
                        </div>
                        <div class="p-4 flex-grow overflow-x-auto">
                            <table class="w-full text-sm text-left text-slate-700 dark:text-slate-300 min-w-[250px]">
                                <thead class="text-xs text-slate-500 uppercase">
                                    <tr>
                                        <th class="pb-2">Hisse</th>
                                        <th class="pb-2 text-right">Adet</th>
                                        <th class="pb-2 text-right">Maliyet</th>
                                        <th class="pb-2 text-right">Güncel Fiyat</th>
                                        <th class="pb-2 text-right">İşlem</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-slate-700/50">
                                    ${trs}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
            });
        }

        function openModal(id) {
            if (appState.frozenMonths[appState.currentViewMonth]) {
                alert("Bu ay kilitli! Değişiklik yapmak için önce kilidi açın.");
                return;
            }
            const m = document.getElementById(id);
            const c = document.getElementById(id + 'Content');
            m.classList.remove('hidden');
            setTimeout(() => { m.classList.remove('opacity-0'); c.classList.remove('scale-95'); }, 10);
        }

        function closeConfirmModal() {
            closeModals();
        }

        function closeModals() {
            ['portfolioModal', 'assetModal', 'confirmModal'].forEach(id => {
                const m = document.getElementById(id);
                const c = document.getElementById(id + 'Content');
                if(m) m.classList.add('opacity-0');
                if(c) c.classList.add('scale-95');
                setTimeout(() => { if(m) m.classList.add('hidden'); }, 300);
            });
            document.getElementById('newPortName').value = '';
            document.getElementById('assetName').value = '';
            document.getElementById('assetAmount').value = '';
            document.getElementById('assetCost').value = '';
            document.getElementById('assetPrice').value = '';
        }

        function openPortfolioModal() { openModal('portfolioModal'); }
        
        async function savePortfolio() {
            const name = document.getElementById('newPortName').value.trim();
            if(!name) return;
            
            const newId = 'p' + Date.now();
            const color = chartColors[appState.portfoliosData[appState.currentViewMonth].length % chartColors.length];
            
            appState.portfoliosData[appState.currentViewMonth].push({ id: newId, name: name, color: color, assets: [] });
            appState.currentPortfolioId = newId; 
            
            await saveState();
            closeModals();
            updateAllViews();
        }

        function confirmDeletePortfolio(id) {
            appState.deleteQueue = { type: 'portfolio', pId: id, aId: null };
            document.getElementById('confirmMessage').textContent = "Bu portföyü ve içindeki tüm hisseleri silmek istediğinize emin misiniz?";
            document.getElementById('confirmBtn').onclick = executeDelete;
            openModal('confirmModal');
        }

        function openAssetModal(portfolioId) {
            document.getElementById('targetPortfolioId').value = portfolioId;
            openModal('assetModal');
        }

        async function saveAsset() {
            const pId = document.getElementById('targetPortfolioId').value;
            const name = document.getElementById('assetName').value.trim().toUpperCase();
            const amount = parseFloat(document.getElementById('assetAmount').value);
            const cost = parseFloat(document.getElementById('assetCost').value);
            let price = document.getElementById('assetPrice').value;

            if(!name || isNaN(amount) || isNaN(cost)) return;
            
            price = parseFloat(price);
            if (isNaN(price)) price = cost; // Fiyat girilmediyse maliyet olsun, refresh yapınca güncellenir

            const ports = appState.portfoliosData[appState.currentViewMonth];
            const portfolio = ports.find(p => p.id === pId);
            
            if(portfolio) {
                portfolio.assets.push({ id: 'a' + Date.now(), name, amount, cost, price });
                await saveState();
            }

            closeModals();
            updateAllViews();
            
            // Yeni hisse eklenince fiyatları arka planda güncelle (kilitli değil zaten)
            refreshPrices();
        }

        function confirmDeleteAsset(pId, aId) {
            appState.deleteQueue = { type: 'asset', pId, aId };
            document.getElementById('confirmMessage').textContent = "Bu hisseyi portföyden çıkarmak istediğinize emin misiniz?";
            document.getElementById('confirmBtn').onclick = executeDelete;
            openModal('confirmModal');
        }

        async function executeDelete() {
            const { type, pId, aId } = appState.deleteQueue;
            const ports = appState.portfoliosData[appState.currentViewMonth];
            
            if (type === 'portfolio') {
                appState.portfoliosData[appState.currentViewMonth] = ports.filter(p => p.id !== pId);
                appState.activeBenchmarks = appState.activeBenchmarks.filter(b => b !== pId);
                if(appState.currentPortfolioId === pId) {
                    appState.currentPortfolioId = appState.portfoliosData[appState.currentViewMonth].length > 0 ? appState.portfoliosData[appState.currentViewMonth][0].id : null;
                }
            } else if (type === 'asset') {
                const p = ports.find(p => p.id === pId);
                if(p) p.assets = p.assets.filter(a => a.id !== aId);
            }
            
            await saveState();
            closeModals();
            updateAllViews();
        }

        function updateAllViews() {
            updatePortfolioDropdown();
            renderMonthlyView();
            renderManagementView();
            renderCompareView();
        }
    