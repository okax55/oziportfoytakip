import re

def update_calculate_return(html):
    old_calc = """        function calculateReturnForPeriod(pId, daysOffset) {
            const todayStr = appState.lastUpdatedDate;
            const currentValObj = getPortfolioValueAndCost(pId, appState.currentViewMonth, todayStr);
            if (!currentValObj) return 0;
            
            const prevStr = getPrevDateStr(todayStr, daysOffset);
            const prevValObj = getPortfolioValueAndCost(pId, appState.currentViewMonth, prevStr) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+1)) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+2)) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+3));
            
            if (!prevValObj || prevValObj.cost === 0) return 0;"""
            
    new_calc = """        function calculateAssetReturn(fetchName, currentPrice, daysOffset) {
            const todayStr = appState.lastUpdatedDate;
            const history = appState.benchmarksHistory && appState.benchmarksHistory[fetchName];
            if (!history || !currentPrice) return null;
            
            let prevPrice = null;
            for (let i = 0; i <= 3; i++) {
                const prevStr = getPrevDateStr(todayStr, daysOffset + i);
                if (history[prevStr] !== undefined) {
                    prevPrice = history[prevStr];
                    break;
                }
            }
            if (!prevPrice) return null;
            return ((currentPrice - prevPrice) / prevPrice) * 100;
        }

        function calculateReturnForPeriod(pId, daysOffset) {
            const todayStr = appState.lastUpdatedDate;
            const currentValObj = getPortfolioValueAndCost(pId, appState.currentViewMonth, todayStr);
            if (!currentValObj) return null;
            
            const prevStr = getPrevDateStr(todayStr, daysOffset);
            const prevValObj = getPortfolioValueAndCost(pId, appState.currentViewMonth, prevStr) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+1)) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+2)) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+3));
            
            if (!prevValObj || prevValObj.cost === 0) return null;"""
            
    return html.replace(old_calc, new_calc)

def update_format_pct(html):
    old_fmt = """                const formatPct = (val) => {
                    if (val === 0) return `<span class="text-slate-500">0.00%</span>`;"""
    new_fmt = """                const formatPct = (val) => {
                    if (val === null || val === undefined) return `<span class="text-slate-500 font-bold">-</span>`;
                    if (val === 0) return `<span class="text-slate-500">0.00%</span>`;"""
    return html.replace(old_fmt, new_fmt)

def update_toplam_varlik(html):
    old_varlik = """                                    <span class="text-xs text-slate-500 uppercase font-semibold border border-slate-300 dark:border-slate-700 rounded px-2 py-1 flex items-center gap-2">
                                        <i class="fa-solid fa-layer-group text-slate-600"></i> Toplam Varlık: ${stats.assetsWithStats.length}
                                    </span>"""
    new_varlik = """                                    <span class="text-xs text-brand-600 dark:text-brand-300 bg-brand-100 dark:bg-brand-900/30 uppercase font-bold border border-brand-300 dark:border-brand-700 rounded-lg px-3 py-1 flex items-center gap-2 shadow-sm">
                                        <i class="fa-solid fa-layer-group"></i> Toplam Varlık: ${stats.assetsWithStats.length}
                                    </span>"""
    return html.replace(old_varlik, new_varlik)

def update_asset_table(html):
    old_asset_fmt = """                    const formatAssetPct = (val) => {
                        if (!val) return `<span class="text-slate-500">0.00%</span>`;"""
    new_asset_fmt = """                    const d1 = calculateAssetReturn(fetchName, a.price || a.cost, 1);
                    const w1 = calculateAssetReturn(fetchName, a.price || a.cost, 7);
                    const m1 = calculateAssetReturn(fetchName, a.price || a.cost, 30);
                    const m3 = calculateAssetReturn(fetchName, a.price || a.cost, 90);
                    const y1 = calculateAssetReturn(fetchName, a.price || a.cost, 365);
                    
                    const formatAssetPct = (val) => {
                        if (val === null || val === undefined) return `<span class="text-slate-500 font-bold">-</span>`;
                        if (val === 0) return `<span class="text-slate-500">0.00%</span>`;"""
    html = html.replace(old_asset_fmt, new_asset_fmt)
    
    old_asset_tds = """                            <td class="py-3 px-4 text-right">${formatAssetPct(a.change / 30)}</td>
                            <td class="py-3 px-4 text-right">${formatAssetPct(a.change / 4)}</td>
                            <td class="py-3 px-4 text-right">${formatAssetPct(a.change)}</td>
                            <td class="py-3 px-4 text-right">${formatAssetPct(a.overallChange)}</td>
                            <td class="py-3 px-4 text-right">${formatBadgeAssetPct(a.change * (a.weight/100))}</td>"""
    new_asset_tds = """                            <td class="py-3 px-4 text-right">${formatAssetPct(d1)}</td>
                            <td class="py-3 px-4 text-right">${formatAssetPct(w1)}</td>
                            <td class="py-3 px-4 text-right">${formatAssetPct(m1)}</td>
                            <td class="py-3 px-4 text-right">${formatAssetPct(m3)}</td>
                            <td class="py-3 px-4 text-right">${formatAssetPct(y1)}</td>
                            <td class="py-3 px-4 text-right">${formatAssetPct(a.overallChange)}</td>
                            <td class="py-3 px-4 text-right">${formatBadgeAssetPct(a.change * (a.weight/100))}</td>"""
    html = html.replace(old_asset_tds, new_asset_tds)
    
    old_asset_ths = """                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Ağırlık</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Günlük</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Haftalık</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">1 Aylık</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Toplam</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Aylık Etki</th>"""
    new_asset_ths = """                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Ağırlık</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Günlük</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Haftalık</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">1 Aylık</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">3 Aylık</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">1 Yıllık</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Toplam</th>
                                        <th scope="col" class="py-3 px-4 font-semibold text-right whitespace-nowrap">Aylık Etki</th>"""
    html = html.replace(old_asset_ths, new_asset_ths)
    
    return html

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    html = update_calculate_return(html)
    html = update_format_pct(html)
    html = update_toplam_varlik(html)
    html = update_asset_table(html)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("Updates applied.")

if __name__ == '__main__':
    main()
