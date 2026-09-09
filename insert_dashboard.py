import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    js_code = """
        function calculateReturnForPeriod(pId, daysOffset) {
            const todayStr = appState.lastUpdatedDate;
            const currentValObj = getPortfolioValueAndCost(pId, appState.currentViewMonth, todayStr);
            if (!currentValObj) return 0;
            
            const prevStr = getPrevDateStr(todayStr, daysOffset);
            const prevValObj = getPortfolioValueAndCost(pId, appState.currentViewMonth, prevStr) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+1)) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+2)) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+3));
            
            if (!prevValObj || prevValObj.cost === 0) return 0;
            
            const currentReturn = (currentValObj.value - currentValObj.cost) / currentValObj.cost;
            const prevReturn = (prevValObj.value - prevValObj.cost) / prevValObj.cost;
            
            return ((1 + currentReturn) / (1 + prevReturn) - 1) * 100;
        }
        
        function calculateTotalReturn(pId) {
            const todayStr = appState.lastUpdatedDate;
            const currentValObj = getPortfolioValueAndCost(pId, appState.currentViewMonth, todayStr);
            if (!currentValObj || currentValObj.cost === 0) return 0;
            return ((currentValObj.value - currentValObj.cost) / currentValObj.cost) * 100;
        }

        function renderPerformanceDetailsTable() {
            const tbody = document.getElementById('performanceDetailsTableBody');
            if (!tbody) return;
            tbody.innerHTML = '';
            
            const allUniquePorts = getAllUniquePortfolios();
            
            allUniquePorts.forEach(p => {
                const pId = p.id;
                const startDate = getPortfolioStartDateStr(pId);
                
                const todayStr = appState.lastUpdatedDate;
                const currentValObj = getPortfolioValueAndCost(pId, appState.currentViewMonth, todayStr);
                const totalAsset = currentValObj ? currentValObj.value : 0;
                
                const d1 = calculateReturnForPeriod(pId, 1);
                const w1 = calculateReturnForPeriod(pId, 7);
                const m1 = calculateReturnForPeriod(pId, 30);
                const m3 = calculateReturnForPeriod(pId, 90);
                const m6 = calculateReturnForPeriod(pId, 180);
                const y1 = calculateReturnForPeriod(pId, 365);
                const total = calculateTotalReturn(pId);
                const totalUsd = total / 1.5; // Placeholder
                
                const formatPct = (val) => {
                    if (val === 0) return `<span class="text-slate-500">0.00%</span>`;
                    const color = val > 0 ? 'text-emerald-400' : 'text-rose-400';
                    const sign = val > 0 ? '+' : '';
                    return `<span class="${color}">${sign}${val.toFixed(2)}%</span>`;
                };

                const formatBadgePct = (val) => {
                    if (val === 0) return `<span class="px-2 py-0.5 rounded-md border bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-500">0.00%</span>`;
                    const bgBorder = val > 0 ? 'bg-emerald-100 dark:bg-emerald-900/30 border-emerald-300 dark:border-emerald-700 text-emerald-700 dark:text-emerald-400' : 'bg-rose-100 dark:bg-rose-900/30 border-rose-300 dark:border-rose-700 text-rose-700 dark:text-rose-400';
                    const sign = val > 0 ? '+' : '';
                    return `<span class="px-2 py-0.5 rounded-md border font-bold ${bgBorder}">${sign}${val.toFixed(2)}%</span>`;
                };

                // formatMoney is already defined in index.html globally!
                
                tbody.innerHTML += `
                    <tr class="hover:bg-slate-400/10 transition-colors">
                        <td class="px-5 py-4 font-medium">${startDate}</td>
                        <td class="px-5 py-4 font-bold text-brand-500 flex items-center gap-2">
                            <span class="w-3 h-3 rounded-full" style="background-color: ${p.color}"></span>
                            ${p.name}
                        </td>
                        <td class="px-5 py-4 font-bold text-right text-slate-900 dark:text-white">${formatMoney(totalAsset)}</td>
                        <td class="px-5 py-4 text-right font-medium">${formatPct(d1)}</td>
                        <td class="px-5 py-4 text-right font-medium">${formatPct(w1)}</td>
                        <td class="px-5 py-4 text-right font-medium">${formatPct(m1)}</td>
                        <td class="px-5 py-4 text-right font-medium">${formatPct(m3)}</td>
                        <td class="px-5 py-4 text-right font-medium">${formatPct(m6)}</td>
                        <td class="px-5 py-4 text-right font-medium">${formatPct(y1)}</td>
                        <td class="px-5 py-4 text-right font-medium">${formatBadgePct(total)}</td>
                        <td class="px-5 py-4 text-right font-medium">${formatBadgePct(totalUsd)}</td>
                    </tr>
                `;
            });
        }

        function renderPortfolioDetailedViews() {
            const container = document.getElementById('portfolioDetailsContainer');
            if (!container) return;
            container.innerHTML = '';
            
            const allUniquePorts = getAllUniquePortfolios();
            
            allUniquePorts.forEach(p => {
                const ports = appState.portfoliosData[appState.currentViewMonth];
                if (!ports) return;
                const activePort = ports.find(x => x.id.split('_')[0] === p.id);
                if (!activePort || activePort.assets.length === 0) return;
                
                const stats = getPortfolioStats(activePort);
                
                const tColor = stats.totalChange >= 0 ? 'text-emerald-400' : 'text-rose-400';
                const tBgBorder = stats.totalChange >= 0 ? 'bg-emerald-100 dark:bg-emerald-900/30 border-emerald-300 dark:border-emerald-700 text-emerald-700 dark:text-emerald-400' : 'bg-rose-100 dark:bg-rose-900/30 border-rose-300 dark:border-rose-700 text-rose-700 dark:text-rose-400';
                const sign = stats.totalChange > 0 ? '+' : '';

                let assetRows = '';
                stats.assetsWithStats.forEach(a => {
                    let fetchName = a.name.includes('.') ? a.name : a.name + '.IS';
                    const logoUrl = `https://financialmodelingprep.com/image-stock/${fetchName}.png`;
                    
                    const formatAssetPct = (val) => {
                        if (!val) return `<span class="text-slate-500">0.00%</span>`;
                        const color = val > 0 ? 'text-emerald-400' : 'text-rose-400';
                        const sg = val > 0 ? '+' : '';
                        return `<span class="${color}">${sg}${val.toFixed(2)}%</span>`;
                    };
                    
                    const formatBadgeAssetPct = (val) => {
                        if (!val) return `<span class="px-2 py-0.5 rounded-md border bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-500">0.00%</span>`;
                        const bgBorder = val > 0 ? 'bg-emerald-100 dark:bg-emerald-900/30 border-emerald-300 dark:border-emerald-700 text-emerald-700 dark:text-emerald-400' : 'bg-rose-100 dark:bg-rose-900/30 border-rose-300 dark:border-rose-700 text-rose-700 dark:text-rose-400';
                        const sg = val > 0 ? '+' : '';
                        return `<span class="px-2 py-0.5 rounded-md border font-bold text-xs ${bgBorder}">${sg}${val.toFixed(2)}%</span>`;
                    };
                    
                    assetRows += `
                        <tr class="hover:bg-slate-400/10 transition-colors border-b border-white/5 last:border-0">
                            <td class="py-3 px-4 flex items-center font-bold text-base text-slate-900 dark:text-white">
                                <img src="${logoUrl}" class="w-8 h-8 rounded-full border border-slate-300 dark:border-slate-600 bg-white mr-3" onerror="this.style.display='none'; this.nextElementSibling.classList.remove('hidden'); this.nextElementSibling.classList.add('flex');">
                                <div class="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 flex justify-center text-xs font-bold border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white items-center hidden mr-3">
                                    ${a.name.substring(0,2)}
                                </div>
                                ${a.name}
                            </td>
                            <td class="py-3 px-4 text-right">${formatMoney(a.price || a.cost)}</td>
                            <td class="py-3 px-4 text-right">${formatMoney(a.initial_cost !== undefined ? a.initial_cost : a.cost)}</td>
                            <td class="py-3 px-4 text-right font-bold">${a.weight.toFixed(2)}%</td>
                            <td class="py-3 px-4 text-right">${formatAssetPct(a.change / 30)}</td>
                            <td class="py-3 px-4 text-right">${formatAssetPct(a.change / 4)}</td>
                            <td class="py-3 px-4 text-right">${formatAssetPct(a.change)}</td>
                            <td class="py-3 px-4 text-right">${formatAssetPct(a.overallChange)}</td>
                            <td class="py-3 px-4 text-right">${formatBadgeAssetPct(a.change * (a.weight/100))}</td>
                        </tr>
                    `;
                });
                
                container.innerHTML += `
                    <div class="glass-panel rounded-2xl shadow-xl overflow-hidden flex flex-col">
                        <div class="p-5 border-b border-white/20 dark:border-white/5 flex justify-between items-center bg-slate-800/5">
                            <div class="flex items-center gap-3">
                                <span class="text-xl font-extrabold tracking-wide uppercase text-slate-900 dark:text-white flex items-center gap-2">
                                    ${p.name}
                                    <a href="#" onclick="switchTab('manage');" class="text-slate-400 hover:text-brand-400 ml-1 text-sm"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>
                                </span>
                            </div>
                            <div class="flex items-center gap-6">
                                <div class="flex items-center gap-2">
                                    <span class="text-xs text-slate-500 uppercase font-semibold border border-slate-300 dark:border-slate-700 rounded px-2 py-1 flex items-center gap-2">
                                        <i class="fa-solid fa-layer-group text-slate-600"></i> Toplam Varlık: ${stats.assetsWithStats.length}
                                    </span>
                                </div>
                                <div class="flex items-center gap-2">
                                    <span class="text-xs text-slate-500 uppercase font-semibold">Bu Ay Getirisi:</span>
                                    <span class="px-3 py-1 rounded-md border font-bold ${tBgBorder}">${sign}${stats.totalChange.toFixed(2)}%</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="p-4 overflow-x-auto">
                            <table class="w-full text-sm text-left text-slate-700 dark:text-slate-300">
                                <thead class="text-xs text-slate-500 dark:text-slate-400 border-b border-white/20 dark:border-white/5 uppercase tracking-wide">
                                    <tr>
                                        <th scope="col" class="py-3 px-4 font-semibold whitespace-nowrap">Hisse / Varlık</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Fiyat</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Maliyet</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Ağırlık</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Günlük</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Haftalık</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">1 Aylık</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Toplam</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Aylık Etki</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-slate-700/30">
                                    ${assetRows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
            });
        }
"""

    if "window.toggleBenchmark = async function" in content:
        content = content.replace("window.toggleBenchmark = async function", js_code + "\n\n        window.toggleBenchmark = async function")
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Success")
    else:
        print("Failed to find insertion point")

if __name__ == '__main__':
    main()
