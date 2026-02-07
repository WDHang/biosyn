#!/usr/bin/env python3
"""
Biosyn 碳得率计算器 - Streamlit极简版
安装: pip install streamlit pandas openpyxl
运行: streamlit run app_streamlit.py
"""

import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Biosyn 碳得率计算", layout="wide")

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
}

def get_carbon_fraction(name):
    db = MOLECULAR_DB.get(name, {'mw': 120.10, 'carbon': 4})
    return db['carbon'] * 12 / db['mw']

# ============ 主界面 ============
st.title("🔬 Biosyn 碳得率计算器")

st.markdown("""
**使用说明:**
1. 上传包含色谱数据的Excel文件
2. 文件需包含"汇总"和"反应数据"两个工作表
3. 查看计算结果
""")

uploaded_file = st.file_uploader("选择Excel文件", type=['xlsx', 'xls'])

if uploaded_file:
    try:
        xl = pd.ExcelFile(uploaded_file)
        
        # 读取数据
        summary_df = pd.read_excel(xl, sheet_name='汇总')
        reaction_df = pd.read_excel(xl, sheet_name='反应数据')
        
        # 构建标准曲线
        c4_standards = summary_df.iloc[0:3]
        c4_response = (c4_standards['峰面积'] / c4_standards['浓度（mg/ml）']).mean()
        
        gald_row = summary_df.iloc[17]
        gald_response = gald_row['峰面积'] / gald_row['浓度（mg/ml）']
        
        st.success(f"标准曲线: C4响应因子={c4_response:.2f}, GALD响应因子={gald_response:.2f}")
        
        # 解析反应数据
        reactions = {}
        current_enzyme = None
        
        for _, row in reaction_df.iterrows():
            enzyme = row.get('酶名称')
            if pd.notna(enzyme):
                current_enzyme = enzyme
                reactions[enzyme] = {'产物': [], 'GALD': 0}
            
            substance = row.get('对应物质')
            if pd.notna(substance):
                peak = row['峰面积']
                if substance == 'GALD':
                    reactions[current_enzyme]['GALD'] = peak
                else:
                    reactions[current_enzyme]['产物'].append({'name': substance, 'peak': peak})
        
        # 计算碳得率
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
                products.append({'name': prod['name'], 'carbon': carbon})
            
            total = gald_carbon + total_product_carbon
            yield_pct = (total_product_carbon / total) * 100 if total > 0 else 0
            
            results.append({
                '酶': enzyme,
                '碳得率%': round(yield_pct, 2),
                '转化率%': round(100 - yield_pct, 2),
                '产物碳': round(total_product_carbon, 4),
                'GALD碳': round(gald_carbon, 4),
                '产物列表': ', '.join([p['name'] for p in products])
            })
        
        # 排序并显示
        results.sort(key=lambda x: x['碳得率%'], reverse=True)
        
        st.subheader("📊 碳得率排名")
        st.dataframe(pd.DataFrame(results))
        
        # 图表
        st.subheader("📈 可视化")
        df_chart = pd.DataFrame(results)
        st.bar_chart(df_chart.set_index('酶')['碳得率%'])
        
        st.subheader("📋 详细数据")
        for r in results:
            st.write(f"**{r['酶']}**: {r['产物列表']}")
            
    except Exception as e:
        st.error(f"处理出错: {e}")

else:
    st.info("请上传Excel文件开始分析")
