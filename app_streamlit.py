#!/usr/bin/env python3
"""
CarbonOracle
"""

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="CarbonOracle", page_icon="🦥", layout="wide")

# ============ 分子数据库 ============
MOLECULAR_DB = {
    'GALD': {'mw': 60.05, 'carbon': 2},
    '赤藓糖': {'mw': 120.10, 'carbon': 4},
    '赤藓酮糖': {'mw': 120.10, 'carbon': 4},
    '苏阿糖': {'mw': 120.10, 'carbon': 4},
    '葡萄糖': {'mw': 180.16, 'carbon': 6},
    '山梨糖': {'mw': 180.16, 'carbon': 6},
    '阿洛糖': {'mw': 180.16, 'carbon': 6},
    '阿洛酮糖': {'mw': 180.16, 'carbon': 6},
    '果糖': {'mw': 180.16, 'carbon': 6},
    '甘露糖': {'mw': 180.16, 'carbon': 6},
}

def get_carbon_fraction(name):
    db = MOLECULAR_DB.get(name, {'mw': 120.10, 'carbon': 4})
    return db['carbon'] * 12 / db['mw']

def export_to_excel(results, c4_response, gald_response):
    """导出结果到Excel"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 汇总表
        summary_data = []
        for i, r in enumerate(results, 1):
            summary_data.append({
                '排名': i,
                '酶': r['酶'],
                '碳得率_%': r['碳得率%'],
                '转化率_%': r['转化率%'],
                '产物碳_mgC_mL': r['产物碳'],
                'GALD碳_mgC_mL': r['GALD碳'],
            })
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='碳得率汇总', index=False)
        
        # 各酶详细表
        for r in results:
            sheet_name = r['酶'].replace(' ', '_')[:31]
            detail_data = []
            # GALD
            detail_data.append({
                '物质': 'GALD(剩余)',
                '类型': 'C2',
                '峰面积': r.get('GALD峰面积', 0),
                '浓度_mg_mL': r['GALD碳'] / (2*12/60.05),
                '碳质量_mgC_mL': r['GALD碳'],
            })
            # 产物
            for prod in r.get('产物详情', []):
                detail_data.append({
                    '物质': prod['name'],
                    '类型': 'C4',
                    '峰面积': prod['peak'],
                    '浓度_mg_mL': prod['peak'] / c4_response,
                    '碳质量_mgC_mL': prod['carbon'],
                })
            pd.DataFrame(detail_data).to_excel(writer, sheet_name=sheet_name, index=False)
        
        # 标准曲线
        std_data = [
            {'糖类型': 'C4', '响应因子': c4_response, '碳质量分数': 4*12/120.10},
            {'糖类型': 'C2(GALD)', '响应因子': gald_response, '碳质量分数': 2*12/60.05},
        ]
        pd.DataFrame(std_data).to_excel(writer, sheet_name='标准曲线', index=False)
    
    return output.getvalue()

# ============ 主界面 ============
st.title("🔬 CarbonOracle")

st.markdown("""
**Carbon Yield Calculator for Enzymatic Reactions**

*Upload your LC/GC data and calculate carbon yield automatically.*

---

**使用说明 (User Guide):**
1. 📁 Upload an Excel file with your chromatographic data
2. 📋 File must contain two sheets: "汇总" (Summary) and "反应数据" (Reaction Data)
3. 📊 View and download calculation results

**Supported Compounds:**
- C4 Sugars: Erythrose, Threose, Erythrulose, Sorbose
- C6 Sugars: Glucose, Fructose, Mannose, Allose, and more
- Substrate: GALD (Glyceraldehyde)
""")

uploaded_file = st.file_uploader("选择Excel文件", type=['xlsx', 'xls'])

if uploaded_file:
    try:
        xl = pd.ExcelFile(uploaded_file)
        
        # 读取数据
        summary_df = pd.read_excel(xl, sheet_name='汇总')
        reaction_df = pd.read_excel(xl, sheet_name='反应数据')
        
        # 清理列名中的空格
        summary_df.columns = summary_df.columns.str.strip()
        reaction_df.columns = reaction_df.columns.str.strip()
        
        # ============ 构建标准曲线 ============
        c4_mask = summary_df['4C标品名称'].notna() & ~summary_df['4C标品名称'].isin(['6C标品名称', '样品名称', '反应条件/体系'])
        c4_standards = summary_df[c4_mask]
        
        if len(c4_standards) == 0:
            st.error("未找到C4糖标准品数据")
            st.stop()
        
        c4_response = (c4_standards['峰面积'] / c4_standards['浓度（mg/ml）']).mean()
        
        gald_mask = summary_df['4C标品名称'] == 'GALD'
        gald_row = summary_df[gald_mask]
        
        if len(gald_row) == 0:
            st.error("未找到GALD标准品数据")
            st.stop()
        
        gald_response = gald_row['峰面积'].values[0] / gald_row['浓度（mg/ml）'].values[0]
        
        st.success(f"标准曲线: C4响应因子={c4_response:.2f}, GALD响应因子={gald_response:.2f}")
        
        # ============ 解析反应数据 ============
        reactions = {}
        current_enzyme = None
        
        for idx, row in reaction_df.iterrows():
            enzyme = row.get('酶名称')
            if pd.notna(enzyme) and str(enzyme).strip() != '':
                current_enzyme = str(enzyme).strip()
                reactions[current_enzyme] = {'产物': [], 'GALD': 0}
            
            substance = row.get('对应物质')
            if pd.notna(substance) and current_enzyme:
                peak = row['峰面积']
                substance = str(substance).strip()
                
                if substance == 'GALD':
                    reactions[current_enzyme]['GALD'] = peak
                else:
                    reactions[current_enzyme]['产物'].append({'name': substance, 'peak': peak})
        
        if not reactions:
            st.error("未找到反应数据")
            st.stop()
        
        # ============ 计算碳得率 ============
        results = []
        for enzyme, data in reactions.items():
            gald_carbon = (data['GALD'] / gald_response) * (2 * 12 / 60.05)
            total_product_carbon = 0
            products = []
            
            for prod in data['产物']:
                cf = get_carbon_fraction(prod['name'])
                conc = prod['peak'] / c4_response
                carbon = conc * cf
                total_product_carbon += carbon
                products.append({'name': prod['name'], 'peak': prod['peak'], 'carbon': carbon})
            
            total = gald_carbon + total_product_carbon
            yield_pct = (total_product_carbon / total) * 100 if total > 0 else 0
            
            results.append({
                '酶': enzyme,
                '碳得率%': round(yield_pct, 2),
                '转化率%': round(100 - yield_pct, 2),
                '产物碳': round(total_product_carbon, 4),
                'GALD碳': round(gald_carbon, 4),
                '产物列表': ', '.join([p['name'] for p in products]),
                '产物详情': products,
                'GALD峰面积': data['GALD'],
            })
        
        results.sort(key=lambda x: x['碳得率%'], reverse=True)
        
        # ============ 显示结果 ============
        st.subheader("📊 碳得率排名")
        st.dataframe(pd.DataFrame(results))
        
        st.subheader("📈 可视化")
        df_chart = pd.DataFrame(results)
        st.bar_chart(df_chart.set_index('酶')['碳得率%'])
        
        st.subheader("📋 详细数据")
        for r in results:
            st.write(f"**{r['酶']}**: {r['产物列表']}")
        
        # ============ 下载按钮 ============
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            excel_data = export_to_excel(results, c4_response, gald_response)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="📥 下载Excel结果",
                data=excel_data,
                file_name=f"碳得率结果_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col2:
            st.info("点击按钮下载完整计算结果，包含汇总表、详细数据和标准曲线参数")
            
    except Exception as e:
        st.error(f"处理出错: {e}")

else:
    st.info("请上传Excel文件开始分析")
