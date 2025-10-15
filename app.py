import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Kripto Veri Paneli",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Kripto Finansal Paneli")

API_KEY = st.secrets.get("api_key")

COIN_LISTESI = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana",
    "Toncoin": "the-open-network",
    "Aave": "aave",
    "PancakeSwap (Cake)": "pancakeswap-token",
    "Uniswap": "uniswap"
}

def format_large_number(num):
    if num is None: return "$0"
    if num > 1_000_000_000_000: return f"${num / 1_000_000_000_000:.2f} T"
    if num > 1_000_000_000: return f"${num / 1_000_000_000:.2f} Mlr"
    if num > 1_000_000: return f"${num / 1_000_000:.2f} Mln"
    return f"${num:,.2f}"

@st.cache_data(ttl=600)
def get_coin_market_data(coin_id):
    URL = 'https://api.coingecko.com/api/v3/coins/markets'
    PARAMETRELER = {'vs_currency': 'usd', 'ids': coin_id, 'x_cg_demo_api_key': API_KEY}
    try:
        response = requests.get(url=URL, params=PARAMETRELER)
        response.raise_for_status()
        return response.json()[0]
    except Exception: return None

@st.cache_data(ttl=3600)
def get_market_chart_data(coin_id, days):
    URL = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    PARAMETRELER = {'vs_currency': 'usd', 'days': days, 'interval': 'daily', 'x_cg_demo_api_key': API_KEY}
    try:
        response = requests.get(url=URL, params=PARAMETRELER)
        response.raise_for_status()
        veri = response.json()
        fiyat_df = pd.DataFrame(veri['prices'], columns=['timestamp', 'Close'])
        hacim_df = pd.DataFrame(veri['total_volumes'], columns=['timestamp', 'Volume'])
        df = pd.merge(fiyat_df, hacim_df, on='timestamp')
        df['Tarih'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('Tarih', inplace=True)
        df['Open'] = df['Close'].shift(1)
        df['High'] = df[['Open', 'Close']].max(axis=1)
        df['Low'] = df[['Open', 'Close']].min(axis=1)
        df.dropna(inplace=True)
        return df
    except Exception: return None

@st.cache_data(ttl=3600)
def get_price_data_for_range(coin_id, start_datetime, end_datetime):
    start_timestamp = int(start_datetime.timestamp())
    end_timestamp = int(end_datetime.timestamp())
    URL = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
    PARAMETRELER = {'vs_currency': 'usd', 'from': start_timestamp, 'to': end_timestamp, 'x_cg_demo_api_key': API_KEY}
    try:
        response = requests.get(url=URL, params=PARAMETRELER)
        response.raise_for_status()
        veri = response.json()['prices']
        df = pd.DataFrame(veri, columns=['timestamp', 'Fiyat (USD)'])
        df['Tarih'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[['Tarih', 'Fiyat (USD)']].set_index('Tarih')
        return df
    except Exception: return None

st.sidebar.title("Ayarlar")
secilen_coin_adi = st.sidebar.selectbox('Coin Seçin:', list(COIN_LISTESI.keys()))
analiz_turu = st.sidebar.radio("Analiz Türü Seçin:", ["Periyot", "Özel Tarih Aralığı"])

show_ma = False
ma_period = 20
enable_drawing = False

if analiz_turu == "Periyot":
    zaman_araliklari = {"Son 30 Gün": 30, "Son 90 Gün": 90, "Son 1 Yıl": 365, "Tüm Zamanlar": "max"}
    secilen_aralik_adi = st.sidebar.selectbox("Periyot Seçin:", zaman_araliklari.keys())
    secilen_gun_sayisi = zaman_araliklari[secilen_aralik_adi]
    
    st.sidebar.subheader("Teknik Göstergeler")
    show_ma = st.sidebar.checkbox("Hareketli Ortalama Göster")
    if show_ma:
        ma_period = st.sidebar.number_input("MA Periyodu:", min_value=5, max_value=200, value=20, step=1)
    
    st.sidebar.subheader("Grafik Araçları")
    enable_drawing = st.sidebar.checkbox("Grafik Üzerinde Çizim Yap")
    if enable_drawing:
        st.sidebar.button("🗑️ Çizimleri Temizle")

else:
    bugun = datetime.now().date()
    baslangic_tarihi = st.sidebar.date_input("Başlangıç Tarihi", bugun - pd.Timedelta(days=30))
    bitis_tarihi = st.sidebar.date_input("Bitiş Tarihi", bugun)

secilen_coin_id = COIN_LISTESI[secilen_coin_adi]

st.header(f"{secilen_coin_adi} Fiyat Analizi")
market_data = get_coin_market_data(secilen_coin_id)
if market_data:
    st.metric(label="Anlık Fiyat (USD)", value=f"${market_data.get('current_price', 0):,.2f}", delta=f"{market_data.get('price_change_percentage_24h', 0):,.2f}%")
else: st.warning("Anlık piyasa verileri alınamadı.")

tab1, tab2 = st.tabs(["Grafik", "Piyasa Detayları"])

with tab1:
    if analiz_turu == "Periyot":
        st.subheader(f"Tarihsel Fiyat Grafiği ({secilen_aralik_adi})")
        with st.spinner('Grafik için veriler yükleniyor...'):
            chart_df = get_market_chart_data(secilen_coin_id, secilen_gun_sayisi)
            if chart_df is not None and not chart_df.empty:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                
                fig.add_trace(go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'], low=chart_df['Low'], close=chart_df['Close'], increasing_line_color='lime', decreasing_line_color='red', name='OHLC'), row=1, col=1)
                
                colors = ['green' if row['Open'] - row['Close'] >= 0 else 'red' for index, row in chart_df.iterrows()]
                fig.add_trace(go.Bar(x=chart_df.index, y=chart_df['Volume'], name='Hacim', marker_color=colors), row=2, col=1)
                
                if show_ma:
                    chart_df[f'MA{ma_period}'] = chart_df['Close'].rolling(window=ma_period).mean()
                    fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df[f'MA{ma_period}'], mode='lines', name=f'{ma_period} Günlük MA', line=dict(color='cyan', width=2)), row=1, col=1)
                
                drag_mode = 'drawline' if enable_drawing else 'pan'
                
                fig.update_layout(
                    xaxis_rangeslider_visible=False, 
                    template="plotly_dark", 
                    height=600, 
                    margin=dict(l=20, r=20, t=20, b=20), 
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    dragmode=drag_mode,
                    newshape=dict(line_color='yellow', line_width=2)
                )
                fig.update_yaxes(title_text="Fiyat (USD)", row=1, col=1)
                fig.update_yaxes(title_text="Hacim", row=2, col=1)
                
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("Seçilen periyot için grafik verisi bulunamadı.")
    else:
        st.subheader(f"{baslangic_tarihi} - {bitis_tarihi} Arası - Çizgi Grafiği")
        if baslangic_tarihi >= bitis_tarihi:
            st.error("Hata: Başlangıç tarihi, bitiş tarihinden sonra veya aynı olamaz.")
        else:
            start_datetime = datetime.combine(baslangic_tarihi, datetime.min.time())
            end_datetime = datetime.combine(bitis_tarihi, datetime.max.time())
            with st.spinner('Çizgi grafiği için veriler yükleniyor...'):
                price_df = get_price_data_for_range(secilen_coin_id, start_datetime, end_datetime)
                if price_df is not None and not price_df.empty:
                    st.line_chart(price_df) 
                else: st.warning("Seçilen tarih aralığı için veri bulunamadı.")

with tab2:
    st.subheader("Piyasa Detayları")
    if market_data:
        detay_verileri = {"Metrik": ["Piyasa Değeri", "24s Hacim", "24s En Yüksek", "24s En Düşük", "Dolaşımdaki Arz", "Toplam Arz"], "Değer": [format_large_number(market_data.get('market_cap', 0)), format_large_number(market_data.get('total_volume', 0)), f"${market_data.get('high_24h', 0):,.2f}", f"${market_data.get('low_24h', 0):,.2f}", f"{market_data.get('circulating_supply', 0):,} {market_data.get('symbol', '').upper()}", f"{market_data.get('total_supply', 0):,}" if market_data.get('total_supply') else "N/A"]}
        df_detaylar = pd.DataFrame(detay_verileri).set_index("Metrik")
        st.table(df_detaylar)
    else: st.warning("Detay verileri alınamadı.")

