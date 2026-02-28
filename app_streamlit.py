#!/usr/bin/env python3
"""
CarbonOracle - Carbon Yield Calculator
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

SUBSTRATE_DB = {
    'GALD': {'mw': 60.05, 'carbon': 2, 'c_type': 'C2'},
    'Erythrose': {'mw': 120.10, 'carbon': 4, 'c_type': 'C4'},
    'Threose': {'mw': 120.10, 'carbon': 4, 'c_type': 'C4'},
    'Erythrulose': {'mw': 120.10, 'carbon': 4, 'c_type': 'C4'},
    'Glucose': {'mw': 180.16, 'carbon': 6, 'c_type': 'C6'},
    'Fructose': {'mw': 180.16, 'carbon': 6, 'c_type': 'C6'},
    'Mannose': {'mw': 180.16, 'carbon': 6, 'c_type': 'C6'},
    'Galactose': {'mw': 180.16, 'carbon': 6, 'c_type': 'C6'},
    'Sorbose': {'mw': 180.16, 'carbon': 6, 'c_type': 'C6'},
    'Tagatose': {'mw': 180.16, 'carbon': 6, 'c_type': 'C6'},
    'Gulose': {'mw': 180.16, 'carbon': 6, 'c_type': 'C6'},
    'Altrose': {'mw': 180.16, 'carbon': 6, 'c_type': 'C6'},
    'Allose': {'mw': 180.16, 'carbon': 6, 'c_type': 'C6'},
    'Idose': {'mw': 180.16, 'carbon': 6, 'c_type': 'C6'},
    'Talose': {'mw': 180.16, 'carbon': 6, 'c_type': 'C6'},
    'Psicose': {'mw': 180.16, 'carbon': 6, 'c_type': 'C6'},
}

COMPOUND_ALIASES = {
    'Psychose': 'Psicose',
}

def get_substrate_list():
    return list(SUBSTRATE_DB.keys())

def normalize_compound_name(name):
    if pd.isna(name):
        return None
    normalized = str(name).strip()
    return COMPOUND_ALIASES.get(normalized, normalized)

def get_carbon_fraction(name):
    db = MOLECULAR_DB.get(name, {'mw': 120.10, 'carbon': 4})
    return db['carbon'] * 12 / db['mw']

def get_sugar_type(name):
    c4_sugars = ['Erythrose', 'Threose', 'Erythrulose']
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

st.title("🔬 CarbonOracle")

st.markdown("""
**Carbon Yield Calculator for Enzymatic Reactions**

*Upload your LC/GC data and calculate carbon yield automatically.*

---

**📋 Excel File Format:**

**Sheet 1: Standard Curve** (required)
| Column | Description |
|--------|-------------|
| Compound | Compound name (e.g., Erythrose, Threose, GALD, Glucose...) |
| Retention_Time | Retention time in minutes |
| Peak_Area | Peak area from chromatograph |
| Concentration | Concentration in mg/ml |

**Sheet 2: Reaction Data** (required)
| Column | Description |
|--------|-------------|
| Enzyme | Enzyme name |
| Substrate | Substrate name for carbon yield calculation |
| Retention_Time | Retention time in minutes |
| Peak_Area | Peak area from chromatograph |

---
""")

uploaded_file = st.file_uploader("Choose Excel File", type=['xlsx', 'xls'])

if uploaded_file:
    try:
        xl = pd.ExcelFile(uploaded_file)
        
        # Read data
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
        
        # Find RT columns
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
        
        # Scan RT matches
        rt_matches = scan_rt_matches(standard_df, reaction_df,
                                     std_compound_col=summary_col_map.get('compound', 'Compound'),
                                     std_rt_col=rt_time_col,
                                     rxn_rt_col=rxn_rt_col,
                                     tolerance=0.15)
        
        # Parse reaction data - SIMPLIFIED
        if 'enzyme' not in reaction_col_map or 'area' not in reaction_col_map:
            st.error("Required columns not found: Enzyme Name, Peak Area")
            st.stop()
        
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
                current_substrate = normalize_compound_name(substrate_val)
            
            # Update enzyme
            if pd.notna(enzyme) and str(enzyme).strip() != '':
                current_enzyme = str(enzyme).strip()
                reactions.setdefault(current_enzyme, {
                    'substrate': current_substrate,
                    'peaks': []  # List of (compound, peak, is_substrate)
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
                    compound_from_col = normalize_compound_name(compound_val)
            
            rt_val = row.get(rxn_rt_col)
            is_predicted = False
            rt_deviation = None
            
            if compound_from_col:
                pred_compound = compound_from_col
            elif pd.notna(rt_val):
                best_match = None
                best_dev = None
                for compound, match in rt_matches.items():
                    dev = float(rt_val) - match['std_rt']
                    abs_dev = abs(dev)
                    if abs_dev <= tolerance:
                        if best_match is None or abs_dev < best_dev:
                            best_match = compound
                            best_dev = abs_dev
                            rt_deviation = round(dev, 6)
                if best_match:
                    pred_compound = normalize_compound_name(best_match)
                    is_predicted = True
                else:
                    pred_compound = 'Unknown'
            else:
                pred_compound = None
            
            if not pred_compound:
                continue
            
            peak = row[reaction_col_map['area']]
            
            # Determine if this peak is substrate or product
            is_substrate = (pred_compound == current_substrate)
            
            # Record peak
            reactions[current_enzyme]['peaks'].append({
                'compound': pred_compound,
                'peak': peak,
                'is_substrate': is_substrate,
                'rt': rt_val,
                'is_predicted': is_predicted,
                'rt_deviation': rt_deviation
            })
            
            # For display
            rt_predictions.append({
                'Enzyme': current_enzyme,
                'RT': round(float(rt_val), 6) if pd.notna(rt_val) else None,
                'pred_compound': pred_compound if pred_compound != 'Unknown' else None,
                'Substrate': current_substrate,
                'Is_Substrate': is_substrate,
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
        
        # ============ Calculate Carbon Yield ============
        c4_sugar_names = ['Erythrose', 'Threose', 'Erythrulose']
        c4_mask = standard_df[summary_col_map['compound']].isin(c4_sugar_names)
        c4_standards = standard_df[c4_mask]
        
        if len(c4_standards) == 0:
            st.error("C4 sugar standard data not found")
            st.stop()
        
        c4_response = (c4_standards[summary_col_map['area']] / c4_standards[summary_col_map['conc']]).mean()
        
        st.markdown("---")
        
        # Auto-detect substrates
        if has_substrate:
            substrates_in_data = set()
            for idx, row in reaction_df.iterrows():
                substrate = row.get(reaction_col_map.get('substrate'))
                if pd.notna(substrate):
                    substrates_in_data.add(normalize_compound_name(substrate))
            
            if substrates_in_data:
                st.success(f"Detected substrates: {', '.join(substrates_in_data)}")
        
        # Calculate carbon yield for each enzyme
        results = []
        for enzyme, data in reactions.items():
            substrate = data['substrate']
            peaks = data['peaks']
            
            # Calculate carbon
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
