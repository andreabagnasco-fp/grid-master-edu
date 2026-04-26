import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Grid Master Console v5.10.0", layout="wide")

COSTI = {
    "RES": 0, "HYDRO": 40, "IMPORT": 60, "GAS": 95,
    "PENALE_TOP": 60, "PENALE_TAGLIO": 3000,
    "STANDBY_GAS": 2.0,
    "STANDBY_HYDRO": 1.0
}

def genera_meteo_v5_8():
    t_steps = np.linspace(0, 24, 144)
    sky_power = np.random.choice([1.0, 0.7, 0.2], p=[0.5, 0.3, 0.2])
    base_fv = 500 * np.maximum(0, np.sin(np.pi * (t_steps - 6) / 12))**1.8
    st.session_state.fv_real = base_fv * sky_power * np.clip(np.random.normal(1.0, 0.12, 144), 0.1, 1.2)

    wind = np.zeros(144)
    wind[0] = np.random.uniform(100, 250)
    for i in range(1, 144):
        step = np.random.normal(0, 45) if np.random.random() > 0.9 else np.random.normal(0, 10)
        wind[i] = np.clip(wind[i-1] + step, 10, 480)
    st.session_state.wind_real = wind

    # BUG FIX 1: corretto st.session_state.sky_desc (era diventato un link Markdown)
    st.session_state.sky_desc = "☀️ Sereno" if sky_power > 0.8 else "⛅ Variabile" if sky_power > 0.3 else "⛈️ Critico"

    st.session_state.fv_pre = pd.Series(st.session_state.fv_real * np.random.uniform(0.9, 1.1)).rolling(12, min_periods=1).mean().values
    st.session_state.wind_pre = pd.Series(st.session_state.wind_real * np.random.uniform(0.85, 1.15)).rolling(12, min_periods=1).mean().values

if 'fv_real' not in st.session_state:
    genera_meteo_v5_8()

# --- HEADER CON LOGO DELLA SCUOLA ---
col_logo, col_titolo = st.columns([1, 8]) # Rapporto tra larghezza logo e titolo

with col_logo:
    st.image("logo-fp-piccolo.png", width=80) # Regola width se il logo appare troppo grande/piccolo

with col_titolo:
    st.title("Grid Master")
st.caption(f"Mantieni sicura la rete minimizzando i costi e le emissioni di CO2. | Meteo: {st.session_state.sky_desc}")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🕹️ Pannello di Controllo")
    scenario = st.selectbox("Seleziona Scenario", ["Standard", "Crollo Improvviso FV", "Blackout Eolico", "Picco di Domanda"])
    st.divider()
    p_import_target = st.slider("Import Programmato (MW)", 0, 800, 400)
    p_hydro_max = st.slider("Potenza Dispacciabile Idro (MW)", 0, 500, 250)
    p_gas_max = st.slider("Potenza Dispacciabile Gas (MW)", 0, 1000, 500)
    
    # Riquadro Costi Stand-by
    st.info(f"💡 Costo Stand-by: Idro €{COSTI['STANDBY_HYDRO']}/MW | Gas €{COSTI['STANDBY_GAS']}/MW")
    
    # --- NUOVO BOX CONTRATTO IMPORT (SPOSTATO QUI) ---
    costo_giornaliero_import = p_import_target * 24 * 60
    st.info(f"""
    💡**Contratto import: {p_import_target} MW vincolati.** Costo: 60 €/MWh (sia che prelevi, sia che non prelevi)  
    **Impegno totale: {costo_giornaliero_import:,.0f} €**
    """)
    
    st.divider()
    st.subheader("⚖️ Pesi Etici (distacco carichi)")
    w_osp = st.slider("Ospedali", 0, 100, 100)
    w_res = st.slider("Residenziale", 0, 100, 60)
    w_ind = st.slider("Industrie", 0, 100, 20)

# --- LOGICA SCENARI ---
t = np.linspace(0, 24, 144)
dt = 10/60
carico = (750 + 200 * np.exp(-((t - 11)**2) / 10) + 400 * np.exp(-((t - 20)**2) / 6))
if scenario == "Picco di Domanda":
    carico *= 1.2

# --- UI PREVISIONALE ---
st.subheader("📋 Analisi Previsionale (Day-Ahead)")
c_t, c_g = st.columns([1, 2.5])

with c_t:
    st.write("**Parametri Economici:**")
    st.table(pd.DataFrame({
        "Voce": ["RES", "Idro", "Import", "Gas", "Penale ToP", "Distacco"],
        "€/MWh": [COSTI["RES"], COSTI["HYDRO"], COSTI["IMPORT"], COSTI["GAS"], COSTI["PENALE_TOP"], COSTI["PENALE_TAGLIO"]]
    }))

    if st.button("🔄 Rigenera Meteo"):
        genera_meteo_v5_8()
        st.rerun()

with c_g:
    fig_pre = go.Figure()
    # Grafico previsionale NON impilato (intenzionale): fill='tozeroy' per tutte le tracce
    fig_pre.add_trace(go.Scatter(x=t, y=np.full(144, p_import_target), name="Import Programmato",
        fill='tozeroy', fillcolor='rgba(128, 128, 128, 0.4)', line=dict(color='gray', width=2)))
    fig_pre.add_trace(go.Scatter(x=t, y=st.session_state.wind_pre, name="Eolico (Previsto)",
        fill='tozeroy', fillcolor='rgba(0, 191, 255, 0.4)', line=dict(color='#00BFFF', width=2)))
    fig_pre.add_trace(go.Scatter(x=t, y=st.session_state.fv_pre, name="FV (Previsto)",
        fill='tozeroy', fillcolor='rgba(255, 215, 0, 0.4)', line=dict(color='#FFD700', width=2)))
    fig_pre.add_trace(go.Scatter(x=t, y=carico, name="Domanda",
        line=dict(color='black', dash='dash', width=2)))
    fig_pre.update_layout(height=320, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_pre, use_container_width=True)

# --- SIMULAZIONE ---
if st.button("▶️ AVVIA SIMULAZIONE", type="primary"):
    fv = st.session_state.fv_real.copy()
    if scenario == "Crollo Improvviso FV":
        fv[70:100] *= 0.1
    wind = st.session_state.wind_real.copy()
    if scenario == "Blackout Eolico":
        wind[50:] *= 0.2

    f, p_gas, p_hyd, p_tag, p_imp_act = [50.0], [], [], [], []
    co2_accumulata = [0]
    costo_op, mwh_top, energia_tot = 0, 0, 0
    tagli = {"Ospedali": 0, "Residenziale": 0, "Industrie": 0}

    for i in range(144):
        gen_res = fv[i] + wind[i]
        imp_act = p_import_target
        hyd, gas, tag = 0, 0, 0
        # BUG FIX 2: deficit inizializzato a 0 per evitare NameError nel ramo surplus
        deficit = 0

        net = carico[i] - (gen_res + imp_act)

        if net < 0:  # Surplus
            cut = min(abs(net), imp_act)
            imp_act -= cut
            mwh_top += (cut * dt)
            net += cut
        else:  # Deficit
            hyd = np.clip(net, 0, p_hydro_max)
            gas = np.clip(net - hyd, 0, p_gas_max)
            
        # AGC — la frequenza risponde al bilancio FISICO reale, prima di qualsiasi taglio
        # Questo è il cuore del modello: la f scende quando manca potenza, sale quando avanza
        bilancio_fisico = (gen_res + imp_act + hyd + gas) - carico[i]
        fn = f[-1] * 0.995 + 50.0 * 0.005 + (bilancio_fisico * 0.00008)

        # Load shedding: scatta DOPO che la frequenza è già scesa, come nella realtà
        if fn < 49.7:
            deficit_hz = 49.7 - fn
            tag = np.clip(deficit_hz / 0.00008 * 1.2, 0, 400)
            prio = sorted(
                [("Ospedali", w_osp), ("Residenziale", w_res), ("Industrie", w_ind)],
                key=lambda x: (x[1], ["Industrie", "Residenziale", "Ospedali"].index(x[0]))
            )
            tagli[prio[0][0]] += tag * dt
            fn += tag * 0.00008  # la frequenza risale parzialmente dopo il taglio

        # Integrazione energetica & CO2
        costo_op += (imp_act*COSTI["IMPORT"] + hyd*COSTI["HYDRO"] + gas*COSTI["GAS"] + tag*COSTI["PENALE_TAGLIO"]) * dt
        energia_tot += (carico[i] * dt)
        co2_accumulata.append(co2_accumulata[-1] + (gas * dt * 0.45))

        f.append(fn)
        p_gas.append(gas)
        p_hyd.append(hyd)
        p_tag.append(tag)
        p_imp_act.append(imp_act)

    # CALCOLO FINALE COSTI
    extra_costo_top = mwh_top * COSTI["PENALE_TOP"]
    costo_standby = (p_gas_max * COSTI["STANDBY_GAS"]) + (p_hydro_max * COSTI["STANDBY_HYDRO"])
    mwh_taglio_tot = sum(p_tag) * dt
    costo_taglio_totale = mwh_taglio_tot * COSTI["PENALE_TAGLIO"]
    costo_totale = costo_op + extra_costo_top + costo_standby
    costo_medio = costo_totale / energia_tot if energia_tot > 0 else 0

    # --- LOGICA DI VALUTAZIONE FREQUENZA v5.9.2 ---
    deviazione_max = np.max(np.abs(np.array(f) - 50.0))
    freq_instabile = deviazione_max > 0.05   # Qualità del servizio scadente
    freq_in_allarme = deviazione_max > 0.2    # Rischio serio
    freq_fuori_range = deviazione_max > 0.5   # Blackout (Soglia Terna/ENTSO-E)

    # --- OUTPUT ---
    st.divider()
    st.markdown("### 🤖 AI Dispatch Debriefing")

    gestione_perfetta = True

    # 1. Controllo Frequenza (Priorità Massima)
    if freq_fuori_range:
        gestione_perfetta = False
        valore_estremo = np.max(f) if np.max(f) > 50 else np.min(f)
        st.error(f"🚨 **BLACKOUT TOTALE!** La frequenza ha raggiunto i {valore_estremo:.2f} Hz. Il sistema è collassato!")
    elif freq_in_allarme:
        gestione_perfetta = False
        st.warning(f"⚠️ **RETE IN ALLARME:** Scostamento critico ({deviazione_max:.2f} Hz). Protezioni di interfaccia vicine allo sgancio automatico!")
    elif freq_instabile:
        gestione_perfetta = False
        # Diagnosi: se il valore massimo è sopra 50.05, la causa è l'eccesso
        causa = "Eccesso di produzione (Rinnovabili non compensate)" if np.max(f) > 50.05 else "Deficit di generazione"
        st.warning(f"⚖️ **Instabilità di Frequenza:** La rete ha oscillato fuori dai parametri di qualità nominali (Max deviazione: {deviazione_max:.3f} Hz). Causa probabile: {causa}.")

    if mwh_taglio_tot > 0:
        gestione_perfetta = False
        if mwh_taglio_tot > 10 or costo_medio > 75:
            st.error(f"✂️ **Distacco Carichi Grave:** Hai perso {mwh_taglio_tot:.1f} MWh! Penali per {int(costo_taglio_totale)} €. Peggior impatto su: {max(tagli, key=tagli.get)}.")
        else:
            st.warning(f"✂️ **Distacco Carichi Contenuto:** Rete in lieve deficit ({mwh_taglio_tot:.1f} MWh persi). Il sistema ha retto al limite.")

    if mwh_top > 20:
        gestione_perfetta = False
        st.warning("💸 **Sovrastima Import:** Le rinnovabili hanno coperto la domanda e hai dovuto tagliare le importazioni, pagando le penali Take-or-Pay.")

    if sum(p_gas) > sum(p_hyd) * 2:
        gestione_perfetta = False
        st.warning("🏭 **Inquinamento e Costi:** Uso eccessivo del Gas. Potevi ottimizzare le riserve o l'import per abbattere emissioni e costi.")

    if costo_standby > 1500:
        gestione_perfetta = False
        st.warning("🪫 **Eccesso di Sicurezza:** Troppe centrali in stand-by inutilmente. I costi di disponibilità hanno alzato la bolletta.")

    if gestione_perfetta and costo_medio < 50:
        st.success("🌟 **Ottimo:** Rete stabile, riserve dimensionate al millimetro e costo medio ottimizzato. Gestione impeccabile.")

    st.write("")

    # KPI — prima riga
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("💰 Costo Medio", f"{costo_medio:.2f} €/MWh")
    k2.metric("⚠️ Extra-costo ToP", f"€ {int(extra_costo_top)}")
    k3.metric("⚙️ Stand-by", f"€ {int(costo_standby)}")
    k4.metric("✂️ Penale Distacco", f"€ {int(costo_taglio_totale)}")
    k5.metric("☁️ CO2 Totale", f"{int(co2_accumulata[-1])} ton")

    # KPI — seconda riga
    j1, j2, j3, j4, j5 = st.columns(5)
    j1.write("")
    j2.metric("📉 Import Rifiutato", f"{mwh_top:.1f} MWh", delta_color="inverse")
    j3.write("")
    j4.metric("🔌 Carico Distaccato", f"{mwh_taglio_tot:.1f} MWh", delta_color="inverse")
    j5.write("")

    # GRAFICO TAKE-OR-PAY
    st.subheader("📉 Analisi Import e Penali Take-or-Pay")
    fig_top = go.Figure()
    fig_top.add_trace(go.Scatter(x=t, y=[p_import_target]*144, name="Import Programmato (Contratto)",
        line=dict(color='black', dash='dash', width=2)))
    fig_top.add_trace(go.Scatter(x=t, y=p_imp_act, name="Import Effettivo (Prelevato)",
        fill='tonexty', fillcolor='rgba(255, 0, 0, 0.3)', line=dict(color='red')))
    fig_top.update_layout(height=200, margin=dict(l=0, r=0, t=20, b=0),
        yaxis_title="MW", yaxis=dict(range=[0, max(800, p_import_target + 100)]))
    st.plotly_chart(fig_top, use_container_width=True)

    # GRAFICI REALI CON CO2
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📊 Bilancio Energetico Reale")
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatter(x=t, y=p_imp_act, name="Import", stackgroup='1', fillcolor='gray'))
        fig_r.add_trace(go.Scatter(x=t, y=wind, name="Eolico", stackgroup='1', fillcolor='#00BFFF'))
        fig_r.add_trace(go.Scatter(x=t, y=fv, name="FV", stackgroup='1', fillcolor='#FFD700'))
        fig_r.add_trace(go.Scatter(x=t, y=p_hyd, name="Idro", stackgroup='1', fillcolor='#3498db'))
        fig_r.add_trace(go.Scatter(x=t, y=p_gas, name="Gas", stackgroup='1', fillcolor='#95a5a6'))
        fig_r.add_trace(go.Scatter(x=t, y=p_tag, name="TAGLIO CARICHI", stackgroup='1', fillcolor='#FF0000'))
        fig_r.add_trace(go.Scatter(x=t, y=carico, name="Domanda", line=dict(color='black', width=3)))
        st.plotly_chart(fig_r, use_container_width=True)

    with c2:
        st.subheader("📈 Sistema & Emissioni")
        fig_sys = make_subplots(specs=[[{"secondary_y": True}]])
        fig_sys.add_trace(go.Scatter(x=t, y=f[1:], name="Hz",
            line=dict(color='orange')), secondary_y=False)
        fig_sys.add_trace(go.Scatter(x=t, y=co2_accumulata[1:], name="CO2",
            line=dict(color='purple', dash='dot')), secondary_y=True)
        fig_sys.update_yaxes(title_text="Frequenza (Hz)", range=[49.5, 50.5], secondary_y=False)
        fig_sys.update_yaxes(title_text="CO2 Cumulata (ton)", secondary_y=True)
        fig_sys.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_sys, use_container_width=True)

        if freq_fuori_range:
            st.error("⚠️ ALLARME: RETE INSTABILE — BLACKOUT!")
        elif freq_in_allarme:
            st.warning("⚠️ ATTENZIONE: FREQUENZA IN ZONA DI ALLARME")

    if mwh_taglio_tot > 0:
        st.subheader("🌐 Valutazione Impatto Sociale")
        if tagli["Ospedali"] > 0:
            st.error("🚨 **EMERGENZA ETICA:** Il distacco ha colpito le infrastrutture critiche (Ospedali). Questa è considerata una gestione fallimentare del sistema di difesa.")
        elif tagli["Residenziale"] > 0:
            st.warning("🏠 **DISAGIO CIVILE:** Il distacco ha interessato le utenze domestiche. Hai protetto gli ospedali, ma migliaia di cittadini sono rimasti al buio.")
        else:
            # BUG FIX 1: corretto st.info (era diventato un link Markdown)
            st.info("🏭 **SCELTA TECNICA:** Il distacco è stato isolato al settore Industriale. Hai sacrificato la produzione economica per proteggere i servizi essenziali e la stabilità della rete.")
