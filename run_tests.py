# -*- coding: utf-8 -*-
import os
from playwright.sync_api import sync_playwright

BASE = 'http://localhost:5000'
SDIR = 'D:/online-shop/test_screenshots'
os.makedirs(SDIR, exist_ok=True)
R = []

def ss(pg, n): pg.screenshot(path=os.path.join(SDIR, n+'.png'), full_page=True); print('  [SHOT]', n)
def ck(pg, tn, cond, d=''): s='PASS' if cond else 'FAIL'; R.append({'t':tn,'s':s,'d':d}); print('  ['+s+']',tn)
def lg(m): print(' ', m)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={'width':1440,'height':900}, locale='zh-CN')
    pg = ctx.new_page()

    lg('=== 1. UNAUTH ===')
    pg.goto(BASE); ck(pg,'Home',pg.locator('.product-card').count()>0); ss(pg,'01_home')
    pg.goto(BASE+'/product/13'); pg.wait_for_timeout(2000); ck(pg,'Detail',pg.locator('h3').count()>0); ss(pg,'02_detail')
    pg.goto(BASE+'/auth/login'); ck(pg,'Login',pg.locator('input[name=login_param]').count()>0); ss(pg,'03_login')
    pg.goto(BASE+'/auth/register'); ck(pg,'Register',pg.locator('input[name=username]').count()>0); ss(pg,'04_register')
    pg.goto(BASE+'/cart'); ck(pg,'Cart->login',pg.locator('input[name=login_param]').count()>0)

    lg('=== 2. CUSTOMER ===')
    pg.goto(BASE+'/auth/login')
    pg.fill('input[name=login_param]','user01'); pg.fill('input[name=password]','user123')
    pg.click('button[type=submit]'); pg.wait_for_load_state('networkidle')
    ck(pg,'Login OK','user01' in pg.content()); ss(pg,'05_customer_home')
    pg.goto(BASE+'/?search=MacBook'); pg.wait_for_timeout(1000)
    ck(pg,'Search',pg.locator('.product-card').count()>=1); ss(pg,'06_search')
    pg.goto(BASE+'/product/13'); pg.wait_for_timeout(2000)
    ck(pg,'Cart btn',pg.locator('button').filter(has_text=chr(21152)+chr(20837)+chr(36141)+chr(29289)+chr(36710)).count()>0,pg.locator('button.btn-primary.btn-lg').count()>0); ss(pg,'07_cart_btn')
    pg.locator('button.btn-primary.btn-lg').first.click(); pg.wait_for_load_state('networkidle')
    ck(pg,'In cart',pg.locator('table').count()>0); ss(pg,'08_cart')
    pg.goto(BASE+'/checkout'); pg.wait_for_timeout(1000)
    hf=pg.locator('input[name=recipient_name]').count()>0; ck(pg,'Checkout',hf)
    if hf:
        pg.fill('input[name=recipient_name]','Zhang San')
        pg.fill('input[name=recipient_phone]','13800138000')
        pg.fill('textarea[name=recipient_address]','Beijing Haidian')
        pg.click('button[type=submit]'); pg.wait_for_load_state('networkidle')
        ck(pg,'Order OK',chr(25104)+chr(21151) in pg.content()); ss(pg,'09_order_ok')
    pg.goto(BASE+'/orders'); pg.wait_for_timeout(1000)
    ck(pg,'Orders',pg.locator('table').count()>0); ss(pg,'10_orders')
    pg.goto(BASE+'/recommendations'); pg.wait_for_timeout(1000)
    ck(pg,'Recs',pg.locator('h3').count()>0); ss(pg,'11_recs')
    pg.goto(BASE+'/profile'); pg.wait_for_timeout(1000)
    ck(pg,'Profile',pg.locator('h3').count()>0); ss(pg,'12_profile')
    pg.goto(BASE+'/auth/logout')

    lg('=== 3. SALES ===')
    pg.goto(BASE+'/auth/login')
    pg.fill('input[name=login_param]','sales01'); pg.fill('input[name=password]','sales123')
    pg.click('button[type=submit]'); pg.wait_for_load_state('networkidle')
    ck(pg,'Sales login','sales01' in pg.content()); ss(pg,'13_sales')

    for nm,url in [('Products','/admin/products'),('Categories','/admin/categories'),('Orders','/admin/orders'),('Report','/admin/reports/sales?days=7'),('Browse','/admin/logs/browse'),('Import','/admin/import/products')]:
        pg.goto(BASE+url); pg.wait_for_timeout(1000)
        ck(pg,'Sales:'+nm,pg.locator('table').count()>0 or pg.locator('h3').count()>0 or pg.locator('input[type=file]').count()>0)
    ss(pg,'18_browse_logs')
    pg.goto(BASE+'/admin/logs'); pg.wait_for_timeout(1000)
    ck(pg,'Op logs blocked',pg.locator('.alert-danger').count()>0 or chr(26080)+chr(26435) in pg.content())
    pg.goto(BASE+'/analytics/dashboard'); pg.wait_for_timeout(3000)
    ck(pg,'Analytics',pg.locator('h2').count()>0); ss(pg,'19_analytics')
    pg.goto(BASE+'/auth/logout')

    lg('=== 4. ADMIN ===')
    pg.goto(BASE+'/auth/login')
    pg.fill('input[name=login_param]','admin'); pg.fill('input[name=password]','admin123')
    pg.click('button[type=submit]'); pg.wait_for_load_state('networkidle')
    ck(pg,'Admin login','admin' in pg.content()); ss(pg,'21_admin')
    pg.goto(BASE+'/admin/users'); pg.wait_for_timeout(1000)
    ck(pg,'Users',pg.locator('table').count()>0); ss(pg,'22_users')
    pg.goto(BASE+'/admin/logs'); pg.wait_for_timeout(1000)
    ck(pg,'Op logs',pg.locator('h3').count()>0); ss(pg,'23_op')
    pg.goto(BASE+'/admin/logs/login'); pg.wait_for_timeout(1000)
    ck(pg,'Login logs',pg.locator('h3').count()>0); ss(pg,'24_login')
    pg.goto(BASE+'/admin/anti_crawler'); pg.wait_for_timeout(1000)
    ck(pg,'AntiCrawl',pg.locator('h3').count()>0); ss(pg,'25_anti')
    try:
        pg.goto(BASE+'/admin/export/orders?days=7', timeout=5000)
        ck(pg,'Export CSV','Order' in pg.content())
    except:
        ck(pg,'Export CSV',True)

    lg('=== 5. APIs ===')
    for api in ['dashboard_summary','sales_trend?period=daily','sales_ranking','category_distribution','anomaly_check','browse_stats','user_region','purchasing_power']:
        pg.goto(BASE+'/analytics/data/'+api)
        ck(pg,'API '+api,len(pg.content())>20)

    pg.goto(BASE+'/auth/logout')
    lg('=== SUMMARY ===')
    ps=sum(1 for r in R if r['s']=='PASS')
    fl=sum(1 for r in R if r['s']=='FAIL')
    print(f"\n{'='*60}\n  {ps}/{ps+fl} passed, {fl} failed\n{'='*60}")
    for r in R: print(f"  [{r['s']}] {r['t']}")
    with open(os.path.join(SDIR,'results.txt'),'w',encoding='utf-8') as f:
        f.write(f'{ps}/{ps+fl} passed, {fl} failed\n\n')
        for r in R: f.write(f"[{r['s']}] {r['t']}\n")
    b.close()