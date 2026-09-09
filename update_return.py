import re

def update_calc(html):
    old = """        function calculateReturnForPeriod(pId, daysOffset) {
            const todayStr = appState.lastUpdatedDate;
            const currentValObj = getPortfolioValueAndCost(pId, appState.currentViewMonth, todayStr);
            if (!currentValObj) return null;
            
            const prevStr = getPrevDateStr(todayStr, daysOffset);
            const prevValObj = getPortfolioValueAndCost(pId, appState.currentViewMonth, prevStr) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+1)) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+2)) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+3));
            
            if (!prevValObj || prevValObj.cost === 0) return null;"""
            
    new = """        function calculateReturnForPeriod(pId, daysOffset) {
            const todayStr = appState.lastUpdatedDate;
            const currentValObj = getPortfolioValueAndCost(pId, appState.currentViewMonth, todayStr);
            if (!currentValObj) return null;
            
            const prevStr = getPrevDateStr(todayStr, daysOffset);
            const startDateStr = getPortfolioStartDateStr(pId);
            if (new Date(prevStr) < new Date(startDateStr)) return null;
            
            const prevValObj = getPortfolioValueAndCost(pId, appState.currentViewMonth, prevStr) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+1)) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+2)) || getPortfolioValueAndCost(pId, appState.currentViewMonth, getPrevDateStr(todayStr, daysOffset+3));
            
            if (!prevValObj || prevValObj.cost === 0) return null;"""
    return html.replace(old, new)

def update_fetch(html):
    old_init_fetch = "fetchHistory(appState.monthlyTimeRange || 'this_month');"
    new_init_fetch = "fetchHistory('1y');"
    # Replace only the first occurrence which is in init()
    return html.replace(old_init_fetch, new_init_fetch, 1)

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = update_calc(html)
html = update_fetch(html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
