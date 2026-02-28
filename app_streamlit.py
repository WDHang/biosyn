#!/usr/bin/env python3
"""
CarbonOracle - Carbon Yield Calculator
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime

st.set_page_config(page_title="CarbonOracle", page_icon="🦥", layout="wide")

# ============ Molecular Database ============
MOLECULAR_DB = {
    'GALD': {'mw': 60.05, 'carbon': 2},
    'Erythrose': {'mw': 120.10, 'carbon': 4},
    'Threose': {'mw': 120.10, 'carbon': 4},
    'Erythrulose': {'mw': 120.10, 'carbon': 4},
    'Glucose': {'mw': 180.16, 'carbon': 6},
    'Fructose': {'mw': 180.16, 'carbon': 6},
    'Mannose': {'mw': 180.16, 'carbon': 6},
    'Galactose': {'mw': 180.16, 'carbon': 6},
    'Sorbose': {'mw': 180.16, 'carbon': 6},
    'Tagatose': {'mw': 180.16, 'carbon': 6},
    'Gulose': {'mw': 180.16, 'carbon': 6},
    'Altrose': {'mw': 180.16, 'carbon': 6},
    'Allose': {'mw': 180.16, 'carbon': 6},
    'Idose': {'mw': 180.16, 'carbon': 6},
    'Talose': {'mw': 180.16, 'carbon': 6},
    'Psicose': {'mw': 180.16, 'carbon': 6},
}

def get_carbon_fraction(name):
    db = MOLECULAR_DB.get(name, {'mw': 120.10, 'carbon': 4})
    return db['carbon'] * 12 / db['mw']

st.title("🔬 CarbonOracle")

st.markdown("""
**Carbon Yield Calculator for Enzymatic Reactions**

*Upload your LC/GC data and calculate carbon yield automatically.*

---

**📋 Excel File Format:**

**Sheet 1: Standard Curve** (required)
- Compound, Retention_Time, Peak_Area, Concentration

**Sheet 2: Reaction Data** (required)
- Enzyme, Substrate, Retention_Time, Peak_Area

---
""")

uploaded_file = st.file_uploader("Choose Excel File", type=['xlsx', 'xls'])

if uploaded_file:
    try:
        xl = pd.ExcelFile(uploaded_file)
        
        # Read data
        standard_df = None
        for name in ['Standard Curve', '汇总', 'Summary']:
            if name in xl.sheet_names:
                standard_df = pd.read_excel(xl, sheet_name=name)
                break
        if standard_df is None:
            st.error("Standard Curve sheet not found")
            st.stop()
        
        reaction_df = None
        for name in ['Reaction Data', 'Reaction', '反应数据']:
            if name in xl.sheet_names:
                reaction_df = pd.read_excel(xl, sheet_name=name)
                break
        if reaction_df is None:
            st.error("Reaction Data sheet not found")
            st.stop()
        
        # Clean column names
        standard_df.columns = standard_df.columns.str.strip()
        reaction_df.columns = reaction_df.columns.str.strip()
        
        # Map column names
        summary_col_map = {}
        for col in standard_df.columns:
            col_lower = str(col).lower().strip()
            if col_lower == 'compound':
                summary_col_map['compound'] = col
            elif 'area' in col_lower:
                summary_col_map['area'] = col
            elif 'concentration' in col_lower:
                summary_col_map['conc'] = col
        
        reaction_col_map = {}
        for col in reaction_df.columns:
            col_lower = str(col).lower().strip()
            if 'enzyme' in col_lower:
                reaction_col_map['enzyme'] = col
            elif 'area' in col_lower:
                reaction_col_map['area'] = col
            elif 'rt' in col_lower or 'retention' in col_lower:
                reaction_col_map['rt'] = col
            elif 'compound' in col_lower:
                reaction_col_map['compound'] = col
            elif 'substrate' in col_lower or '底物' in col:
                reaction_col_map['substrate'] = col
        
        # Check required columns
        if 'enzyme' not in reaction_col_map or 'area' not in reaction_col_map:
            st.error("Required columns not found: Enzyme Name, Peak Area")
            st.stop()
        
        # Build RT reference: {RT_value: compound_name}
        rt_ref = {}
        for _, row in standard_df.iterrows():
            compound = row.get(summary_col_map.get('compound', 'Compound'))
            rt = row.get('Retention_Time')
            if pd.notna(rt) and pd.notna(compound):
                rt_ref[round(float(rt), 6)] = str(compound).strip()
        
        # C4 response factor
        c4_sugar_names = ['Erythrose', 'Threose', 'Erythrulose']
        c4_mask = standard_df[summary_col_map['compound']].isin(c4_sugar_names)
        c4_standards = standard_df[c4_mask]
        
        if len(c4_standards) == 0:
            st.error("C4 sugar standard data not found")
            st.stop()
        
        c4_response = (c4_standards[summary_col_map['area']] / c4_standards[summary_col_map['conc']]).mean()
        
        # Parse reaction data
        has_compound = 'compound' in reaction_col_map
        has_substrate = 'substrate' in reaction_col_map
        tolerance = 0.15
        
        reactions = {}
        current_enzyme = None
        current_substrate = None
        rt_predictions = []
        
        for idx, row in reaction_df.iterrows():
            enzyme = row.get(reaction_col_map.get('enzyme'))
            substrate_val = row.get(reaction_col_map.get('substrate'))
            
            # Update substrate
            if has_substrate and pd.notna(substrate_val):
                current_substrate = str(substrate_val).strip()
            
            # Update enzyme
            if pd.notna(enzyme) and str(enzyme).strip() != '':
                current_enzyme = str(enzyme).strip()
                reactions.setdefault(current_enzyme, {
                    'substrate': current_substrate,
                    'peaks': []
                })
            elif current_enzyme:
                reactions.setdefault(current_enzyme, {
                    'substrate': current_substrate,
                    'peaks': []
                })
            
            if not current_enzyme:
                continue
            
            # Get compound from column or RT matching
            compound_from_col = None
            if has_compound:
                compound_val = row.get(reaction_col_map.get('compound'))
                if pd.notna(compound_val):
                    compound_from_col = str(compound_val).strip()
            
            rt_val = row.get(reaction_col_map.get('rt', 'Retention_Time'))
            
            # RT matching
            if compound_from_col:
                pred_compound = compound_from_col
                is_predicted = False
                rt_deviation = None
            elif pd.notna(rt_val):
                best_match = None
                best_dev = None
                for std_rt, compound in rt_ref.items():
                    dev = float(rt_val) - std_rt
                    abs_dev = abs(dev)
                    if abs_dev <= tolerance:
                        if best_match is None or abs_dev < best_dev:
                            best_match = compound
                            best_dev = abs_dev
                            rt_deviation = round(dev, 6)
                if best_match:
                    pred_compound = best_match
                    is_predicted = True
                else:
                    pred_compound = 'Unknown'
                    is_predicted = True
                    rt_deviation = None
            else:
                continue
            
            peak = row[reaction_col_map['area']]
            is_substrate_peak = (pred_compound == current_substrate)
            
            # Record peak
            reactions[current_enzyme]['peaks'].append({
                'compound': pred_compound,
                'peak': peak,
                'is_substrate': is_substrate_peak
            })
            
            # For display - Substrate after Enzyme
            rt_predictions.append({
                'Enzyme': current_enzyme,
                'Substrate': current_substrate,
                'RT': round(float(rt_val), 6) if pd.notna(rt_val) else None,
                'pred_compound': pred_compound if pred_compound != 'Unknown' else None,
                'Is_Substrate': is_substrate_peak,
                'RT_Deviation': f"{rt_deviation:+.6f}" if rt_deviation is not None else '-',
                'Peak_Area': round(peak, 6)
            })
        
        if not reactions:
            st.error("Reaction data not found")
            st.stop()
        
        # Show RT matching results
        st.subheader("🔬 RT Matching Results by Enzyme")
        if rt_predictions:
            pred_df = pd.DataFrame(rt_predictions)
            st.dataframe(pred_df)
        
        st.markdown("---")
        
        # Auto-detect substrates
        if has_substrate:
            substrates_in_data = set()
            for idx, row in reaction_df.iterrows():
                substrate = row.get(reaction_col_map.get('substrate'))
                if pd.notna(substrate):
                    substrates_in_data.add(str(substrate).strip())
            if substrates_in_data:
                st.success(f"Detected substrates: {', '.join(substrates_in_data)}")
        
        # Calculate carbon yield
        results = []
        for enzyme, data in reactions.items():
            substrate = data['substrate']
            peaks = data['peaks']
            
            substrate_carbon = 0
            product_carbon = 0
            products = []
            
            for p in peaks:
                cf = get_carbon_fraction(p['compound'])
                conc = p['peak'] / c4_response
                carbon = conc * cf
                
                if p['is_substrate']:
                    substrate_carbon += carbon
                else:
                    product_carbon += carbon
                    products.append({
                        'name': p['compound'],
                        'peak': p['peak'],
                        'carbon': carbon
                    })
            
            total = substrate_carbon + product_carbon
            yield_pct = (product_carbon / total) * 100 if total > 0 else 0
            
            results.append({
                'enzyme': enzyme,
                'substrate': substrate,
                'yield_pct': round(yield_pct, 2),
                'conversion_pct': round(100 - yield_pct, 2),
                'product_carbon': round(product_carbon, 4),
                'substrate_carbon': round(substrate_carbon, 4),
                'products': products,
            })
        
        results.sort(key=lambda x: x['yield_pct'], reverse=True)
        
        # Display response factors
        st.success("Standard Curves calculated successfully!")
        st.markdown(f"""
        <div style="display: flex; gap: 40px; margin-top: 16px;">
            <div>
                <span style="color: #666; font-size: 14px;">C4 Sugar Response Factor</span><br>
                <span style="font-size: 18px; font-weight: 600;">{c4_response:.6f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # ============ Display Results ============
        st.subheader("📊 Carbon Yield Ranking")
        
        display_df = pd.DataFrame([{
            'Rank': i+1,
            'Enzyme': r['enzyme'],
            'Substrate': r['substrate'],
            'Carbon_Yield_%': r['yield_pct'],
            'Conversion_%': r['conversion_pct'],
            'Product_Carbon': r['product_carbon'],
            'Substrate_Carbon': r['substrate_carbon'],
        } for i, r in enumerate(results)])
        st.dataframe(display_df)
        
        # ============ Product Details ============
        st.subheader("📦 Product Details by Enzyme")
        
        for r in results:
            with st.expander(f"{r['enzyme']} ({r['yield_pct']}% yield)", expanded=False):
                product_data = []
                for prod in r['products']:
                    conc = prod['peak'] / c4_response
                    product_data.append({
                        'Compound': prod['name'],
                        'Peak_Area': round(prod['peak'], 6),
                        'Concentration': round(conc, 6),
                        'Carbon_Mass': round(prod['carbon'], 6),
                    })
                if product_data:
                    st.dataframe(pd.DataFrame(product_data))
                else:
                    st.info("No products detected")
        
        # ============ Visualization ============
        st.subheader("📈 Visualization")
        df_chart = pd.DataFrame(results)
        
        chart = alt.Chart(df_chart).mark_bar(cornerRadiusEnd=4).encode(
            x=alt.X('enzyme', title='Enzyme', sort='-y'),
            y=alt.Y('yield_pct', title='Carbon Yield (%)', scale=alt.Scale(domain=[0, 100])),
            color=alt.Color('yield_pct', scale=alt.Scale(domain=[0, 100], range=['#90CAF9', '#1565C0']), legend=None),
            tooltip=['enzyme', 'yield_pct', 'conversion_pct', 'product_carbon', 'substrate']
        ).properties(
            height=350,
            width=600
        ).configure_axis(
            labelFontSize=12,
            titleFontSize=14
        )
        
        st.altair_chart(chart, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error: {e}")
        import traceback
        st.error(traceback.format_exc())

else:
    st.info("Upload an Excel file to begin analysis")
