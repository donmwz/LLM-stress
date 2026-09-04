
import asyncio
import json
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from config import TestConfig, RequestStatus
from engine import AsyncEngine
from metrics import compute_metrics
from chart_data import build_timeline_df, build_throughput_df, build_comparison_df
from logger import build_export_payload
from exporters import export_to_csv_string, export_to_html_string

from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="LLM Stress Lab", page_icon="◌", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
        :root { --ink:#172033; --muted:#687386; --line:#e7eaf0; --surface:#fff; --accent:#635bff; }
        .stApp { background: #f7f8fa; color: var(--ink); }

        .block-container {
            padding: 2.25rem 2.5rem 4rem;
            max-width: 1440px;
        }

        [data-testid="stSidebar"] {
            background: rgba(255,255,255,.96);
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] > div {
            padding-top: 1.25rem;
        }

        .hero-card {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 1.75rem 1.9rem;
            box-shadow: 0 1px 2px rgba(16,24,40,.03);
            margin-bottom: 1.5rem;
        }

        .eyebrow {
            font-size: 0.7rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #635bff;
            font-weight: 700;
            margin-bottom: 0.45rem;
        }

        .hero-card h1 {
            margin: 0 0 0.3rem 0;
            font-size: clamp(1.9rem, 2.6vw, 2.6rem);
            line-height: 1.12;
            color: var(--ink);
            letter-spacing: -.035em;
        }

        .hero-card p {
            margin: 0;
            color: var(--muted);
            font-size: 0.98rem;
            line-height: 1.5;
        }

        .section-shell {
            margin-top: 1.2rem;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: .75rem;
            margin: 1rem 0 1.4rem;
        }

        .stat-card {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 1rem 1.05rem;
            box-shadow: none;
        }

        .stat-card .label {
            font-size: 0.68rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 0.45rem;
            font-weight: 700;
        }

        .stat-card .value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--ink);
            line-height: 1.2;
        }

        .stat-card .sub {
            font-size: 0.8rem;
            color: var(--muted);
            margin-top: 0.25rem;
        }

        .stButton > button,
        .stDownloadButton > button {
            background: var(--accent);
            color: #ffffff;
            border: 1px solid var(--accent);
            border-radius: 12px;
            font-weight: 600;
            padding: 0.7rem 1rem;
            box-shadow: none;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            background: #5149e8;
            border-color: #5149e8;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 0.8rem 1rem;
            box-shadow: none;
        }

        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div > div,
        .stMultiSelect > div > div > div {
            background: #ffffff;
            color: #0f172a;
            border: 1px solid #d9dee8;
            border-radius: 12px;
        }

        .stDataFrame, .stPlotlyChart {
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid var(--line);
        }
        [data-testid="stForm"], [data-testid="stExpander"] {
            background:#fff; border:1px solid var(--line); border-radius:14px;
        }
        h1, h2, h3, p, label { font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
        h2, h3 { letter-spacing:-.02em; color:var(--ink); }
        [data-testid="stSidebar"] h2 { font-size:1.15rem; }
        @media (max-width: 768px) {
            .block-container { padding: 1rem 1rem 3rem; }
            .hero-card { padding: 1.25rem; border-radius:16px; }
            .hero-card h1 { font-size:1.75rem; }
            .stat-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
        }
        @media (max-width: 460px) {
            .stat-grid { grid-template-columns: 1fr; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_stat_cards(stats):
    cards_html = "".join(
        f"""
        <div class="stat-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            <div class="sub">{sub}</div>
        </div>
        """
        for label, value, sub in stats
    )
    st.markdown(f'<div class="stat-grid">{cards_html}</div>', unsafe_allow_html=True)


if "runs" not in st.session_state:
    st.session_state.runs = []  # her biri: {"label", "config", "results", "metrics", "wall_clock"}

# --------------------------------------------------------------------------
# KONFİGÜRASYON PANELİ
# --------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-card">
        <div class="eyebrow">Performance workspace</div>
        <h1>LLM Stress Lab</h1>
        <p>Modelleri gerçek yük altında karşılaştırın; gecikme, kararlılık ve üretim hızını tek bir sade çalışma alanında izleyin.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Test ayarları")
    st.caption("Sağlayıcıyı ve yük profilini belirleyin.")

    provider = st.selectbox("Sağlayıcı", ["openrouter", "openai", "anthropic", "gemini", "grok"])
    is_openrouter = provider == "openrouter"
    if is_openrouter:
        env_api_key = os.getenv("OPENROUTER_API_KEY", "")
        entered_api_key = st.text_input(
            "OpenRouter API anahtarı",
            type="password",
            placeholder="sk-or-v1-...",
            help="Anahtar kaynak koda kaydedilmez; yalnızca bu sunucu oturumunda kullanılır.",
        )
        api_key = entered_api_key or env_api_key
        model_default = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        if env_api_key and not entered_api_key:
            st.caption("Sunucuda kayıtlı OpenRouter anahtarı kullanılıyor.")
        else:
            st.caption("Anahtar kaydedilmeden yalnızca bu oturumda kullanılır.")
    else:
        api_key = st.text_input("API anahtarı", type="password", help="Yalnızca bu sunucu oturumunda kullanılır.")
        model_default = ""
    model = st.text_input("Model", value=model_default, placeholder="Örn. gpt-4o veya claude-sonnet-4-6")

    st.subheader("Yük profili")
    concurrency = st.slider("Eşzamanlılık (Concurrency)", 1, 100, 5)
    total_requests = st.number_input("Toplam İstek Sayısı", min_value=1, max_value=2000, value=20)
    timeout = st.number_input("Timeout (sn)", min_value=1.0, max_value=600.0, value=60.0)

    ramp_up = st.checkbox("Ramp-Up (kademeli başlat)")
    ramp_up_delay = st.number_input("Ramp-Up Gecikmesi (sn)", min_value=0.0, value=0.5, disabled=not ramp_up)

    stream = st.checkbox("Streaming kullan (TTFT ölçümü için önerilir)", value=True)
    save_responses = st.checkbox("Yanıtları Kaydet (Save LLM Responses)", value=False,
                                  help="Büyük testlerde bellek/dosya boyutunu optimize etmek için varsayılan kapalı")

    st.subheader("İstek içeriği")
    prompt_mode = st.radio("Prompt kaynağı", ["Sabit prompt", "Dataset (JSON) yükle"])
    prompt = ""
    prompts_list = None
    if prompt_mode == "Sabit prompt":
        prompt = st.text_area("Test mesajı", value="500 kelimelik bir makale yaz", height=140)
    else:
        uploaded = st.file_uploader("Prompt dataset (JSON liste, örn: [\"p1\", \"p2\", ...])", type=["json"])
        if uploaded is not None:
            try:
                data = json.loads(uploaded.read().decode("utf-8"))
                prompts_list = [str(x) for x in data] if isinstance(data, list) else None
                if prompts_list:
                    st.success(f"{len(prompts_list)} prompt yüklendi (round-robin kullanılacak)")
                else:
                    st.error("JSON bir string listesi olmalı, örn: [\"prompt1\", \"prompt2\"]")
            except Exception as e:
                st.error(f"JSON okunamadı: {e}")

    run_label = st.text_input("Bu koşu için etiket (karşılaştırma grafiğinde görünür)",
                               value=f"{provider}:{model}" if model else provider)

    start_clicked = st.button("Testi başlat", type="primary", width="stretch")

# --------------------------------------------------------------------------
# TESTİ ÇALIŞTIR
# --------------------------------------------------------------------------
if start_clicked:
    if not api_key or not model:
        key_hint = "OPENROUTER_API_KEY ortam değişkeni bulunamadı." if is_openrouter else "API anahtarı ve model alanları zorunludur."
        st.error(key_hint)
    elif prompt_mode == "Sabit prompt" and not prompt.strip():
        st.error("Prompt boş olamaz.")
    elif prompt_mode == "Dataset (JSON) yükle" and not prompts_list:
        st.error("Geçerli bir prompt dataset'i yüklemelisin.")
    else:
        config = TestConfig(
            provider=provider,
            api_key=api_key,
            model=model,
            prompt=prompt,
            prompts=prompts_list,
            concurrency=concurrency,
            total_requests=int(total_requests),
            timeout=timeout,
            ramp_up=ramp_up,
            ramp_up_delay=ramp_up_delay,
            stream=stream,
            save_responses=save_responses,
        )
        engine = AsyncEngine(config)
        with st.spinner(f"{total_requests} istek, concurrency={concurrency} ile test çalışıyor..."):
            results = asyncio.run(engine.run())
        metrics = compute_metrics(results, wall_clock_seconds=engine.wall_clock_seconds)

        st.session_state.runs.append({
            "label": run_label or f"{provider}:{model}",
            "config": config,
            "results": results,
            "metrics": metrics,
            "wall_clock": engine.wall_clock_seconds,
            "run_start_perf": engine.run_start_perf,
        })
        st.success(f"Test tamamlandı: {metrics.success_count}/{metrics.total_requests} başarılı")
        failed_results = [r for r in results if r.status != RequestStatus.SUCCESS]
        if failed_results:
            with st.expander(f"Başarısız istek ayrıntıları ({len(failed_results)})"):
                for failed in failed_results[:10]:
                    status_code = f"HTTP {failed.status_code}" if failed.status_code else "Ağ/uygulama hatası"
                    st.error(f"İstek #{failed.request_id} · {status_code}: {failed.error_message or failed.status.value}")

# --------------------------------------------------------------------------
# SON KOŞUNUN SONUÇLARI
# --------------------------------------------------------------------------
if st.session_state.runs:
    latest = st.session_state.runs[-1]
    m = latest["metrics"]
    results = latest["results"]
    config: TestConfig = latest["config"]

    st.markdown(f"<div class=\"section-shell\"><h2 style='margin:0 0 .5rem;color:#172033;'>Son koşu · {latest['label']}</h2></div>", unsafe_allow_html=True)

    render_stat_cards([
        ("Success Rate", f"{m.success_rate_pct}%", f"{m.success_count}/{m.total_requests} başarılı"),
        ("Avg Süre", f"{m.avg_total_ms:.0f} ms" if m.avg_total_ms else "-", "ortalama yanıt süresi"),
        ("P99 Latency", f"{m.p99_ms:.0f} ms" if m.p99_ms else "-", "%99 gecikme"),
        ("Avg TTFT", f"{m.avg_ttft_ms:.0f} ms" if m.avg_ttft_ms else "-", "ilk metin süresi"),
        ("TPS (agg)", f"{m.aggregate_tps:.1f}" if m.aggregate_tps else "-", "birleşik işlem hızı"),
        ("Toplam İstek", str(m.total_requests), "tüm istekler"),
        ("Hata", str(m.error_count), "başarısız istekler"),
        ("Rate Limited", str(m.rate_limited_count), "429 yanıtları"),
        ("Timeout", str(m.timeout_count), "zaman aşımı"),
    ])

    st.subheader("Eşzamanlı istekler")
    timeline_df = build_timeline_df(results, latest["run_start_perf"])
    if not timeline_df.empty:
        fig = px.scatter(
            timeline_df, x="start_offset_s", y="duration_ms", color="status",
            hover_data=["request_id", "ttft_ms"],
            labels={"start_offset_s": "Zaman (sn)", "duration_ms": "Yanıt Süresi (ms)"},
        )
        st.plotly_chart(fig, width="stretch")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Throughput (RPS)")
        throughput_df = build_throughput_df(results, latest["run_start_perf"])
        if not throughput_df.empty:
            fig2 = px.bar(throughput_df, x="second", y="completed_requests",
                           labels={"second": "Saniye", "completed_requests": "Tamamlanan İstek"})
            st.plotly_chart(fig2, width="stretch")

    with col_b:
        st.subheader("Sağlayıcı karşılaştırması")
        if len(st.session_state.runs) > 1:
            comp_df = build_comparison_df(st.session_state.runs)
            fig3 = px.bar(comp_df, x="label", y=["avg_ttft_ms", "avg_tps"], barmode="group",
                          labels={"value": "Değer", "label": "Koşu", "variable": "Metrik"})
            st.plotly_chart(fig3, width="stretch")
        else:
            st.info("Karşılaştırma için en az 2 farklı koşu (farklı provider/model) çalıştır.")

    # ----------------------------------------------------------------------
    # YANIT İNCELEME PANELİ
    # ----------------------------------------------------------------------
    if config.save_responses:
        st.subheader("Yanıtları incele")
        for r in sorted(results, key=lambda x: x.request_id):
            if r.status != RequestStatus.SUCCESS:
                continue
            with st.expander(f"#{r.request_id} — {r.total_ms:.0f}ms — {r.token_count} token"):
                st.text(r.output_text or "(boş yanıt)")
    else:
        st.caption("Yanıt metinlerini görmek için sol panelden 'Yanıtları Kaydet' seçeneğini aç.")

    # ----------------------------------------------------------------------
    # RAPOR DIŞA AKTARMA (FAZ 4)
    # ----------------------------------------------------------------------
    st.subheader("Raporu dışa aktar")
    payload = build_export_payload(config, results, m, latest["wall_clock"])
    json_str = json.dumps(payload, ensure_ascii=False, indent=2)
    csv_str = export_to_csv_string(config, results, m, latest["wall_clock"])
    html_str = export_to_html_string(config, results, m, latest["wall_clock"])

    d1, d2, d3 = st.columns(3)
    d1.download_button("JSON indir", json_str, file_name="llm_stress_test_sonuc.json", mime="application/json", width="stretch")
    d2.download_button("CSV indir", csv_str, file_name="llm_stress_test_sonuc.csv", mime="text/csv", width="stretch")
    d3.download_button("HTML rapor indir", html_str, file_name="llm_stress_test_raporu.html", mime="text/html", width="stretch")

    with st.expander("📋 Tüm Koşu Geçmişi"):
        hist_rows = [{
            "Etiket": run["label"],
            "Provider": run["config"].provider,
            "Model": run["config"].model,
            "Success %": run["metrics"].success_rate_pct,
            "Avg (ms)": round(run["metrics"].avg_total_ms or 0, 1),
            "P99 (ms)": round(run["metrics"].p99_ms or 0, 1),
            "TPS (agg)": round(run["metrics"].aggregate_tps or 0, 1),
        } for run in st.session_state.runs]
        st.dataframe(pd.DataFrame(hist_rows), width="stretch")
else:
    st.info("Soldaki panelden bir test yapılandırıp 'Testi Başlat'a bas.")
