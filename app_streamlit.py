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

# Substrate database for carbon yield calculation
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
    c4_sugars = ['Erythrose', 'Threose', 'Erythrulose', '赤藓糖', '苏阿糖', '赤藓酮糖']
    if name in c4_sugars:
        return 'C4'
    return 'C6'

def build_rt_reference(standard_df, compound_col='Compound', rt_col='Retention_Time'):
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

def export_to_excel(results, c4_response, substrate_info, substrate_response):
    """Export results to Excel"""
    output = BytesIO()
    substrate_name = substrate_info['name']
    substrate_c_type = substrate_info['c_type']
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = []
        for i, r in enumerate(results, 1):
            summary_data.append({
                'Rank': i,
                'Enzyme': r['enzyme'],
                'Substrate': r['substrate'],
                'Carbon_Yield_%': r['yield_pct'],
                'Conversion_%': r['conversion_pct'],
                'Product_Carbon_mgC_mL': r['product_carbon'],
                f'{substrate_name}_Carbon_mgC_mL': r['substrate_carbon'],
            })
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Carbon_Yield_Summary', index=False)
        
        # Individual enzyme sheets
        for r in results:
            sheet_name = r['enzyme'].replace(' ', '_')[:31]
            detail_data = []
            # Substrate
            detail_data.append({
                'Compound': f'{substrate_name} (Remaining)',
                'Type': substrate_c_type,
                'Peak_Area': r.get('substrate_peak', 0),
                'Concentration_mg_mL': r['substrate_carbon'] / (substrate_info['carbon'] * 12 / substrate_info['mw']),
                'Carbon_Mass_mgC_mL': r['substrate_carbon'],
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
            {'Sugar_Type': substrate_c_type, 'Response_Factor': substrate_response, 'Carbon_Fraction': substrate_info['carbon']*12/substrate_info['mw']},
        ]
        pd.DataFrame(std_data).to_excel(writer, sheet_name='Standard_Curves', index=False)
    
    return output.getvalue()

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
| Enzyme | Enzyme name (fill in first row only, leave blank for subsequent peaks) |
| substrate | Substrate name for carbon yield calculation (optional, if not provided will show dropdown) |
| Retention_Time | Retention time in minutes |
| Peak_Area | Peak area from chromatograph |
| Compound | Compound name (optional, will do RT matching if empty) |

---

**📌 Supported Compounds:**
- C4 Sugars: Erythrose, Threose, Erythrulose
- C6 Sugars: Glucose, Fructose, Mannose, Galactose, Sorbose, etc.
- C2: GALD (Glyceraldehyde)
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
            elif 'substrate' in col_lower or '底物' in col:
                reaction_col_map['substrate'] = col
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

        # ============ Parse Reaction Data with RT Matching ============
        if 'enzyme' not in reaction_col_map or 'area' not in reaction_col_map:
            st.error("Required columns not found: Enzyme Name, Peak Area")
            st.stop()

        has_compound = 'compound' in reaction_col_map
        has_substrate = 'substrate' in reaction_col_map
        tolerance = 0.15

        reactions = {}
        current_enzyme = None
        current_substrate = None  # Store substrate per enzyme
        rt_predictions = []

        for idx, row in reaction_df.iterrows():
            enzyme = row.get(reaction_col_map.get('enzyme'))

            if has_substrate:
                substrate_val = row.get(reaction_col_map.get('substrate'))
                if pd.notna(substrate_val):
                    current_substrate = normalize_compound_name(substrate_val)

            if pd.notna(enzyme) and str(enzyme).strip() != '':
                current_enzyme = str(enzyme).strip()
                reactions.setdefault(
                    current_enzyme,
                    {'substrate': current_substrate, 'substrate_peaks': {}, 'products': []}
                )
            elif current_enzyme:
                reactions.setdefault(
                    current_enzyme,
                    {'substrate': current_substrate, 'substrate_peaks': {}, 'products': []}
                )

            if not current_enzyme:
                continue

            substance = normalize_compound_name(row.get(reaction_col_map.get('compound'))) if has_compound else None
            is_predicted = False
            rt_deviation = None
            rt_val = None

            if not substance and has_substrate:
                substrate_in_row = row.get(reaction_col_map.get('substrate'))
                if pd.notna(substrate_in_row):
                    substance = normalize_compound_name(substrate_in_row)

            if not substance:
                rt_val = row.get(rxn_rt_col)
                if pd.notna(rt_val):
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
                        substance = normalize_compound_name(best_match)
                        is_predicted = True
                    else:
                        substance = 'Unknown'

            if pd.notna(substance):
                peak = row[reaction_col_map['area']]
                substance = str(substance).strip()

                rt_predictions.append({
                    'Enzyme': current_enzyme,
                    'RT': round(float(rt_val), 6) if pd.notna(rt_val) else None,
                    'Compound': substance if substance != 'Unknown' else None,
                    'RT_Deviation': f"{rt_deviation:+.6f}" if rt_deviation is not None else '-',
                    'Peak_Area': round(peak, 6)
                })

                # Check if substance is a known substrate
                if substance in SUBSTRATE_DB:
                    reactions[current_enzyme]['substrate_peaks'][substance] = peak
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

        # Show RT matching results by Enzyme
        st.subheader("🔬 RT Matching Results by Enzyme")
        if rt_predictions:
            pred_df = pd.DataFrame(rt_predictions)
            st.dataframe(pred_df)

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
        
        # ============ Substrate Detection ============
        has_substrate_col = 'substrate' in reaction_col_map
        
        st.markdown("---")
        
        if has_substrate_col:
            # Auto-detect substrate from data
            substrates_in_data = set()
            for idx, row in reaction_df.iterrows():
                substrate = row.get(reaction_col_map.get('substrate'))
                if pd.notna(substrate):
                    substrates_in_data.add(normalize_compound_name(substrate))
            
            if substrates_in_data:
                if len(substrates_in_data) == 1:
                    selected_substrate = list(substrates_in_data)[0]
                    st.success(f"Detected substrate: {selected_substrate}")
                else:
                    st.warning(f"Multiple substrates detected: {substrates_in_data}. Using the first one.")
                    selected_substrate = list(substrates_in_data)[0]
            else:
                st.error("Substrate column found but no valid substrate values.")
                st.stop()
        else:
            # Show dropdown for substrate selection
            st.subheader("🎯 Select Substrate for Carbon Yield Calculation")
            
            available_substrates = set()
            for enzyme, data in reactions.items():
                available_substrates.update(data['substrate_peaks'].keys())
            
            substrate_options = get_substrate_list()
            
            if available_substrates:
                st.info(f"Detected substrates in data: {', '.join(available_substrates)}")
            
            selected_substrate = st.selectbox(
                "Choose substrate for carbon yield calculation:",
                options=substrate_options,
                index=substrate_options.index('GALD') if 'GALD' in substrate_options else 0
            )
        
        # Get substrate info
        if selected_substrate in SUBSTRATE_DB:
            substrate_info = SUBSTRATE_DB[selected_substrate]
        else:
            # Unknown substrate - use default C4 properties
            substrate_info = {'mw': 120.10, 'carbon': 4, 'c_type': 'C4'}
            st.warning(f"{selected_substrate} not in database, assuming C4 sugar properties.")
        
        # Calculate response factor for selected substrate
        if substrate_info['c_type'] == 'C4':
            substrate_response = c4_response
            st.info(f"{selected_substrate} is a C4 sugar, using C4 response factor.")
        else:
            substrate_mask = standard_df[summary_col_map['compound']] == selected_substrate
            substrate_row = standard_df[substrate_mask]
            
            if len(substrate_row) == 0:
                st.warning(f"{selected_substrate} standard data not found. Using C4 response factor as fallback.")
                substrate_response = c4_response
            else:
                substrate_response = substrate_row[summary_col_map['area']].values[0] / substrate_row[summary_col_map['conc']].values[0]

        st.success("Standard Curves calculated successfully!")
        st.markdown(f"""
        <div style="display: flex; gap: 40px; margin-top: 16px;">
            <div>
                <span style="color: #666; font-size: 14px;">C4 Sugar Response Factor</span><br>
                <span style="font-size: 18px; font-weight: 600;">{c4_response:.6f}</span>
            </div>
            <div>
                <span style="color: #666; font-size: 14px;">{selected_substrate} Response Factor</span><br>
                <span style="font-size: 18px; font-weight: 600;">{substrate_response:.6f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ============ Calculate Carbon Yield ============
        results = []
        for enzyme, data in reactions.items():
            # Get substrate peak for selected substrate
            substrate_peak = data['substrate_peaks'].get(selected_substrate, 0)
            substrate_carbon = (substrate_peak / substrate_response) * (substrate_info['carbon'] * 12 / substrate_info['mw'])
            
            total_product_carbon = 0
            products = []
            
            for prod in data['products']:
                cf = get_carbon_fraction(prod['name'])
                conc = prod['peak'] / c4_response
                carbon = conc * cf
                total_product_carbon += carbon
                products.append({'name': prod['name'], 'peak': prod['peak'], 'carbon': carbon})
            
            total = substrate_carbon + total_product_carbon
            yield_pct = (total_product_carbon / total) * 100 if total > 0 else 0
            
            results.append({
                'enzyme': enzyme,
                'yield_pct': round(yield_pct, 2),
                'conversion_pct': round(100 - yield_pct, 2),
                'product_carbon': round(total_product_carbon, 4),
                'substrate_carbon': round(substrate_carbon, 4),
                'substrate': selected_substrate,
                'product_list': ', '.join([p['name'] for p in products]),
                'products': products,
                'substrate_peak': substrate_peak,
            })
        
        results.sort(key=lambda x: x['yield_pct'], reverse=True)
        
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
                    c_type = get_sugar_type(prod['name'])
                    conc = prod['peak'] / c4_response
                    product_data.append({
                        'Compound': prod['name'] + (" *" if prod.get('is_predicted') else ""),
                        'Type': c_type,
                        'Peak_Area': round(prod['peak'], 6),
                        'Concentration': round(conc, 6),
                        'Carbon_Mass': round(prod['carbon'], 6),
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
        
        col1, col2 = st.columns(2)
        with col1:
            # Handle unknown substrate for Excel export
            if selected_substrate in SUBSTRATE_DB:
                substrate_info_dict = {'name': selected_substrate, **SUBSTRATE_DB[selected_substrate]}
            else:
                substrate_info_dict = {'name': selected_substrate, 'mw': 120.10, 'carbon': 4, 'c_type': 'C4'}
            excel_data = export_to_excel(results, c4_response, substrate_info_dict, substrate_response)

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
