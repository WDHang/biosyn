#!/usr/bin/env python3
"""
CarbonOracle
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="CarbonOracle", page_icon="🦥", layout="wide")

# ============ Molecular Database ============
MOLECULAR_DB = {
    'GALD': {'mw': 60.05, 'carbon': 2},
    'Erythrose': {'mw': 120.10, 'carbon': 4},
    'Threose': {'mw': 120.10, 'carbon': 4},
    'Erythrulose': {'mw': 120.10, 'carbon': 4},
    'Glucose': {'mw': 180.16, 'carbon': 6},
    'Sorbose': {'mw': 180.16, 'carbon': 6},
    'Tagatose': {'mw': 180.16, 'carbon': 6},
    'Gulose': {'mw': 180.16, 'carbon': 6},
    'Altrose': {'mw': 180.16, 'carbon': 6},
    'Allose': {'mw': 180.16, 'carbon': 6},
    'Mannose': {'mw': 180.16, 'carbon': 6},
    'Galactose': {'mw': 180.16, 'carbon': 6},
    'Idose': {'mw': 180.16, 'carbon': 6},
    'Fructose': {'mw': 180.16, 'carbon': 6},
    'Psychose': {'mw': 180.16, 'carbon': 6},
    'Talose': {'mw': 180.16, 'carbon': 6},
}

def get_carbon_fraction(name):
    db = MOLECULAR_DB.get(name, {'mw': 120.10, 'carbon': 4})
    return db['carbon'] * 12 / db['mw']

def get_sugar_type(name):
    c4_sugars = ['Erythrose', 'Threose', 'Erythrulose', '赤藓糖', '苏阿糖', '赤藓酮糖']
    if name in c4_sugars:
        return 'C4'
    return 'C6'

def build_rt_reference(standard_df, compound_col='Compound', rt_col='Retention_Time'):
    rt_ref = {}
    for _, row in standard_df.iterrows():
        compound = row.get(compound_col)
        rt = row.get(rt_col)
        if pd.notna(rt) and pd.notna(compound):
            rt_ref[round(float(rt), 6)] = str(compound).strip()
    return rt_ref

def scan_rt_matches(standard_df, reaction_df, std_compound_col='Compound', std_rt_col='Retention_Time', 
                    rxn_rt_col='Retention_Time', tolerance=0.15):
    import numpy as np
    
    std_rts = []
    for _, row in standard_df.iterrows():
        compound = row.get(std_compound_col)
        rt = row.get(std_rt_col)
        if pd.notna(compound) and pd.notna(rt):
            std_rts.append({'compound': str(compound).strip(), 'std_rt': round(float(rt), 6)})
    
    rxn_rts = reaction_df[rxn_rt_col].dropna().tolist()
    rxn_rts_array = np.array(rxn_rts)
    
    matches = {}
    for std in std_rts:
        compound = std['compound']
        std_rt = std['std_rt']
        
        deviations = np.abs(rxn_rts_array - std_rt)
        min_dev = np.min(deviations) if len(deviations) > 0 else None
        closest_idx = np.argmin(deviations) if len(deviations) > 0 else None
        closest_rt = rxn_rts[closest_idx] if closest_idx is not None else None
        
        matches[compound] = {
            'std_rt': std_rt,
            'matched_rt': round(closest_rt, 6) if closest_rt is not None else None,
            'deviation': round(closest_rt - std_rt, 6) if closest_rt is not None else None,
            'abs_deviation': round(min_dev, 6) if min_dev is not None else None,
            'is_match': min_dev <= tolerance if min_dev is not None else False
        }
    
    return matches

def get_peak_by_rt(reaction_df, target_rt, tolerance=0.15, rxn_rt_col='Retention_Time', area_col='Peak_Area'):
    for _, row in reaction_df.iterrows():
        rt = row.get(rxn_rt_col)
        if pd.notna(rt) and abs(float(rt) - target_rt) <= tolerance:
            return row.get(area_col)
    return None

def export_to_excel(results, c4_response, gald_response):
    """Export results to Excel"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = []
        for i, r in enumerate(results, 1):
            summary_data.append({
                'Rank': i,
                'Enzyme': r['enzyme'],
                'Carbon_Yield_%': r['yield_pct'],
                'Conversion_%': r['conversion_pct'],
                'Product_Carbon_mgC_mL': r['product_carbon'],
                'GALD_Carbon_mgC_mL': r['gald_carbon'],
            })
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Carbon_Yield_Summary', index=False)
        
        # Individual enzyme sheets
        for r in results:
            sheet_name = r['enzyme'].replace(' ', '_')[:31]
            detail_data = []
            # GALD
            detail_data.append({
                'Compound': 'GALD (Remaining)',
                'Type': 'C2',
                'Peak_Area': r.get('gald_peak', 0),
                'Concentration_mg_mL': r['gald_carbon'] / (2*12/60.05),
                'Carbon_Mass_mgC_mL': r['gald_carbon'],
            })
            # Products
            for prod in r.get('products', []):
                detail_data.append({
                    'Compound': prod['name'],
                    'Type': 'C4',
                    'Peak_Area': prod['peak'],
                    'Concentration_mg_mL': prod['peak'] / c4_response,
                    'Carbon_Mass_mgC_mL': prod['carbon'],
                })
            pd.DataFrame(detail_data).to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Standard curves
        std_data = [
            {'Sugar_Type': 'C4', 'Response_Factor': c4_response, 'Carbon_Fraction': 4*12/120.10},
            {'Sugar_Type': 'C2(GALD)', 'Response_Factor': gald_response, 'Carbon_Fraction': 2*12/60.05},
        ]
        pd.DataFrame(std_data).to_excel(writer, sheet_name='Standard_Curves', index=False)
    
    return output.getvalue()

# ============ Main Interface ============
st.title("🔬 CarbonOracle")

st.markdown("""
**Carbon Yield Calculator for Enzymatic Reactions**

*Upload your LC/GC data and calculate carbon yield automatically.*

---
**User Guide:**
1. 📁 Upload an Excel file with your chromatographic data
2. 📋 Sheet names: "Standard Curve" and "Reaction Data"
3. 📊 View and download calculation results

**Supported Compounds:**
- C4 Sugars: Erythrose, Threose, Erythrulose
- C6 Sugars: Glucose, Fructose, Mannose, Sorbose, Allose, and more
- Substrate: GALD (Glyceraldehyde)
""")

uploaded_file = st.file_uploader("Choose Excel File", type=['xlsx', 'xls'])

if uploaded_file:
    try:
        xl = pd.ExcelFile(uploaded_file)
        
        # Read data
        # Try both English and Chinese sheet names
        standard_names = ['Standard Curve', '汇总', 'Summary']
        reaction_names = ['Reaction Data', 'Reaction', '反应数据']
        
        standard_df = None
        for name in standard_names:
            if name in xl.sheet_names:
                standard_df = pd.read_excel(xl, sheet_name=name)
                break
        if standard_df is None:
            st.error("Standard Curve sheet not found")
            st.stop()
        
        reaction_df = None
        for name in reaction_names:
            if name in xl.sheet_names:
                reaction_df = pd.read_excel(xl, sheet_name=name)
                break
        if reaction_df is None:
            st.error("Reaction Data sheet not found")
            st.stop()
        
        # Clean column names
        standard_df.columns = standard_df.columns.str.strip()
        reaction_df.columns = reaction_df.columns.str.strip()
        
        # Map column names (support both English and Chinese)
        summary_col_map = {}
        reaction_col_map = {}
        
        # Summary sheet column mapping
        for col in standard_df.columns:
            col_lower = str(col).lower().strip()
            if col_lower == 'compound' or '4c' in col_lower or 'standard' in col_lower:
                summary_col_map['compound'] = col
            elif 'area' in col_lower or '峰面积' in col:
                summary_col_map['area'] = col
            elif 'concentration' in col_lower or '浓度' in col:
                summary_col_map['conc'] = col
        
        # Reaction sheet column mapping
        for col in reaction_df.columns:
            col_lower = str(col).lower().strip()
            if 'enzyme' in col_lower or '酶名称' in col:
                reaction_col_map['enzyme'] = col
            elif 'area' in col_lower or '峰面积' in col:
                reaction_col_map['area'] = col
            elif 'rt' in col_lower or 'retention' in col_lower or '保留时间' in col:
                reaction_col_map['rt'] = col
            elif 'compound' in col_lower or '物质' in col or '对应物质' in col:
                reaction_col_map['compound'] = col

        # ============ Scan RT Matches from Reaction Data ============
        rt_time_col = 'Retention_Time'
        if rt_time_col not in standard_df.columns:
            for col in standard_df.columns:
                if 'rt' in str(col).lower() or 'retention' in str(col).lower():
                    rt_time_col = col
                    break

        rxn_rt_col = 'Retention_Time'
        for col in reaction_df.columns:
            if 'rt' in str(col).lower() or 'retention' in str(col).lower():
                rxn_rt_col = col
                break

        rt_matches = scan_rt_matches(standard_df, reaction_df,
                                     std_compound_col=summary_col_map.get('compound', 'Compound'),
                                     std_rt_col=rt_time_col,
                                     rxn_rt_col=rxn_rt_col,
                                     tolerance=0.15)

        # Show RT match results
        st.subheader("🔬 RT Matching Results")
        match_data = []
        for compound, match in rt_matches.items():
            status = '✓' if match['is_match'] else '✗'
            match_data.append({
                'Compound': compound,
                'Std_RT': f"{match['std_rt']:.6f}",
                'Matched_RT': f"{match['matched_rt']:.6f}" if match['matched_rt'] else '-',
                'Deviation': f"{match['deviation']:+.6f}" if match['deviation'] else '-',
                'Status': status
            })
        st.dataframe(pd.DataFrame(match_data))

        # ============ Parse Reaction Data ============
        if 'enzyme' not in reaction_col_map or 'area' not in reaction_col_map:
            st.error("Required columns not found: Enzyme Name, Peak Area")
            st.stop()

        has_compound = 'compound' in reaction_col_map

        reactions = {}
        current_enzyme = None

        for idx, row in reaction_df.iterrows():
            enzyme = row.get(reaction_col_map.get('enzyme'))
            if pd.notna(enzyme) and str(enzyme).strip() != '':
                current_enzyme = str(enzyme).strip()
                reactions[current_enzyme] = {'products': [], 'GALD': 0}

            substance = row.get(reaction_col_map.get('compound')) if has_compound else None
            is_predicted = False
            rt_deviation = None

            if not has_compound or (pd.notna(substance) and str(substance).strip() == ''):
                rt_val = row.get(rxn_rt_col)
                if pd.notna(rt_val):
                    for compound, match in rt_matches.items():
                        if match['matched_rt'] and abs(float(rt_val) - match['matched_rt']) <= 0.001:
                            substance = compound
                            is_predicted = True
                            rt_deviation = match['deviation']
                            break

            if pd.notna(substance) and current_enzyme:
                peak = row[reaction_col_map['area']]
                substance = str(substance).strip()

                if substance == 'GALD':
                    reactions[current_enzyme]['GALD'] = peak
                else:
                    reactions[current_enzyme]['products'].append({
                        'name': substance,
                        'peak': peak,
                        'is_predicted': is_predicted,
                        'rt_deviation': rt_deviation
                    })

                if substance == 'GALD':
                    reactions[current_enzyme]['GALD'] = peak
                elif substance != 'Unknown':
                    reactions[current_enzyme]['products'].append({
                        'name': substance,
                        'peak': peak,
                        'is_predicted': is_predicted,
                        'rt_deviation': rt_deviation
                    })

        if not reactions:
            st.error("Reaction data not found")
            st.stop()

        # ============ Calculate Carbon Yield ============
        c4_sugar_names = ['Erythrose', 'Threose', 'Erythrulose', '赤藓糖', '苏阿糖', '赤藓酮糖']
        c4_mask = standard_df[summary_col_map['compound']].isin(c4_sugar_names)
        c4_standards = standard_df[c4_mask]

        if len(c4_standards) == 0:
            st.error("C4 sugar standard data not found")
            st.stop()

        c4_response = (c4_standards[summary_col_map['area']] / c4_standards[summary_col_map['conc']]).mean()
        
        gald_mask = standard_df[summary_col_map['compound']] == 'GALD'
        gald_row = standard_df[gald_mask]
        
        if len(gald_row) == 0:
            st.error("GALD standard data not found")
            st.stop()
        
        gald_response = gald_row[summary_col_map['area']].values[0] / gald_row[summary_col_map['conc']].values[0]

        st.success("Standard Curves calculated successfully!")
        st.markdown(f"""
        <div style="display: flex; gap: 40px; margin-top: 16px;">
            <div>
                <span style="color: #666; font-size: 14px;">C4 Sugar Response Factor</span><br>
                <span style="font-size: 18px; font-weight: 600;">{c4_response:.6f}</span>
            </div>
            <div>
                <span style="color: #666; font-size: 14px;">GALD Response Factor</span><br>
                <span style="font-size: 18px; font-weight: 600;">{gald_response:.6f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        results = []
        for enzyme, data in reactions.items():
            gald_carbon = (data['GALD'] / gald_response) * (2 * 12 / 60.05)
            total_product_carbon = 0
            products = []
            
            for prod in data['products']:
                cf = get_carbon_fraction(prod['name'])
                conc = prod['peak'] / c4_response
                carbon = conc * cf
                total_product_carbon += carbon
                products.append({'name': prod['name'], 'peak': prod['peak'], 'carbon': carbon})
            
            total = gald_carbon + total_product_carbon
            yield_pct = (total_product_carbon / total) * 100 if total > 0 else 0
            
            results.append({
                'enzyme': enzyme,
                'yield_pct': round(yield_pct, 2),
                'conversion_pct': round(100 - yield_pct, 2),
                'product_carbon': round(total_product_carbon, 4),
                'gald_carbon': round(gald_carbon, 4),
                'product_list': ', '.join([p['name'] for p in products]),
                'products': products,
                'gald_peak': data['GALD'],
            })
        
        results.sort(key=lambda x: x['yield_pct'], reverse=True)
        
        # ============ Display Results ============
        st.subheader("📊 Carbon Yield Ranking")
        
        display_df = pd.DataFrame([{
            'Rank': i+1,
            'Enzyme': r['enzyme'],
            'Carbon_Yield_%': r['yield_pct'],
            'Conversion_%': r['conversion_pct'],
            'Product_Carbon': r['product_carbon'],
            'GALD_Carbon': r['gald_carbon'],
        } for i, r in enumerate(results)])
        st.dataframe(display_df)
        
        # ============ Product Details ============
        st.subheader("📦 Product Details by Enzyme")

        for r in results:
            with st.expander(f"{r['enzyme']} ({r['yield_pct']}% yield)", expanded=False):
                product_data = []
                for prod in r['products']:
                    c_type = get_sugar_type(prod['name'])
                    conc = prod['peak'] / c4_response
                    product_data.append({
                        'Compound': prod['name'] + (" *" if prod.get('is_predicted') else ""),
                        'Type': c_type,
                        'Peak_Area': round(prod['peak'], 6),
                        'Concentration': round(conc, 6),
                        'Carbon_Mass': round(prod['carbon'], 6),
                        'RT_Deviation': f"{prod['rt_deviation']:+.6f}" if prod.get('rt_deviation') else '-'
                    })
                st.dataframe(pd.DataFrame(product_data))
        
        st.subheader("📈 Visualization")
        df_chart = pd.DataFrame(results)

        chart = alt.Chart(df_chart).mark_bar(cornerRadiusEnd=4).encode(
            x=alt.X('enzyme', title='Enzyme', sort='-y'),
            y=alt.Y('yield_pct', title='Carbon Yield (%)', scale=alt.Scale(domain=[0, 100])),
            color=alt.Color('yield_pct', scale=alt.Scale(domain=[0, 100], range=['#90CAF9', '#1565C0']), legend=None),
            tooltip=['enzyme', 'yield_pct', 'conversion_pct', 'product_carbon']
        ).properties(
            height=350,
            width=600
        ).configure_axis(
            labelFontSize=12,
            titleFontSize=14
        )

        st.altair_chart(chart, use_container_width=True)
        
        # ============ Download Button ============
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            excel_data = export_to_excel(results, c4_response, gald_response)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="📥 Download Excel Results",
                data=excel_data,
                file_name=f"Carbon_Yield_Results_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col2:
            st.info("Click to download complete results including summary, details, and standard curves")
            
    except Exception as e:
        st.error(f"Error: {e}")

else:
    st.info("Upload an Excel file to begin analysis")
